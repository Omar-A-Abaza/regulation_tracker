from datetime import date

import pytest

from database import repository as repo
from database.models import Document
from scrapers.base import DocumentCandidate


@pytest.fixture
def session():
    engine = repo.get_engine("sqlite://")  # in-memory database, gone after the test
    repo.init_db(engine)
    with repo.make_session(engine) as s:
        yield s


def candidate(**overrides):
    fields = dict(source="eurlex", title="Test act", url="https://example.eu/a", framework="eu_ai_act",
                  date_published=date(2026, 7, 20), external_id="32026R0001", categories=["gpai"])
    fields.update(overrides)
    return DocumentCandidate(**fields)


def test_saving_twice_keeps_one_copy(session):
    assert repo.save_document(session, candidate()) is True
    assert repo.save_document(session, candidate()) is False
    assert session.query(Document).count() == 1


def test_same_id_with_different_link_is_a_copy(session):
    # The seed uses an ELI link; the scraper uses a CELEX link. Same law.
    repo.save_document(session, candidate(url="https://eur-lex.europa.eu/eli/reg/2026/1/oj"), is_seed=True)
    assert repo.save_document(session, candidate(url="https://eur-lex.europa.eu/...CELEX:32026R0001")) is False


def test_documents_without_id_dedupe_by_link(session):
    assert repo.save_document(session, candidate(external_id=None)) is True
    assert repo.save_document(session, candidate(external_id=None)) is False


def test_get_recent_is_newest_first(session):
    repo.save_document(session, candidate(url="u1", external_id="a", date_published=date(2025, 1, 1)))
    repo.save_document(session, candidate(url="u2", external_id="b", date_published=date(2026, 1, 1)))
    repo.save_document(session, candidate(url="u3", external_id="c", date_published=None))
    assert [d.url for d in repo.get_recent(session)] == ["u2", "u1", "u3"]


def test_run_log(session):
    run = repo.start_run(session, "eurlex")
    repo.finish_run(session, run, found=8, new=7)
    ok = repo.last_runs(session)["eurlex"]
    assert (ok.status, ok.found_count, ok.new_count) == ("success", 8, 7)

    failed = repo.start_run(session, "eurlex")
    repo.finish_run(session, failed, error="boom")
    assert repo.last_runs(session)["eurlex"].status == "failed"
