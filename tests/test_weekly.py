"""The weekly job: --yes, running with no terminal, and when it counts as failed."""
from datetime import date

import pytest

import main
from database import repository as repo
from database.models import Document
from processors import summarizer as summ
from scrapers.base import DocumentCandidate
from tests.test_summarizer import FakeClient, FakeFetcher

TODAY = date(2026, 11, 4)


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SUMMARY_BUDGET_USD", raising=False)
    engine = repo.get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    repo.init_db(engine)
    with repo.make_session(engine) as s:
        repo.save_document(s, DocumentCandidate(source="nist", title="Doc", url="https://x/1",
                                                framework="nist_ai_rmf", note="A note."), is_seed=True)
        s.commit()
    return engine


def summarized(engine):
    with repo.make_session(engine) as s:
        return [d.title for d in s.query(Document) if d.summary_json]


def test_no_terminal_means_no_question(engine, monkeypatch, capsys):
    monkeypatch.setattr(main, "can_ask", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("asked with no terminal"))
    assert main.cmd_summarize(engine, summarizer=summ.Summarizer(FakeClient()), fetcher=FakeFetcher(), today=TODAY)
    assert summarized(engine) == ["Doc"]
    assert "without asking" in capsys.readouterr().out


def test_at_a_terminal_it_still_asks(engine, monkeypatch):
    monkeypatch.setattr(main, "can_ask", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    client = FakeClient()
    main.cmd_summarize(engine, summarizer=summ.Summarizer(client), fetcher=FakeFetcher(), today=TODAY)
    assert client.created == []


def test_yes_still_respects_the_spending_cap(engine, monkeypatch, capsys):
    monkeypatch.setenv("SUMMARY_BUDGET_USD", "0.001")
    client = FakeClient()
    main.cmd_summarize(engine, summarizer=summ.Summarizer(client), fetcher=FakeFetcher(), today=TODAY, yes=True)
    assert client.created == []
    assert "spending cap" in capsys.readouterr().out


def weekly(engine, results):
    return main.cmd_weekly(engine, yes=True, summarizer=summ.Summarizer(FakeClient()), fetcher=FakeFetcher(),
                           scrape=lambda _engine, _source: results, today=TODAY)


def test_weekly_fails_when_every_source_failed(engine, capsys):
    assert weekly(engine, [False, False, False]) is False
    assert "Every source failed" in capsys.readouterr().out


def test_weekly_still_succeeds_when_some_sources_failed(engine, capsys):
    assert weekly(engine, [True, False, True]) is True
    assert "1 of 3 sources failed" in capsys.readouterr().out


def test_weekly_accepts_yes(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    seen = {}
    monkeypatch.setattr(main, "cmd_weekly", lambda engine, yes: seen.setdefault("yes", yes) or True)
    assert main.main(["weekly", "--yes"]) == 0
    assert seen == {"yes": True}
