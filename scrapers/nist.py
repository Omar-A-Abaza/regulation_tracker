"""NIST scraper.

Reads NIST's topic news feeds. NIST renamed its "artificial intelligence" topic to
"super intelligence" in 2026, so we read both (plus IT, where agentic-AI news lands)
and keep only news items with an AI word in the title.
"""
import re

from processors.classifier import classify
from scrapers.base import BaseScraper, DocumentCandidate, FeedItem, clean_text, first_sentence, read_rss_items

FEEDS = [
    "https://www.nist.gov/news-events/super%20intelligence/rss.xml",
    "https://www.nist.gov/news-events/artificial%20intelligence/rss.xml",
    "https://www.nist.gov/news-events/information%20technology/rss.xml",
]

AI_PATTERN = re.compile(r"(?i:artificial intelligence|super ?intelligence|machine learning|agentic|\bAI RMF\b)|\bAI\b|\bC?AISI\b")
# Job posts and grant announcements aren't guidance.
SKIP_TITLES = re.compile(r"(?i)^apply on|usajobs|\bposition\b|\ballocates\b|\bawards?\b")


class NistScraper(BaseScraper):
    name = "nist"
    label = "NIST"

    def fetch(self) -> list[DocumentCandidate]:
        items, errors = [], []
        for url in FEEDS:
            try:
                items.extend(read_rss_items(self.request("GET", url).content))
            except Exception as e:
                errors.append(f"{url}: {e}")
        # One feed going missing is fine; all of them failing is a real problem.
        if errors and not items:
            raise RuntimeError("All NIST feeds failed: " + "; ".join(errors))
        return select_items(items)


def is_relevant(item: FeedItem) -> bool:
    """News only (no events, staff spotlights or job posts), with an AI word in the title."""
    return (
        "/news-events/news/" in item.link
        and not item.title.lower().startswith("spotlight")
        and not SKIP_TITLES.search(item.title)
        and bool(AI_PATTERN.search(item.title))
    )


def select_items(items: list[FeedItem]) -> list[DocumentCandidate]:
    seen: dict[str, DocumentCandidate] = {}
    for item in items:
        if item.link in seen or not is_relevant(item):
            continue
        description = clean_text(item.description_html)
        # Some descriptions start by repeating the title.
        if description.startswith(item.title):
            description = description[len(item.title):].lstrip(" :.-–")
        seen[item.link] = DocumentCandidate(
            source="nist",
            title=item.title,
            url=item.link,
            framework="nist_ai_rmf",
            date_published=item.published,
            note=first_sentence(description) or None,
            categories=classify(f"{item.title} {description}"),
        )
    return list(seen.values())
