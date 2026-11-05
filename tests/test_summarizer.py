"""AI summaries, tested with a fake AI client: free, and never touches the real API."""
import json
from datetime import date
from types import SimpleNamespace

import pytest

import main
from database import repository as repo
from database.models import Document
from processors import summarizer as summ
from scrapers.base import DocumentCandidate

TODAY = date(2026, 11, 4)
GOOD_ANSWER = {
    "tldr": ["One.", "Two.", "Three.", "Four (should be dropped)."],
    "who_is_affected": "Providers of general-purpose AI models.",
    "key_deadline_date": "2026-12-02",
    "key_deadline": "New bans apply.",
    "actions_required": ["Check your image tools."],
    "risk_level": "Action Required",
    "categories": ["gpai", "prohibited", "gpai"],
}


class FakeClient:
    """Stands in for anthropic.Anthropic(). Records every request."""

    def __init__(self, answer=GOOD_ANSWER, tokens=1_000, stop_reason="end_turn", token_counts=None):
        self.answer, self.tokens, self.stop_reason = answer, tokens, stop_reason
        self.token_counts = token_counts or {}  # title -> tokens
        self.created, self.counted = [], []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.messages = SimpleNamespace(count_tokens=self._count)

    def _count(self, **kwargs):
        self.counted.append(kwargs)
        content = kwargs["messages"][0]["content"]
        tokens = next((t for title, t in self.token_counts.items() if f"Title: {title}\n" in content), self.tokens)
        return SimpleNamespace(input_tokens=tokens)

    def _create(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(self.answer))],
            stop_reason=self.stop_reason,
            usage=SimpleNamespace(input_tokens=1_000, output_tokens=500),
            model=summ.MODEL,
        )


class FakeFetcher:
    def __init__(self, texts=None):
        self.texts = texts or {}

    def text_for(self, doc):
        return self.texts.get(doc.title)

    def close(self):
        pass


def doc(**fields):
    defaults = dict(source="nist", title="Doc", url="https://x/1", framework="nist_ai_rmf", note="A note.",
                    date_published=date(2026, 10, 1), categories=["other"])
    defaults.update(fields)
    return Document(**defaults)


# --- the summarizer itself ------------------------------------------------

def test_validate_tidies_the_answer():
    clean = summ.validate(GOOD_ANSWER)
    assert clean["tldr"] == ["One.", "Two.", "Three."]
    assert clean["categories"] == ["gpai", "prohibited"]


@pytest.mark.parametrize("bad", [{**GOOD_ANSWER, "risk_level": "Panic"}, {**GOOD_ANSWER, "tldr": []}])
def test_validate_rejects_bad_answers(bad):
    with pytest.raises(summ.SummaryError):
        summ.validate(bad)


def test_summarize_sends_the_right_request_and_records_cost():
    client = FakeClient()
    result = summ.Summarizer(client).summarize(doc(raw_text="Full text here."), TODAY)
    request = client.created[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert request["fallbacks"] == "default"
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert request["output_config"]["effort"] == "low"
    assert request["output_config"]["format"]["schema"] == summ.OUTPUT_SCHEMA
    assert "<document>\nFull text here.\n</document>" in request["messages"][0]["content"]
    meta = result["_meta"]
    assert meta["cost_usd"] == pytest.approx((1_000 * 2 + 500 * 10) / 1_000_000)
    assert meta["based_on"] == "full_text"


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_unusable_responses_raise(stop_reason):
    with pytest.raises(summ.SummaryError):
        summ.Summarizer(FakeClient(stop_reason=stop_reason)).summarize(doc(), TODAY)


def test_without_full_text_it_uses_the_description():
    text = summ.build_input(doc(raw_text=None), TODAY)
    assert "Short description: A note." in text and "full text isn't available" in text


def test_needs_summary_until_done_and_again_if_text_changes():
    d = doc(raw_text="Version 1")
    assert summ.needs_summary(d)
    summ.apply_summary(d, summ.Summarizer(FakeClient()).summarize(d, TODAY))
    assert not summ.needs_summary(d)
    d.raw_text = "Version 2"
    assert summ.needs_summary(d)


def test_apply_summary_replaces_keyword_tags():
    d = doc()
    summ.apply_summary(d, summ.Summarizer(FakeClient()).summarize(d, TODAY))
    assert d.categories == ["gpai", "prohibited"]
    assert d.risk_level == "Action Required"


def test_apply_summary_keeps_old_tags_when_model_has_none():
    d = doc(categories=["governance"])
    summ.apply_summary(d, summ.Summarizer(FakeClient({**GOOD_ANSWER, "categories": []})).summarize(d, TODAY))
    assert d.categories == ["governance"]


# --- the summarize command ------------------------------------------------

@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SUMMARY_BUDGET_USD", raising=False)
    engine = repo.get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    repo.init_db(engine)
    with repo.make_session(engine) as s:
        for n in range(3):
            repo.save_document(s, DocumentCandidate(source="nist", title=f"Doc {n}", url=f"https://x/{n}",
                                                    framework="nist_ai_rmf", note="A note.",
                                                    date_published=date(2026, 10, n + 1)), is_seed=True)
        s.commit()
    return engine


def summaries(engine):
    with repo.make_session(engine) as s:
        return {d.title: d.summary_json for d in s.query(Document)}


def run(engine, client=None, **kwargs):
    kwargs.setdefault("fetcher", FakeFetcher())
    return main.cmd_summarize(engine, summarizer=summ.Summarizer(client) if client else None, today=TODAY, **kwargs)


def test_dry_run_spends_nothing(engine, capsys):
    client = FakeClient()
    assert run(engine, client, dry_run=True)
    assert client.created == []
    assert "Estimated cost" in capsys.readouterr().out


def test_saying_no_spends_nothing(engine):
    client = FakeClient()
    run(engine, client, confirm=lambda _: "n")
    assert client.created == []


def test_summarizes_once_then_never_again(engine, capsys):
    client = FakeClient()
    assert run(engine, client, yes=True)
    assert len(client.created) == 3
    assert all(s and s["risk_level"] == "Action Required" for s in summaries(engine).values())
    run(engine, client, yes=True)
    assert len(client.created) == 3  # no new requests
    assert "Nothing to summarize" in capsys.readouterr().out


def test_limit(engine):
    client = FakeClient()
    run(engine, client, yes=True, limit=1)
    assert len(client.created) == 1


def test_very_long_documents_are_skipped_unless_asked(engine):
    client = FakeClient(token_counts={"Doc 0": 50_000})
    run(engine, client, yes=True)
    assert summaries(engine)["Doc 0"] is None and len(client.created) == 2
    run(engine, client, yes=True, include_large=True)
    assert summaries(engine)["Doc 0"] is not None


def test_spending_cap_stops_the_run(engine, monkeypatch, capsys):
    monkeypatch.setenv("SUMMARY_BUDGET_USD", "0.015")  # each summary here costs about $0.007-0.009
    client = FakeClient()
    run(engine, client, yes=True)
    assert len(client.created) < 3
    assert "spending cap" in capsys.readouterr().out


def test_no_key_means_no_spending(engine, capsys):
    assert run(engine, None, yes=True) is False
    assert "No API key found" in capsys.readouterr().out


def test_dry_run_without_key_gives_a_rough_estimate(engine, capsys):
    assert run(engine, None, dry_run=True)
    assert "rough estimate" in capsys.readouterr().out


def test_full_text_is_fetched_and_saved_first(engine):
    client = FakeClient()
    run(engine, client, yes=True, fetcher=FakeFetcher({"Doc 1": "The whole document."}))
    with repo.make_session(engine) as s:
        d = s.query(Document).filter_by(title="Doc 1").one()
    assert d.raw_text == "The whole document."
    assert d.summary_json["_meta"]["based_on"] == "full_text"


def test_a_failed_summary_is_not_saved_and_the_run_continues(engine):
    client = FakeClient(stop_reason="refusal")
    assert run(engine, client, yes=True) is False
    assert all(s is None for s in summaries(engine).values())
    assert len(client.created) == 3
