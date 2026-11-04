"""Data for the dashboard: loading from the database, filtering, and small helpers.

No Streamlit in this file, so it's easy to test.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.engine import Engine

from database import repository as repo
from database.models import Document

ROOT = Path(__file__).resolve().parent.parent
TIMELINE_FILE = ROOT / "data" / "timeline.yaml"

FRAMEWORKS = {"eu_ai_act": "EU AI Act", "nist_ai_rmf": "NIST", "us_federal": "US federal", "us_state": "US states"}
CATEGORIES = {
    "gpai": "GPAI", "high_risk": "High-risk", "prohibited": "Banned uses", "penalties": "Fines & enforcement",
    "transparency": "Transparency", "governance": "Governance", "other": "Other",
}
SOURCES = {
    "eurlex": "EUR-Lex", "eu_ai_office": "EU AI Office", "nist": "NIST",
    "federal_register": "Federal Register", "state_laws": "State law",
}
# Names used in the scrape log (one per scraper).
RUN_SOURCES = {
    "eurlex": "EUR-Lex", "eurlex_versions": "EUR-Lex (AI Act text versions)", "eu_ai_office": "EU AI Office",
    "nist": "NIST", "federal_register": "Federal Register", "pages": "Watched pages",
}
DATE_RANGES = {"Last 30 days": 30, "Last 90 days": 90, "Last 12 months": 365, "All time": None}
# Short forms people type, and the full names our documents use.
SEARCH_ALIASES = {
    "ftc": "federal trade commission",
    "eo": "executive order",
    "caisi": "center for ai standards",
    "fda": "food and drug administration",
    "doe": "energy department",
    "dhs": "homeland security",
}


@dataclass
class DocRow:
    id: int
    source: str
    title: str
    url: str
    date_published: date | None
    date_detected: datetime
    framework: str
    note: str | None
    status: str  # "new", "backfill" (found on a scraper's first run) or "seed" (starting data)
    categories: list[str] = field(default_factory=list)
    summary: dict | None = None

    @property
    def is_new(self) -> bool:
        return self.status == "new"


@dataclass
class SourceHealth:
    key: str
    label: str
    status: str
    last_checked: datetime
    new_count: int
    error: str | None


def load_documents(engine: Engine) -> list[DocRow]:
    with repo.make_session(engine) as session:
        backfill_runs = repo.first_run_ids(session)
        rows = []
        for doc in session.scalars(select(Document)):
            status = "seed" if doc.is_seed else "new" if repo.is_new(doc, backfill_runs) else "backfill"
            rows.append(DocRow(
                id=doc.id, source=doc.source, title=doc.title, url=doc.url, date_published=doc.date_published,
                date_detected=doc.date_detected, framework=doc.framework, note=doc.note, status=status,
                categories=list(doc.categories or []), summary=doc.summary_json,
            ))
    return sort_newest_first(rows)


def sort_newest_first(docs: list[DocRow]) -> list[DocRow]:
    # Documents with no publish date go last.
    return sorted(docs, key=lambda d: (d.date_published is not None, d.date_published or date.min, d.id), reverse=True)


def filter_documents(
    docs: list[DocRow],
    *,
    today: date,
    frameworks: list[str] | None = None,
    categories: list[str] | None = None,
    sources: list[str] | None = None,
    days: int | None = None,
    query: str = "",
) -> list[DocRow]:
    """Empty filter lists mean "everything"."""
    query = query.strip().lower()
    terms = [query, SEARCH_ALIASES[query]] if query in SEARCH_ALIASES else [query]
    since = today - timedelta(days=days) if days is not None else None
    kept = []
    for doc in docs:
        if frameworks and doc.framework not in frameworks:
            continue
        if categories and not set(doc.categories) & set(categories):
            continue
        if sources and doc.source not in sources:
            continue
        if since and (doc.date_published is None or doc.date_published < since):
            continue
        text = f"{doc.title} {doc.note or ''}".lower()
        if query and not any(term in text for term in terms):
            continue
        kept.append(doc)
    return kept


def new_this_week(docs: list[DocRow], now: datetime, days: int = 7) -> list[DocRow]:
    """Really new documents (not starting data, not first-run backfill) found in the last `days` days."""
    since = now - timedelta(days=days)
    return [d for d in docs if d.is_new and d.date_detected >= since]


def load_health(engine: Engine) -> list[SourceHealth]:
    with repo.make_session(engine) as session:
        runs = repo.last_runs(session)
    return [
        SourceHealth(key=key, label=RUN_SOURCES.get(key, key), status=run.status, last_checked=run.started_at,
                     new_count=run.new_count, error=run.error)
        for key, run in sorted(runs.items(), key=lambda kv: RUN_SOURCES.get(kv[0], kv[0]))
    ]


def load_milestones(path: Path = TIMELINE_FILE) -> list[dict]:
    return sorted(yaml.safe_load(path.read_text())["milestones"], key=lambda m: m["date"])


def next_milestone(milestones: list[dict], today: date) -> dict | None:
    return next((m for m in milestones if m["date"] >= today), None)


# --- timeline -------------------------------------------------------------

JURISDICTIONS = {"EU": "EU", "US-CA": "California", "US-CO": "Colorado"}
SOON_DAYS = 90
# Each state has an icon and a label, so color is never the only clue.
MILESTONE_STATES = {"done": "✅ In force", "soon": f"⏳ Within {SOON_DAYS} days", "later": "🗓️ Later"}


def milestone_state(milestone: dict, today: date) -> str:
    days = (milestone["date"] - today).days
    return "done" if days < 0 else "soon" if days <= SOON_DAYS else "later"


def days_label(when: date, today: date) -> str:
    days = (when - today).days
    if days == 0:
        return "today"
    unit = "day" if abs(days) == 1 else "days"
    return f"in {days} {unit}" if days > 0 else f"{-days} {unit} ago"


def filter_milestones(
    milestones: list[dict], *, jurisdictions: list[str] | None = None, categories: list[str] | None = None
) -> list[dict]:
    """Empty filter lists mean "everything"."""
    kept = []
    for m in milestones:
        if jurisdictions and m["jurisdiction"] not in jurisdictions:
            continue
        if categories and not set(m.get("categories", [])) & set(categories):
            continue
        kept.append(m)
    return kept


def moved_milestones(milestones: list[dict]) -> list[dict]:
    """Deadlines a later law pushed back (they have an original_date)."""
    return [m for m in milestones if m.get("original_date")]


def time_ago(then: datetime, now: datetime) -> str:
    seconds = (now - then).total_seconds()
    if seconds < 60:
        return "just now"
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            n = int(seconds // size)
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    return "just now"


def nice_date(d: date) -> str:
    return f"{d:%b} {d.day}, {d.year}"
