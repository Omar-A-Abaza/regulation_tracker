"""Commands for the AI Regulation Tracker.

  python main.py init-db                 create the empty database
  python main.py seed                    load the starting documents
  python main.py scrape --source eurlex  run one scraper, "pages" for the page watcher, or "all"
  python main.py list                    print the latest documents
  python main.py new                     print what's really new (last 7 days)
  python main.py runs                    print the scrape log
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

from database import repository as repo
from processors.classifier import classify
from processors.differ import summarize_change
from scrapers.base import BaseScraper, DocumentCandidate
from scrapers.eu_ai_office import EuAiOfficeScraper
from scrapers.eurlex import EurLexScraper, EurLexVersionsScraper
from scrapers.federal_register import FederalRegisterScraper
from scrapers.nist import NistScraper
from scrapers.page_watcher import PageWatcher, WatchedPage, fingerprint, load_pages

ROOT = Path(__file__).resolve().parent
SEED_FILE = ROOT / "data" / "seed_documents.yaml"

SCRAPERS: dict[str, type[BaseScraper]] = {
    scraper.name: scraper
    for scraper in (EurLexScraper, EurLexVersionsScraper, EuAiOfficeScraper, NistScraper, FederalRegisterScraper)
}


def cmd_init_db(engine) -> None:
    (ROOT / "data").mkdir(exist_ok=True)
    repo.init_db(engine)
    print(f"Database ready: {engine.url}")


def cmd_seed(engine) -> None:
    rows = yaml.safe_load(SEED_FILE.read_text())["documents"]
    with repo.make_session(engine) as session:
        new = sum(repo.save_document(session, DocumentCandidate(**row), is_seed=True) for row in rows)
        session.commit()
    print(f"Starting data: {len(rows)} documents → {new} new, {len(rows) - new} already saved")


def run_scraper(engine, scraper_cls: type[BaseScraper]) -> bool:
    """Run one scraper, save what it finds, and log the run. Returns True if it worked."""
    scraper = scraper_cls()
    with repo.make_session(engine) as session:
        run = repo.start_run(session, scraper.name)
        try:
            found = scraper.fetch()
            new_docs = [doc for doc in found if repo.save_document(session, doc, run_id=run.id)]
        except Exception as e:
            session.rollback()
            repo.finish_run(session, run, error=f"{type(e).__name__}: {e}")
            print(f"{scraper.label}: FAILED — {type(e).__name__}: {e}")
            return False
        finally:
            scraper.close()
        repo.finish_run(session, run, found=len(found), new=len(new_docs))

    print(f"{scraper.label}: found {len(found)} documents → {len(new_docs)} new, {len(found) - len(new_docs)} already saved")
    for doc in new_docs:
        print(f"  NEW  {doc.date_published or '????-??-??'}  {doc.title[:100]}")
    return True


def check_page(session, page: WatchedPage, text: str, run_id: int) -> DocumentCandidate | None:
    """Compare a page with its last fingerprint. Saves an "updated" document if it changed.
    The first time we see a page, we only save its fingerprint (nothing to compare with)."""
    new_hash = fingerprint(text)
    last = repo.last_fingerprint(session, page.url)
    if last and last.content_hash == new_hash:
        return None
    repo.save_fingerprint(session, page.url, new_hash, text)
    if last is None:
        return None
    note = summarize_change(last.content_text or "", text)
    change = DocumentCandidate(
        source=page.source,
        title=f"Page updated: {page.name}",
        # The fragment keeps each change's link unique; it still opens the page.
        url=f"{page.url}#update-{new_hash[:12]}",
        framework=page.framework,
        date_published=date.today(),
        external_id=f"page:{page.url}:{new_hash[:12]}",
        note=note,
        categories=classify(f"{page.name} {note}"),
    )
    repo.save_document(session, change, run_id=run_id)
    return change


def run_page_watch(engine, watcher: PageWatcher | None = None, pages: list[WatchedPage] | None = None) -> bool:
    """Check every watched page and log the run. One page failing doesn't stop the others."""
    watcher = watcher or PageWatcher()
    pages = pages if pages is not None else load_pages()
    changes, errors = [], []
    with repo.make_session(engine) as session:
        run = repo.start_run(session, watcher.name)
        for page in pages:
            try:
                change = check_page(session, page, watcher.page_text(page), run.id)
            except Exception as e:
                errors.append(f"{page.name}: {type(e).__name__}: {e}")
                continue
            if change:
                changes.append(change)
        watcher.close()
        error = "; ".join(errors) or None
        repo.finish_run(session, run, found=len(pages), new=len(changes), error=error,
                        partial=len(errors) < len(pages))

    print(f"{watcher.label}: checked {len(pages) - len(errors)} of {len(pages)} pages → {len(changes)} changed")
    for change in changes:
        print(f"  CHANGED  {change.title}\n           {change.note}")
    for error in errors:
        print(f"  FAILED   {error}")
    return not errors


def cmd_scrape(engine, source: str) -> bool:
    names = list(SCRAPERS) if source == "all" else [] if source == "pages" else [source]
    results = [run_scraper(engine, SCRAPERS[name]) for name in names]
    if source in ("all", "pages"):
        results.append(run_page_watch(engine))
    return all(results)


def cmd_list(engine, limit: int) -> None:
    with repo.make_session(engine) as session:
        backfill_runs = repo.first_run_ids(session)
        for doc in repo.get_recent(session, limit=limit):
            if doc.is_seed:
                tag = "  (starting data)"
            elif not repo.is_new(doc, backfill_runs):
                tag = "  (found on first run)"
            else:
                tag = ""
            print(f"{doc.date_published or '????-??-??'}  {doc.source:<16} {doc.title[:85]}{tag}")
        print()
        for source, run in sorted(repo.last_runs(session).items()):
            print(f"Last checked {source}: {run.started_at:%Y-%m-%d %H:%M} UTC — {run.status}, {run.new_count} new")


def cmd_new(engine, days: int) -> None:
    with repo.make_session(engine) as session:
        docs = repo.get_new_documents(session, days=days)
    if not docs:
        print(f"Nothing new in the last {days} days.")
        return
    print(f"{len(docs)} new in the last {days} days:")
    for doc in docs:
        print(f"  {doc.date_detected:%Y-%m-%d}  {doc.source:<16} {doc.title[:85]}")
        if doc.note:
            print(f"  {'':<10}  {'':<16} {doc.note[:120]}")


def cmd_runs(engine, limit: int) -> None:
    with repo.make_session(engine) as session:
        for run in repo.recent_runs(session, limit=limit):
            took = f"{(run.finished_at - run.started_at).total_seconds():.0f}s" if run.finished_at else "-"
            print(f"#{run.id:<4} {run.started_at:%Y-%m-%d %H:%M}  {run.source:<17} {run.status:<8} "
                  f"found {run.found_count:<3} new {run.new_count:<3} {took:>5}")
            if run.error:
                print(f"       {run.error[:150]}")


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="AI Regulation Tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="create the empty database")
    sub.add_parser("seed", help="load the starting documents")
    scrape = sub.add_parser("scrape", help="run scrapers")
    scrape.add_argument("--source", choices=[*SCRAPERS, "pages", "all"], default="all")
    listing = sub.add_parser("list", help="print the latest documents")
    listing.add_argument("--limit", type=int, default=25)
    new = sub.add_parser("new", help="print what's really new")
    new.add_argument("--days", type=int, default=7)
    runs = sub.add_parser("runs", help="print the scrape log")
    runs.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    engine = repo.get_engine()
    repo.init_db(engine)  # makes sure the tables exist for every command

    if args.command == "init-db":
        cmd_init_db(engine)
    elif args.command == "seed":
        cmd_seed(engine)
    elif args.command == "scrape":
        return 0 if cmd_scrape(engine, args.source) else 1
    elif args.command == "list":
        cmd_list(engine, args.limit)
    elif args.command == "new":
        cmd_new(engine, args.days)
    elif args.command == "runs":
        cmd_runs(engine, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
