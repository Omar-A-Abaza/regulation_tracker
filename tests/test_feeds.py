"""Tests for the two news-feed scrapers: NIST and the EU AI Office."""
from datetime import date
from pathlib import Path

from scrapers import eu_ai_office, nist
from scrapers.base import read_rss_items

FIXTURES = Path(__file__).parent / "fixtures"


def nist_docs():
    return nist.select_items(read_rss_items((FIXTURES / "nist_super_intelligence_rss.xml").read_bytes()))


def eu_docs():
    return eu_ai_office.select_items(read_rss_items((FIXTURES / "eu_ai_office_rss.xml").read_bytes()))


def test_read_rss_items():
    items = read_rss_items((FIXTURES / "eu_ai_office_rss.xml").read_bytes())
    assert len(items) == 10
    assert all(i.title and i.link.startswith("https://") for i in items)


def test_nist_keeps_ai_news_only():
    docs = nist_docs()
    assert docs
    assert all("/news-events/news/" in d.url for d in docs)  # no events
    assert not any(d.title.startswith("Spotlight") for d in docs)
    assert not any("USAJobs" in d.title or "Allocates" in d.title for d in docs)
    assert any(d.title.startswith("Key Practices for Incident Readiness") for d in docs)


def test_nist_model_evaluations_count_as_gpai():
    doc = next(d for d in nist_docs() if d.title == "CAISI Evaluation of DeepSeek V4 Pro")
    assert "gpai" in doc.categories
    assert doc.date_published == date(2026, 5, 1)


def test_nist_note_does_not_repeat_title():
    doc = next(d for d in nist_docs() if d.title.startswith("Key Practices for Incident Readiness"))
    assert not (doc.note or "").startswith("Key Practices")


def test_eu_feed_keeps_ai_items_and_skips_the_rest():
    titles = {d.title for d in eu_docs()}
    assert "First harmonised standard supporting the AI Act published in the Official Journal" in titles
    assert not any("Temu" in t or "Booking.com" in t for t in titles)  # Digital Services Act, not AI
    assert not any("AI Innovation Month" in t for t in titles)  # event


def test_eu_note_is_the_feed_summary():
    doc = next(d for d in eu_docs() if d.title.startswith("First harmonised standard"))
    assert doc.note.startswith("The European Commission has published the reference")
    assert doc.framework == "eu_ai_act"
    assert doc.date_published == date(2026, 10, 19)
