"""Helper functions for the database. Everything else uses these, so the rules live in one place."""
import os
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, or_, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, Document, PageFingerprint, ScrapeRun, utcnow
from scrapers.base import DocumentCandidate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_URL = f"sqlite:///{ROOT / 'data' / 'tracker.db'}"


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or os.getenv("DATABASE_URL") or DEFAULT_DB_URL)


def init_db(engine: Engine) -> None:
    """Create any missing tables and columns. Safe to run more than once."""
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)


def _add_missing_columns(engine: Engine) -> None:
    # create_all() doesn't add new columns to tables that already exist.
    # Our new columns are all optional, so adding them is safe.
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    col_type = column.type.compile(engine.dialect)
                    conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}"))


def make_session(engine: Engine) -> Session:
    return sessionmaker(engine, expire_on_commit=False)()


def find_existing(session: Session, candidate: DocumentCandidate) -> Document | None:
    """Find a saved document with the same ID number or the same link."""
    conditions = [Document.url == candidate.url]
    if candidate.external_id:
        conditions.append(Document.external_id == candidate.external_id)
    return session.scalars(select(Document).where(or_(*conditions))).first()


def save_document(
    session: Session, candidate: DocumentCandidate, *, is_seed: bool = False, run_id: int | None = None
) -> bool:
    """Save a document if we don't have it yet. Returns True if it was new."""
    if find_existing(session, candidate):
        return False
    session.add(
        Document(
            source=candidate.source,
            title=candidate.title,
            url=candidate.url,
            external_id=candidate.external_id,
            date_published=candidate.date_published,
            framework=candidate.framework,
            categories=candidate.categories,
            note=candidate.note,
            is_seed=is_seed,
            first_seen_run_id=run_id,
        )
    )
    # Flush so a second copy in the same batch is caught by find_existing.
    session.flush()
    return True


def get_recent(session: Session, days: int | None = None, limit: int | None = None) -> list[Document]:
    """Newest documents first. `days` limits by publish date."""
    query = select(Document).order_by(Document.date_published.desc().nulls_last(), Document.id.desc())
    if days is not None:
        query = query.where(Document.date_published >= date.today() - timedelta(days=days))
    if limit:
        query = query.limit(limit)
    return list(session.scalars(query))


def start_run(session: Session, source: str) -> ScrapeRun:
    run = ScrapeRun(source=source)
    session.add(run)
    session.commit()
    return run


def finish_run(
    session: Session,
    run: ScrapeRun,
    *,
    found: int = 0,
    new: int = 0,
    error: str | None = None,
    partial: bool = False,
) -> None:
    """`partial` means some parts worked and some failed (the error says which)."""
    run.finished_at = utcnow()
    run.found_count = found
    run.new_count = new
    run.status = "partial" if error and partial else "failed" if error else "success"
    run.error = error
    session.commit()


def last_runs(session: Session) -> dict[str, ScrapeRun]:
    """The most recent run for each source (for the "last checked" line)."""
    latest: dict[str, ScrapeRun] = {}
    for run in session.scalars(select(ScrapeRun).order_by(ScrapeRun.started_at)):
        latest[run.source] = run
    return latest


def recent_runs(session: Session, limit: int = 20) -> list[ScrapeRun]:
    return list(session.scalars(select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(limit)))


def first_run_ids(session: Session) -> set[int]:
    """The first run that worked, for each source. Everything it found is old
    material the source already had (a "backfill"), not news."""
    query = select(func.min(ScrapeRun.id)).where(ScrapeRun.status != "failed").group_by(ScrapeRun.source)
    return set(session.scalars(query))


def is_new(doc: Document, backfill_runs: set[int]) -> bool:
    """Really new: found by a scraper after that scraper's first run. Not starting data."""
    return not doc.is_seed and doc.first_seen_run_id is not None and doc.first_seen_run_id not in backfill_runs


def get_new_documents(session: Session, days: int = 7) -> list[Document]:
    """Documents that are really new and were found in the last `days` days."""
    since = utcnow() - timedelta(days=days)
    query = select(Document).where(Document.date_detected >= since).order_by(Document.date_detected.desc())
    backfill_runs = first_run_ids(session)
    return [doc for doc in session.scalars(query) if is_new(doc, backfill_runs)]


def get_unemailed_new(session: Session) -> list[Document]:
    """Really new documents that haven't been in an update email yet."""
    backfill_runs = first_run_ids(session)
    query = select(Document).where(Document.notified_at.is_(None)).order_by(Document.date_detected.desc())
    return [doc for doc in session.scalars(query) if is_new(doc, backfill_runs)]


def mark_emailed(session: Session, docs: list[Document]) -> None:
    now = utcnow()
    for doc in docs:
        doc.notified_at = now
    session.commit()


def last_fingerprint(session: Session, url: str) -> PageFingerprint | None:
    query = select(PageFingerprint).where(PageFingerprint.url == url).order_by(PageFingerprint.id.desc())
    return session.scalars(query).first()


def save_fingerprint(session: Session, url: str, content_hash: str, content_text: str) -> None:
    session.add(PageFingerprint(url=url, content_hash=content_hash, content_text=content_text))
    session.flush()
