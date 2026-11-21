import json
import re
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


def test_filter_by_urgency():
    docs = [row(1), row(2), row(3)]
    docs[0].risk_level, docs[1].risk_level = "Action Required", "Watch"
    assert [d.id for d in data.filter_documents(docs, today=TODAY, risk_levels=["Action Required"])] == [1]
    assert [d.id for d in data.filter_documents(docs, today=TODAY, risk_levels=["none"])] == [3]


def test_search_understands_short_forms():
    assert [d.id for d in data.filter_documents(DOCS, today=TODAY, query="FTC")] == [2]


def test_new_this_week_ignores_seed_backfill_and_old():
    docs = [row(1), row(2, status="seed"), row(3, status="backfill"), row(4, detected=NOW - timedelta(days=8))]
    assert [d.id for d in data.new_this_week(docs, NOW)] == [1]


def test_sort_puts_undated_last():
    assert [d.id for d in data.sort_newest_first(DOCS)] == [1, 2, 3]


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


def run_app(page=None, params=None):
    # The pages cache their database connection; each test uses its own database.
    st.cache_data.clear()
    st.cache_resource.clear()
    at = AppTest.from_file(APP, default_timeout=30)
    for key, value in (params or {}).items():
        at.query_params[key] = value
    at.run()
    if page:
        at.switch_page(page).run()
    return at


def board_data(at):
    frames = at.get("iframe")
    assert len(frames) == 1
    html = frames[0].proto.srcdoc
    return json.loads(re.search(r"var DATA = (.*?);\n", html).group(1))


# --- fuse board (home page) -------------------------------------------------

def test_fuse_board_is_the_home_page(app_db):
    at = run_app()
    assert not at.exception
    assert at.title[0].value == "Fuse board"
    board = board_data(at)
    titles = {i["title"] for i in board["items"]}
    assert "High-risk AI rules apply (Annex III)" in titles  # from the timeline
    assert board["header"]["sources"] == 0
    assert any("haven't run yet" in w.value for w in at.warning)


def test_fuse_board_shows_a_failing_source(app_db):
    with repo.make_session(app_db) as s:
        repo.finish_run(s, repo.start_run(s, "nist"), error="RuntimeError: down")
    at = run_app()
    assert not at.exception
    assert board_data(at)["header"]["failing"] == ["NIST"]
    assert not at.warning


def test_fuse_board_includes_document_deadlines(app_db):
    from database.models import Document
    with repo.make_session(app_db) as s:
        doc = s.query(Document).one()
        doc.risk_level = "Action Required"
        doc.summary_json = {**SUMMARY, "key_deadline_date": (date.today() + timedelta(days=20)).isoformat(),
                            "key_deadline": "Comments due."}
        s.commit()
    item = next(i for i in board_data(run_app())["items"] if i["kind"] == "document")
    assert item["urgency"] == "red" and item["ai_urgency"] == "Action Required"
    assert item["summary"] == SUMMARY["tldr"]


# --- all documents ----------------------------------------------------------

SUMMARY = {"tldr": ["First bullet.", "Second bullet.", "Third bullet."],
           "who_is_affected": "AI providers", "key_deadline_date": "", "key_deadline": "",
           "actions_required": [], "risk_level": "Action Required", "categories": ["penalties"],
           "_meta": {"model": "claude-sonnet-5-5", "based_on": "full_text", "summarized_at": "2026-11-04T10:00:00"}}


def test_documents_page_lists_every_document_with_its_source(app_db):
    at = run_app("documents.py")
    assert not at.exception
    assert at.title[0].value == "All documents"
    assert at.subheader[0].value.startswith("1 of 1 documents")
    text = " ".join(m.value for m in at.markdown)
    assert "Starting data" in text and "Costs \\$874 Million" in text
    assert "No AI summary yet" in text
    assert len(at.get("iframe")) == 1  # the next-5 fuse strip


def test_documents_page_shows_ai_summary_and_urgency(app_db):
    from database.models import Document
    with repo.make_session(app_db) as s:
        doc = s.query(Document).one()
        doc.risk_level = "Action Required"
        doc.summary_json = SUMMARY
        s.commit()
    at = run_app("documents.py")
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Action Required" in text and "First bullet." in text
    assert at.expander[0].label == "Full AI summary"


def test_documents_page_shows_a_failing_source(app_db):
    with repo.make_session(app_db) as s:
        repo.finish_run(s, repo.start_run(s, "nist"), error="RuntimeError: down")
    at = run_app("documents.py")
    assert not at.exception
    table = at.dataframe[0].value
    assert table.loc[0, "Source"] == "NIST" and "down" in table.loc[0, "Problem"]


def test_filters_can_be_set_from_the_link(app_db):
    at = run_app("documents.py", {"urgency": "Action Required", "range": "Last 30 days", "category": "gpai"})
    assert not at.exception
    urgency = next(m for m in at.multiselect if m.label == "Urgency")
    assert urgency.value == ["Action Required"]
    assert next(m for m in at.multiselect if m.label == "Category").value == ["gpai"]
    assert next(b for b in at.selectbox if b.label == "Date range").value == "Last 30 days"
    assert any("No documents match" in i.value for i in at.info)  # the test document has no urgency


def test_search_box_filters_the_list(app_db):
    at = run_app("documents.py")
    at.text_input[0].input("nothing matches this").run()
    assert not at.exception
    assert any("No documents match" in i.value for i in at.info)


def test_sorting(app_db):
    at = run_app("documents.py")
    sort = next(b for b in at.selectbox if b.label == "Sort by")
    for option in sort.options:
        sort.set_value(option).run()
        assert not at.exception
