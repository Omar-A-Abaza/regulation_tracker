"""EU AI Office scraper.

The AI Office's web pages block programs (error 403), but the site's news feed is
open and allowed by its robots.txt. The feed covers all EU digital topics and only
holds the 10 newest items, so we keep the AI-related ones and run often enough
not to miss any.
"""
import re

from bs4 import BeautifulSoup

from processors.classifier import classify
from scrapers.base import BaseScraper, DocumentCandidate, FeedItem, clean_text, first_sentence, read_rss_items

FEED_URL = "https://digital-strategy.ec.europa.eu/en/rss.xml"

AI_PATTERN = re.compile(r"(?i:\bAI Act\b|artificial intelligence|general[- ]purpose AI|\bGPAI\b|copyright)|\bAI\b")
# Events and funding calls aren't rules or guidance.
SKIP_SECTIONS = ("/events/", "/funding/")


class EuAiOfficeScraper(BaseScraper):
    name = "eu_ai_office"
    label = "EU AI Office"

    def fetch(self) -> list[DocumentCandidate]:
        return select_items(read_rss_items(self.request("GET", FEED_URL).content))


def summary_of(item: FeedItem) -> str:
    """The feed's short summary line, if it has one; otherwise the plain text."""
    soup = BeautifulSoup(item.description_html, "lxml")
    teaser = soup.select_one(".ecl-page-header-standardised__description, .cnt-teaser p")
    return clean_text(str(teaser)) if teaser else clean_text(item.description_html)


def select_items(items: list[FeedItem]) -> list[DocumentCandidate]:
    keep = []
    for item in items:
        if any(section in item.link for section in SKIP_SECTIONS):
            continue
        summary = summary_of(item)
        if not AI_PATTERN.search(f"{item.title} {summary}"):
            continue
        keep.append(
            DocumentCandidate(
                source="eu_ai_office",
                title=item.title,
                url=item.link,
                framework="eu_ai_act",
                date_published=item.published,
                note=first_sentence(summary) or None,
                categories=classify(f"{item.title} {summary}"),
            )
        )
    return keep
