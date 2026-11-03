"""Day 4: page watching, "really new" documents, the scrape log, and AI Act text versions."""
import json
from pathlib import Path

import pytest

import main
from database import repository as repo
from database.models import Document, ScrapeRun
from processors.differ import summarize_change
from scrapers.base import BaseScraper, DocumentCandidate
from scrapers.eurlex import parse_versions
from scrapers.page_watcher import WatchedPage, extract_text

FIXTURES = Path(__file__).parent / "fixtures"
PAGE = WatchedPage(name="Test page", url="https://example.gov/page", selector="main",
                   source="nist", framework="nist_ai_rmf")


@pytest.fixture
def engine(tmp_path):
    engine = repo.get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    repo.init_db(engine)
    return engine


class FakeWatcher:
    """Stands in for PageWatcher: returns whatever text we give it."""

    name, label = "pages", "Watched pages"

    def __init__(self, texts):
        self.texts = texts

    def page_text(self, page):
        text = self.texts[page.url]
        if isinstance(text, Exception):
            raise text
        return text

    def close(self):
        pass


def docs(engine):
    with repo.make_session(engine) as s:
        return list(s.query(Document))


# --- differ ---------------------------------------------------------------

def test_summarize_change_quotes_added_and_removed_text():
    note = summarize_change("AI RMF 1.0\nBeing revised.", "AI RMF 1.0\nAI RMF 2.0 released.")
    assert note == "New text: “AI RMF 2.0 released.”. Removed: “Being revised.”."


def test_summarize_change_with_no_text_change():
    assert "layout" in summarize_change("same", "same")


# --- page text ------------------------------------------------------------

def test_extract_text_keeps_main_content_only():
    html = "<nav>Menu</nav><main><h1>Title</h1><script>x()</script><p>Body   text</p></main><footer>F</footer>"
    assert extract_text(html, "main") == "Title\nBody text"


def test_extract_text_keeps_links_inside_their_sentence():
    html = '<main><p>NIST released a <a href="/x">concept note</a> for an <em>AI RMF</em> profile.</p></main>'
    assert extract_text(html, "main") == "NIST released a concept note for an AI RMF profile."


def test_extract_text_fails_loudly_if_layout_changes():
    with pytest.raises(ValueError):
        extract_text("<div>No main here</div>", "main")


# --- page watcher ---------------------------------------------------------

def test_first_check_only_saves_a_fingerprint(engine):
    assert main.run_page_watch(engine, FakeWatcher({PAGE.url: "v1"}), [PAGE])
    assert docs(engine) == []


def test_same_page_twice_is_not_a_change(engine):
    main.run_page_watch(engine, FakeWatcher({PAGE.url: "v1"}), [PAGE])
    main.run_page_watch(engine, FakeWatcher({PAGE.url: "v1"}), [PAGE])
    assert docs(engine) == []


def test_changed_page_creates_an_update(engine):
    main.run_page_watch(engine, FakeWatcher({PAGE.url: "Intro\nOld news"}), [PAGE])
    main.run_page_watch(engine, FakeWatcher({PAGE.url: "Intro\nAI RMF 2.0 is out"}), [PAGE])
    [doc] = docs(engine)
    assert doc.title == "Page updated: Test page"
    assert "AI RMF 2.0 is out" in doc.note
    assert doc.url.startswith(PAGE.url)
    with repo.make_session(engine) as s:
        assert [d.id for d in repo.get_new_documents(s)] == [doc.id]


def test_one_failing_page_makes_the_run_partial(engine):
    other = WatchedPage(name="Other", url="https://example.gov/other", selector="main",
                        source="nist", framework="nist_ai_rmf")
    ok = main.run_page_watch(engine, FakeWatcher({PAGE.url: "v1", other.url: ValueError("gone")}), [PAGE, other])
    assert not ok
    with repo.make_session(engine) as s:
        run = repo.last_runs(s)["pages"]
    assert run.status == "partial"
    assert "Other" in run.error


# --- "really new" ---------------------------------------------------------

class FakeScraper(BaseScraper):
    name, label = "fake", "Fake"
    batches: list[list[DocumentCandidate]] = []

    def fetch(self):
        return self.batches.pop(0)


def candidate(n):
    return DocumentCandidate(source="fake", title=f"Doc {n}", url=f"https://example.gov/{n}", framework="us_federal")


def test_first_run_is_backfill_not_news(engine):
    FakeScraper.batches = [[candidate(1), candidate(2)], [candidate(1), candidate(2), candidate(3)]]
    main.run_scraper(engine, FakeScraper)
    with repo.make_session(engine) as s:
        assert repo.get_new_documents(s) == []
    main.run_scraper(engine, FakeScraper)
    with repo.make_session(engine) as s:
        assert [d.title for d in repo.get_new_documents(s)] == ["Doc 3"]


def test_starting_data_is_never_new(engine):
    with repo.make_session(engine) as s:
        repo.save_document(s, candidate(1), is_seed=True)
        s.commit()
        assert repo.get_new_documents(s) == []


# --- scrape log -----------------------------------------------------------

class BrokenScraper(BaseScraper):
    name, label = "broken", "Broken"

    def fetch(self):
        raise RuntimeError("site is down")


def test_failed_run_is_logged(engine):
    assert main.run_scraper(engine, BrokenScraper) is False
    with repo.make_session(engine) as s:
        run = s.query(ScrapeRun).one()
    assert (run.status, run.error) == ("failed", "RuntimeError: site is down")


def test_failed_first_run_does_not_count_as_backfill(engine):
    # If the first run failed, the first run that *worked* is the backfill.
    main.run_scraper(engine, BrokenScraper)
    FakeScraper.batches = [[candidate(1)]]
    main.run_scraper(engine, FakeScraper)
    with repo.make_session(engine) as s:
        assert repo.get_new_documents(s) == []


# --- AI Act text versions -------------------------------------------------

def test_parse_versions():
    versions = parse_versions(json.loads((FIXTURES / "eurlex_versions.json").read_text()))
    assert [v.external_id for v in versions] == ["02024R1689-20260727", "02024R1689-20240712"]
    assert versions[0].title == "Full text of the EU AI Act, version of 27 Jul 2026"


# --- adding columns to an existing database -------------------------------

def test_init_db_adds_new_columns_to_old_tables(tmp_path):
    engine = repo.get_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE page_fingerprints (id INTEGER PRIMARY KEY, url VARCHAR, "
                             "content_hash VARCHAR, fetched_at DATETIME)")
    repo.init_db(engine)
    with engine.connect() as conn:
        columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(page_fingerprints)")]
    assert "content_text" in columns
