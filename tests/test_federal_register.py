import json
from datetime import date
from pathlib import Path

from scrapers.federal_register import select_documents, text_is_about_ai, title_is_about_ai

FIXTURES = Path(__file__).parent / "fixtures"
PRESIDENTIAL = json.loads((FIXTURES / "federal_register_presidential.json").read_text())
AGENCY = json.loads((FIXTURES / "federal_register_agency.json").read_text())

AI_HEAVY = "The Federal Government will use artificial intelligence. AI " * 10
MENTIONS_ONCE = "This order is about mortgage credit. " * 100 + "It also touches on AI."


def titles(docs):
    return {d.title for d in docs}


def test_title_check():
    assert title_is_about_ai("Inaugurating the Era of Super Intelligence")
    assert title_is_about_ai("AI-Enabled Optimization of Early-Phase Clinical Trials")
    assert not title_is_about_ai("Promoting Access to Mortgage Credit")
    assert not title_is_about_ai("Maintaining the database")  # "ai" inside a word


def test_text_check():
    assert text_is_about_ai(AI_HEAVY)
    assert not text_is_about_ai(MENTIONS_ONCE)


def test_orders_that_only_mention_ai_are_dropped():
    docs = select_documents(PRESIDENTIAL, [], lambda d: MENTIONS_ONCE)
    kept = titles(docs)
    assert "EO 14434 — Inaugurating the Era of Super Intelligence" in kept
    assert not any("Mortgage Credit" in t for t in kept)
    assert not any("Veterans" in t for t in kept)


def test_orders_kept_when_text_is_about_ai():
    # "Launching the Genesis Mission" has no AI word in the title, but its text is about AI.
    get_text = lambda d: AI_HEAVY if "Genesis" in d["title"] else MENTIONS_ONCE
    assert "EO 14363 — Launching the Genesis Mission" in titles(select_documents(PRESIDENTIAL, [], get_text))


def test_agency_documents_need_ai_in_title_and_skip_paperwork():
    kept = titles(select_documents([], AGENCY, lambda d: ""))
    assert "Policy Statement Concerning the Suppression of Accuracy in Artificial Intelligence Systems" in kept
    assert not any("Information Collection" in t for t in kept)
    assert len(kept) < 40  # out of 412 that mention AI somewhere


def test_executive_order_fields():
    doc = next(d for d in select_documents(PRESIDENTIAL, [], lambda d: "") if d.external_id == "2026-20321")
    assert doc.date_published == date(2026, 10, 2)
    assert doc.framework == "us_federal"
    assert doc.note == "Executive Order, signed Sep 29, 2026."


def test_ftc_case_is_tagged_as_penalties():
    doc = next(d for d in select_documents([], AGENCY, lambda d: "") if "Workado" in d.title)
    assert "penalties" in doc.categories
    assert doc.note == "Notice from Federal Trade Commission."
