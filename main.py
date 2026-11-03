"""Commands for the AI Regulation Tracker.

  python main.py init-db                 create the empty database
  python main.py seed                    load the starting documents
  python main.py scrape --source eurlex  run a scraper (or --source all)
  python main.py list                    print the latest documents
"""
import argparse
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from database import repository as repo
from scrapers.base import BaseScraper, DocumentCandidate
from scrapers.eu_ai_office import EuAiOfficeScraper
from scrapers.eurlex import EurLexScraper
from scrapers.federal_register import FederalRegisterScraper
from scrapers.nist import NistScraper

ROOT = Path(__file__).resolve().parent
SEED_FILE = ROOT / "data" / "seed_documents.yaml"

SCRAPERS: dict[str, type[BaseScraper]] = {
    scraper.name: scraper
    for scraper in (EurLexScraper, EuAiOfficeScraper, NistScraper, FederalRegisterScraper)
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


def cmd_scrape(engine, source: str) -> bool:
    names = list(SCRAPERS) if source == "all" else [source]
    results = [run_scraper(engine, SCRAPERS[name]) for name in names]
    return all(results)


def cmd_list(engine, limit: int) -> None:
    with repo.make_session(engine) as session:
        docs = repo.get_recent(session, limit=limit)
        for doc in docs:
            seed = "  (starting data)" if doc.is_seed else ""
            print(f"{doc.date_published or '????-??-??'}  {doc.source:<16} {doc.title[:85]}{seed}")
        print()
        for source, run in sorted(repo.last_runs(session).items()):
            print(f"Last checked {source}: {run.started_at:%Y-%m-%d %H:%M} UTC — {run.status}, {run.new_count} new")


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="AI Regulation Tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="create the empty database")
    sub.add_parser("seed", help="load the starting documents")
    scrape = sub.add_parser("scrape", help="run scrapers")
    scrape.add_argument("--source", choices=[*SCRAPERS, "all"], default="all")
    listing = sub.add_parser("list", help="print the latest documents")
    listing.add_argument("--limit", type=int, default=25)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
