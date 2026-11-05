"""The update email, tested with a fake mail server (nothing is really sent)."""
from datetime import date

import pytest

import main
from database import repository as repo
from database.models import Document
from notifications import email_digest
from scrapers.base import BaseScraper, DocumentCandidate

TODAY = date(2026, 11, 4)
SETTINGS = email_digest.EmailSettings(host="smtp.test", port=587, user="me@gmail.com", password="pw",
                                      to=["boss@example.com"])
SUMMARY = {"tldr": ["Bans AI-made fake images.", "Applies from Dec 2."], "who_is_affected": "AI providers",
           "key_deadline_date": "2026-12-02", "key_deadline": "Ban applies.",
           "actions_required": ["Check image filters."], "risk_level": "Action Required", "categories": ["gpai"],
           "_meta": {}}


class FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout):
        self.host = host

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        self.user = user

    def send_message(self, message):
        FakeSMTP.sent.append(message)


def d(title, risk=None, summary=None, published=date(2026, 11, 1)):
    return Document(title=title, source="federal_register", url=f"https://x/{title}", framework="us_federal",
                    risk_level=risk, summary_json=summary, note="A note.", date_published=published)


def test_action_required_comes_first():
    docs = [d("Info", "Informational"), d("None"), d("Act", "Action Required"), d("Watch", "Watch")]
    assert [x.title for x in email_digest.sort_for_email(docs)] == ["Act", "Watch", "Info", "None"]


def test_subject_line_counts_urgent_items():
    assert email_digest.subject_line([d("a", "Action Required"), d("b", "Watch")], TODAY) == \
        "AI regulation update: 2 new, 1 action required (Nov 4, 2026)"


def test_text_has_summary_deadline_and_actions():
    text = email_digest.build_text([d("EO", "Action Required", SUMMARY)], TODAY)
    assert "Bans AI-made fake images." in text
    assert "Deadline: 2026-12-02 Ban applies." in text
    assert "To do: Check image filters." in text


def test_unsummarized_document_shows_its_note():
    assert "A note." in email_digest.build_text([d("No summary")], TODAY)


def test_html_is_escaped():
    assert "<script>" not in email_digest.build_html([d("<script>alert(1)</script>")], TODAY)


def test_send_builds_a_two_part_email():
    FakeSMTP.sent = []
    email_digest.send([d("EO", "Action Required", SUMMARY)], SETTINGS, TODAY, smtp_class=FakeSMTP)
    [message] = FakeSMTP.sent
    assert message["To"] == "boss@example.com"
    assert message.get_body("plain") is not None and message.get_body("html") is not None


def test_settings_missing_means_none(monkeypatch):
    for key in ("SMTP_USER", "SMTP_PASSWORD", "ALERT_TO"):
        monkeypatch.delenv(key, raising=False)
    assert email_digest.EmailSettings.from_env() is None


# --- the digest command ---------------------------------------------------

class OneDocScraper(BaseScraper):
    name, label = "fake", "Fake"
    batches = []

    def fetch(self):
        return self.batches.pop(0)


@pytest.fixture
def engine(tmp_path):
    engine = repo.get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    repo.init_db(engine)
    FakeSMTP.sent = []
    return engine


def add_new_document(engine):
    """A first run (backfill, never emailed), then a second run that finds something really new."""
    old = DocumentCandidate(source="nist", title="Old", url="https://x/old", framework="nist_ai_rmf")
    new = DocumentCandidate(source="nist", title="New", url="https://x/new", framework="nist_ai_rmf", note="Fresh.")
    OneDocScraper.batches = [[old], [old, new]]
    main.run_scraper(engine, OneDocScraper)
    main.run_scraper(engine, OneDocScraper)


def test_nothing_new_sends_nothing(engine, capsys):
    assert main.cmd_digest(engine, settings=SETTINGS, smtp_class=FakeSMTP, today=TODAY)
    assert FakeSMTP.sent == [] and "Nothing new" in capsys.readouterr().out


def test_sends_new_items_once(engine):
    add_new_document(engine)
    assert main.cmd_digest(engine, settings=SETTINGS, smtp_class=FakeSMTP, today=TODAY)
    assert len(FakeSMTP.sent) == 1
    assert FakeSMTP.sent[0]["Subject"] == "AI regulation update: 1 new (Nov 4, 2026)"
    main.cmd_digest(engine, settings=SETTINGS, smtp_class=FakeSMTP, today=TODAY)
    assert len(FakeSMTP.sent) == 1  # already emailed


def test_preview_does_not_send_or_mark(engine, capsys):
    add_new_document(engine)
    main.cmd_digest(engine, preview=True, today=TODAY)
    assert "Fresh." in capsys.readouterr().out
    with repo.make_session(engine) as s:
        assert len(repo.get_unemailed_new(s)) == 1


def test_missing_settings_prints_help_and_does_not_mark(engine, monkeypatch, capsys):
    for key in ("SMTP_USER", "SMTP_PASSWORD", "ALERT_TO"):
        monkeypatch.delenv(key, raising=False)
    add_new_document(engine)
    assert main.cmd_digest(engine, today=TODAY) is False
    assert "Email isn't set up yet" in capsys.readouterr().out
    with repo.make_session(engine) as s:
        assert len(repo.get_unemailed_new(s)) == 1


def test_test_email_does_not_mark_anything(engine):
    with repo.make_session(engine) as s:
        repo.save_document(s, DocumentCandidate(source="nist", title="Summed", url="https://x/s",
                                                framework="nist_ai_rmf"), is_seed=True)
        s.query(Document).one().summary_json = SUMMARY
        s.commit()
    assert main.cmd_digest(engine, test=True, settings=SETTINGS, smtp_class=FakeSMTP, today=TODAY)
    assert len(FakeSMTP.sent) == 1
    with repo.make_session(engine) as s:
        assert s.query(Document).one().notified_at is None
