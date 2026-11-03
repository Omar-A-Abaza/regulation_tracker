from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from dashboard import data
from dashboard.data import DocRow
from database import repository as repo
from scrapers.base import DocumentCandidate

APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")
TODAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 2, 12, 0)


def row(n, *, framework="eu_ai_act", categories=("gpai",), source="eurlex", published=TODAY, status="new",
        detected=NOW, title=None, note=None):
    return DocRow(id=n, source=source, title=title or f"Doc {n}", url=f"https://x/{n}", date_published=published,
                  date_detected=detected, framework=framework, note=note, status=status, categories=list(categories))


DOCS = [
    row(1, published=TODAY - timedelta(days=3), title="Copyright consultation"),
    row(2, framework="us_federal", categories=["penalties"], source="federal_register",
        published=TODAY - timedelta(days=60), note="Notice from Federal Trade Commission."),
    row(3, framework="nist_ai_rmf", categories=["governance"], source="nist", published=None),
]


def test_empty_filters_keep_everything():
    assert len(data.filter_documents(DOCS, today=TODAY)) == 3


def test_filter_by_framework_category_and_source():
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, frameworks=["us_federal"])] == [2]
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, categories=["gpai", "governance"])] == [1, 3]
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, sources=["nist"])] == [3]


def test_date_range_drops_old_and_undated():
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, days=30)] == [1]


def test_search_looks_at_title_and_note():
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, query="COPYRIGHT")] == [1]
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, query="trade commission")] == [2]


def test_search_understands_short_forms():
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, query="FTC")] == [2]


def test_new_this_week_ignores_seed_backfill_and_old():
    docs = [row(1), row(2, status="seed"), row(3, status="backfill"), row(4, detected=NOW - timedelta(days=8))]
    assert [d.id for d in data.new_this_week(docs, NOW)] == [1]


def test_sort_puts_undated_last():
    assert [d.id for d in data.sort_newest_first(DOCS)] == [1, 2, 3]


def test_next_milestone():
    milestones = [{"date": date(2026, 8, 2), "title": "past"}, {"date": date(2026, 12, 2), "title": "next"}]
    assert data.next_milestone(milestones, TODAY)["title"] == "next"
    assert data.next_milestone(milestones, date(2027, 1, 1)) is None


def test_real_timeline_has_a_next_deadline():
    assert data.next_milestone(data.load_milestones(), TODAY) is not None


def test_time_ago():
    assert data.time_ago(NOW - timedelta(seconds=5), NOW) == "just now"
    assert data.time_ago(NOW - timedelta(minutes=1), NOW) == "1 minute ago"
    assert data.time_ago(NOW - timedelta(hours=3), NOW) == "3 hours ago"
    assert data.time_ago(NOW - timedelta(days=2), NOW) == "2 days ago"


# --- the whole page -------------------------------------------------------

@pytest.fixture
def app_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = repo.get_engine(url)
    repo.init_db(engine)
    with repo.make_session(engine) as s:
        repo.save_document(s, DocumentCandidate(
            source="federal_register", title="Costs $874 Million (a title with a dollar sign)",
            url="https://x/(1)", framework="us_federal", date_published=date.today(), categories=["penalties"]),
            is_seed=True)
        s.commit()
    return engine


def run_app():
    # The page caches its database connection; each test uses its own database.
    st.cache_data.clear()
    st.cache_resource.clear()
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_page_loads_with_no_scrape_runs(app_db):
    at = run_app()
    assert not at.exception
    assert at.title[0].value == "What changed this week"
    assert any("haven't run yet" in w.value for w in at.warning)


def test_page_warns_when_a_source_failed(app_db):
    with repo.make_session(app_db) as s:
        repo.finish_run(s, repo.start_run(s, "nist"), error="RuntimeError: down")
    at = run_app()
    assert not at.exception
    assert any("NIST" in w.value and "might be missing" in w.value for w in at.warning)


def test_search_box_filters_the_list(app_db):
    at = run_app()
    at.text_input[0].input("nothing matches this").run()
    assert not at.exception
    assert any("No updates match" in i.value for i in at.info)
