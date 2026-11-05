"""Commands for the AI Regulation Tracker.

  python main.py init-db                 create the empty database
  python main.py seed                    load the starting documents
  python main.py scrape --source eurlex  run one scraper, "pages" for the page watcher, or "all"
  python main.py list                    print the latest documents
  python main.py new                     print what's really new (last 7 days)
  python main.py runs                    print the scrape log
  python main.py summarize --dry-run     show what AI summaries would cost (spends nothing)
  python main.py summarize               write AI summaries for documents that don't have one
  python main.py digest                  email what's new since the last email (--preview to just print it)
  python main.py weekly                  scrape, summarize what's new, and email it
"""
import argparse
import os
import smtplib
import sys
from datetime import date
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv
from sqlalchemy import select

from database import repository as repo
from database.models import Document
from notifications import email_digest
from processors import summarizer as summ
from processors.classifier import classify
from processors.differ import summarize_change
from processors.fulltext import FullTextFetcher, save_text
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


NO_KEY_HELP = """No API key found. To add yours:
  1. cp .env.example .env      (only the first time)
  2. code .env                 (opens it in VS Code)
  3. Fill in the line:  ANTHROPIC_API_KEY=sk-ant-...
Nothing was spent."""

NO_EMAIL_HELP = """Email isn't set up yet. In your .env file, fill in:
  SMTP_USER=your.address@gmail.com
  SMTP_PASSWORD=your 16-letter Gmail app password
  ALERT_TO=where.to.send@example.com"""


def fetch_missing_text(session, docs: list[Document], fetcher: FullTextFetcher | None = None) -> None:
    """Download the full text of documents that don't have it yet (free: just reading public pages)."""
    missing = [d for d in docs if not d.raw_text]
    if not missing:
        return
    print(f"Getting full text for {len(missing)} documents...")
    fetcher = fetcher or FullTextFetcher()
    for doc in missing:
        try:
            text = fetcher.text_for(doc)
        except Exception as e:
            print(f"  couldn't get the text of \"{doc.title[:60]}\" ({type(e).__name__}); will use its description")
            continue
        if text:
            save_text(doc, text)
    fetcher.close()
    session.commit()


def plan_summaries(docs: list[Document], summarizer, today: date, *, limit: int | None,
                   include_large: bool) -> summ.Plan:
    """Count tokens and pick which documents fit. Without a key, uses a rough estimate."""
    plan = summ.Plan(docs=[], tokens={}, too_large=[], exact=summarizer is not None)
    for doc in docs:
        if limit and len(plan.docs) >= limit:
            break
        tokens = (summarizer.count_tokens(doc, today) if summarizer
                  else round(len(summ.build_input(doc, today)) / 3.5))  # rough: no key to count with
        plan.tokens[doc.id] = tokens
        if tokens > summ.MAX_INPUT_TOKENS and not include_large:
            plan.too_large.append(doc)
        else:
            plan.docs.append(doc)
    return plan


def cmd_summarize(engine, *, dry_run=False, limit=None, yes=False, include_large=False, only_new=False,
                  summarizer=None, fetcher=None, confirm=input, today=None) -> bool:
    today = today or date.today()
    budget = summ.budget_from_env()
    with repo.make_session(engine) as session:
        backfill_runs = repo.first_run_ids(session)
        docs = [d for d in session.scalars(select(Document)) if summ.needs_summary(d)]
        if only_new:
            docs = [d for d in docs if repo.is_new(d, backfill_runs)]
        # Really new documents first, then newest first.
        docs.sort(key=lambda d: (not repo.is_new(d, backfill_runs), -(d.date_published or date.min).toordinal()))
        if not docs:
            print("Nothing to summarize: every document already has a summary.")
            return True

        fetch_missing_text(session, docs, fetcher)
        has_key = summarizer is not None or bool(os.getenv("ANTHROPIC_API_KEY"))
        if has_key and summarizer is None:
            summarizer = summ.Summarizer()
        try:
            plan = plan_summaries(docs, summarizer, today, limit=limit, include_large=include_large)
        except anthropic.AuthenticationError:
            print("Your API key wasn't accepted. Check ANTHROPIC_API_KEY in .env. Nothing was spent.")
            return False
        except anthropic.APIError as e:
            print(f"Couldn't count tokens ({type(e).__name__}: {e}). Nothing was spent.")
            return False

        all_summarized = session.scalars(select(Document).where(Document.summary_json.is_not(None))).all()
        avg_output = summ.average_output_tokens(list(all_summarized))
        estimate = plan.estimated_cost(avg_output)
        print(f"\nSummaries with Claude Sonnet 5.5: {len(plan.docs)} documents")
        if plan.too_large:
            print(f"  Skipped {len(plan.too_large)} very long documents (over {summ.MAX_INPUT_TOKENS:,} tokens). "
                  "Add --include-large to include them:")
            for doc in plan.too_large:
                print(f"    - {doc.title[:70]} ({plan.tokens[doc.id]:,} tokens)")
        input_tokens = sum(plan.tokens[d.id] for d in plan.docs)
        kind = "counted" if plan.exact else "rough estimate, add your API key for an exact count"
        print(f"  Text to read: {input_tokens:,} tokens ({kind})")
        print(f"  Estimated cost: about ${estimate:.2f}  (spending cap for this run: ${budget:.2f})")
        if estimate > budget:
            print("  The run will stop when it reaches the cap. Run it again later to continue.")
        if dry_run or not plan.docs:
            print("Nothing was spent.")
            return True
        if not has_key:
            print(NO_KEY_HELP)
            return False
        if not yes and confirm("Go ahead? (y/n) ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Nothing was spent.")
            return True

        spent, done, failed = 0.0, 0, 0
        for doc in plan.docs:
            if spent + summ.cost(plan.tokens[doc.id], avg_output) > budget:
                print(f"Stopped at the spending cap (${budget:.2f}). Run again to continue.")
                break
            try:
                summary = summarizer.summarize(doc, today)
            except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
                print("Your API key wasn't accepted. Check ANTHROPIC_API_KEY in .env.")
                failed += 1
                break
            except (summ.SummaryError, anthropic.APIError, ValueError) as e:
                print(f"  FAILED  {doc.title[:70]}: {e}")
                failed += 1
                continue
            summ.apply_summary(doc, summary)
            session.commit()
            spent += summary["_meta"]["cost_usd"]
            done += 1
            print(f"  {email_digest.RISK_ICONS[summary['risk_level']]} {summary['risk_level']:<15} "
                  f"${summary['_meta']['cost_usd']:.3f}  {doc.title[:70]}")
        print(f"\nDone: {done} summarized, {failed} failed. Spent ${spent:.2f}.")
        return failed == 0


def cmd_digest(engine, *, preview=False, test=False, settings=None, smtp_class=smtplib.SMTP, today=None) -> bool:
    """Email what's new since the last email. --test sends the 3 latest summaries without marking anything."""
    today = today or date.today()
    with repo.make_session(engine) as session:
        if test:
            query = (select(Document).where(Document.summary_json.is_not(None))
                     .order_by(Document.date_published.desc().nulls_last()).limit(3))
            docs = list(session.scalars(query))
        else:
            docs = repo.get_unemailed_new(session)
        if not docs:
            print("Nothing new to send." if not test else "No summaries yet. Run `python main.py summarize` first.")
            return True
        if preview:
            print(email_digest.build_text(docs, today))
            return True
        settings = settings or email_digest.EmailSettings.from_env()
        if settings is None:
            print(NO_EMAIL_HELP + "\n\nHere's what the email would say:\n")
            print(email_digest.build_text(docs, today))
            return False
        try:
            email_digest.send(docs, settings, today, smtp_class=smtp_class)
        except (smtplib.SMTPException, OSError) as e:
            print(f"The email couldn't be sent: {type(e).__name__}: {e}")
            return False
        if not test:
            repo.mark_emailed(session, docs)
        print(f"Sent {'a test email' if test else 'the update'} about {len(docs)} documents to {', '.join(settings.to)}.")
        return True


def cmd_weekly(engine) -> bool:
    """The one command a weekly job runs: check every source, summarize what's new, email it."""
    scraped = cmd_scrape(engine, "all")
    summarized = cmd_summarize(engine, only_new=True, yes=True)
    emailed = cmd_digest(engine)
    return scraped and summarized and emailed


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
    summarize = sub.add_parser("summarize", help="write AI summaries (shows the cost and asks first)")
    summarize.add_argument("--dry-run", action="store_true", help="only show what it would cost")
    summarize.add_argument("--limit", type=int, help="summarize at most this many documents")
    summarize.add_argument("--yes", action="store_true", help="don't ask before spending")
    summarize.add_argument("--include-large", action="store_true", help="include very long documents")
    digest = sub.add_parser("digest", help="email what's new since the last email")
    digest.add_argument("--preview", action="store_true", help="print the email instead of sending it")
    digest.add_argument("--test", action="store_true", help="send the 3 latest summaries as a test")
    sub.add_parser("weekly", help="scrape, summarize what's new, and email it")
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
    elif args.command == "summarize":
        ok = cmd_summarize(engine, dry_run=args.dry_run, limit=args.limit, yes=args.yes,
                           include_large=args.include_large)
        return 0 if ok else 1
    elif args.command == "digest":
        return 0 if cmd_digest(engine, preview=args.preview, test=args.test) else 1
    elif args.command == "weekly":
        return 0 if cmd_weekly(engine) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
