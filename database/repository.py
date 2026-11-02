"""Helper functions for the database. Everything else uses these, so the rules live in one place."""
import os
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, Document, ScrapeRun, utcnow
from scrapers.base import DocumentCandidate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_URL = f"sqlite:///{ROOT / 'data' / 'tracker.db'}"


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or os.getenv("DATABASE_URL") or DEFAULT_DB_URL)


def init_db(engine: Engine) -> None:
    """Create any missing tables. Safe to run more than once."""
    Base.metadata.create_all(engine)


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
    session: Session, run: ScrapeRun, *, found: int = 0, new: int = 0, error: str | None = None
) -> None:
    run.finished_at = utcnow()
    run.found_count = found
    run.new_count = new
    run.status = "failed" if error else "success"
    run.error = error
    session.commit()


def last_runs(session: Session) -> dict[str, ScrapeRun]:
    """The most recent run for each source (for the "last checked" line)."""
    latest: dict[str, ScrapeRun] = {}
    for run in session.scalars(select(ScrapeRun).order_by(ScrapeRun.started_at)):
        latest[run.source] = run
    return latest
