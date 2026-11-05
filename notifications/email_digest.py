"""The update email: what's new since the last email, with the AI summaries.

Sent through Gmail (or any SMTP server) with Python's built-in email tools.
Settings come from .env: SMTP_USER, SMTP_PASSWORD (a Gmail app password), ALERT_TO.
"""
import html
import os
import smtplib
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage

from database.models import Document

RISK_ORDER = {"Action Required": 0, "Watch": 1, "Informational": 2}
RISK_ICONS = {"Action Required": "🔴", "Watch": "🟡", "Informational": "⚪"}
SOURCE_NAMES = {"eurlex": "EUR-Lex", "eu_ai_office": "EU AI Office", "nist": "NIST",
                "federal_register": "Federal Register", "state_laws": "State law"}


@dataclass
class EmailSettings:
    host: str
    port: int
    user: str
    password: str
    to: list[str]

    @classmethod
    def from_env(cls) -> "EmailSettings | None":
        """None if the email settings aren't filled in yet."""
        user, password, to = os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"), os.getenv("ALERT_TO")
        if not (user and password and to):
            return None
        return cls(host=os.getenv("SMTP_HOST") or "smtp.gmail.com", port=int(os.getenv("SMTP_PORT") or 587),
                   user=user, password=password, to=[a.strip() for a in to.split(",") if a.strip()])


def sort_for_email(docs: list[Document]) -> list[Document]:
    """Action Required first, then Watch, then Informational, then documents without a summary."""
    return sorted(docs, key=lambda d: (RISK_ORDER.get(d.risk_level, 3), -(d.date_published or date.min).toordinal()))


def subject_line(docs: list[Document], today: date) -> str:
    urgent = sum(d.risk_level == "Action Required" for d in docs)
    extra = f", {urgent} action required" if urgent else ""
    return f"AI regulation update: {len(docs)} new{extra} ({today:%b} {today.day}, {today.year})"


def _summary(doc: Document) -> dict:
    return {k: v for k, v in (doc.summary_json or {}).items() if k != "_meta"}


def _when(doc: Document) -> str:
    d = doc.date_published
    return f"{d:%b} {d.day}, {d.year}" if d else "date unknown"


def build_text(docs: list[Document], today: date) -> str:
    lines = [subject_line(docs, today), ""]
    for doc in sort_for_email(docs):
        s = _summary(doc)
        level = doc.risk_level or "Not summarized yet"
        lines.append(f"{RISK_ICONS.get(doc.risk_level, '•')} [{level}] {doc.title}")
        lines.append(f"   {SOURCE_NAMES.get(doc.source, doc.source)} · {_when(doc)}")
        for bullet in s.get("tldr") or ([doc.note] if doc.note else []):
            lines.append(f"   - {bullet}")
        if s.get("key_deadline"):
            lines.append(f"   Deadline: {s.get('key_deadline_date') or ''} {s['key_deadline']}".rstrip())
        for action in s.get("actions_required", []):
            lines.append(f"   To do: {action}")
        lines.append(f"   {doc.url}")
        lines.append("")
    lines.append("Summaries are written by AI from the official source. Always check the source before acting.")
    return "\n".join(lines)


def build_html(docs: list[Document], today: date) -> str:
    e = html.escape
    parts = [f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:680px;color:#1f2430">'
             f'<h2 style="margin:0 0 16px">{e(subject_line(docs, today))}</h2>']
    for doc in sort_for_email(docs):
        s = _summary(doc)
        level = doc.risk_level or "Not summarized yet"
        bullets = s.get("tldr") or ([doc.note] if doc.note else [])
        parts.append('<div style="border:1px solid #e3e6eb;border-radius:10px;padding:14px 16px;margin:0 0 12px">')
        parts.append(f'<div style="font-size:13px;color:#5d6475">{RISK_ICONS.get(doc.risk_level, "•")} '
                     f'<b>{e(level)}</b> · {e(SOURCE_NAMES.get(doc.source, doc.source))} · {e(_when(doc))}</div>')
        parts.append(f'<div style="font-size:16px;font-weight:600;margin:6px 0">{e(doc.title)}</div>')
        if bullets:
            parts.append('<ul style="margin:6px 0 6px 18px;padding:0">'
                         + "".join(f"<li>{e(b)}</li>" for b in bullets) + "</ul>")
        if s.get("key_deadline"):
            parts.append(f'<div><b>Deadline:</b> {e(s.get("key_deadline_date") or "")} {e(s["key_deadline"])}</div>')
        if s.get("actions_required"):
            parts.append("<div><b>To do:</b><ul style='margin:4px 0 0 18px;padding:0'>"
                         + "".join(f"<li>{e(a)}</li>" for a in s["actions_required"]) + "</ul></div>")
        parts.append(f'<div style="margin-top:6px"><a href="{e(doc.url)}">Open source ↗</a></div></div>')
    parts.append('<p style="font-size:12px;color:#5d6475">Summaries are written by AI from the official source. '
                 "Always check the source before acting.</p></div>")
    return "".join(parts)


def send(docs: list[Document], settings: EmailSettings, today: date, smtp_class=smtplib.SMTP) -> None:
    message = EmailMessage()
    message["Subject"] = subject_line(docs, today)
    message["From"] = settings.user
    message["To"] = ", ".join(settings.to)
    message.set_content(build_text(docs, today))
    message.add_alternative(build_html(docs, today), subtype="html")
    with smtp_class(settings.host, settings.port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.user, settings.password)
        smtp.send_message(message)
