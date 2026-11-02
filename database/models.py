"""The 3 database tables: documents, page_fingerprints, scrape_runs."""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # SQLite has no time zones, so we store plain UTC times.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class ScrapeRun(Base):
    """One row per scraper run: when, did it work, how many new items."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(20), default="running")  # running / success / failed
    found_count: Mapped[int] = mapped_column(default=0)
    new_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)


class Document(Base):
    """One row per law, guide or update."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    # The source's own ID (e.g. EU CELEX number). Stops the same law being saved twice.
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    date_published: Mapped[date | None]
    date_detected: Mapped[datetime] = mapped_column(default=utcnow)
    framework: Mapped[str] = mapped_column(String(50), index=True)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    note: Mapped[str | None] = mapped_column(Text)
    is_seed: Mapped[bool] = mapped_column(default=False)
    first_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_runs.id"))

    # Filled in later weeks.
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[dict | None] = mapped_column(JSON)  # Week 2: AI summary
    risk_level: Mapped[str | None] = mapped_column(String(30))  # Week 2
    notified_at: Mapped[datetime | None]  # alerts (to-do)


class PageFingerprint(Base):
    """The last fingerprint (hash) of a watched page, to spot changes. Used from Day 4."""

    __tablename__ = "page_fingerprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(default=utcnow)
