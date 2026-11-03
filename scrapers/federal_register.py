"""Federal Register scraper.

Uses the official Federal Register data service (no page scraping needed).
Searching for "artificial intelligence" also returns documents that only mention
AI once, so we filter:
  - White House documents: keep if the title is about AI, or AI comes up often in the text.
  - Agency documents (rules, notices): keep only if AI is in the title.
"""
import re
from collections.abc import Callable
from datetime import date

from processors.classifier import classify
from scrapers.base import BaseScraper, DocumentCandidate

API_URL = "https://www.federalregister.gov/api/v1/documents.json"
SINCE = date(2025, 1, 1)
FIELDS = [
    "title", "type", "subtype", "document_number", "publication_date", "signing_date",
    "executive_order_number", "html_url", "raw_text_url", "agencies", "abstract",
]

AI_PATTERN = re.compile(r"(?i:artificial intelligence|super ?intelligence|machine learning)|\bAI\b")
# On Day 3, AI-focused orders had 8+ mentions and 10+ per 1,000 words; orders that
# only mention AI had 0–6. These limits sit safely between the two groups.
MIN_MENTIONS = 8
MIN_PER_1000_WORDS = 5
# Routine agency paperwork that happens to have AI in the title.
SKIP_TITLES = re.compile(r"(?i)information collection|notice of (public )?meeting|sunshine act")

TYPE_LABELS = {"Rule": "Final rule", "Proposed Rule": "Proposed rule", "Notice": "Notice"}


class FederalRegisterScraper(BaseScraper):
    name = "federal_register"
    label = "Federal Register"
    min_interval = 0.5

    def fetch(self) -> list[DocumentCandidate]:
        presidential = self.search(["PRESDOCU"])
        agency = self.search(["RULE", "PRORULE", "NOTICE"])
        return select_documents(presidential, agency, self.full_text)

    def search(self, types: list[str]) -> list[dict]:
        """All matching documents since SINCE, following every results page."""
        params = {
            "conditions[term]": '"artificial intelligence"',
            "conditions[publication_date][gte]": SINCE.isoformat(),
            "conditions[type][]": types,
            "fields[]": FIELDS,
            "per_page": 1000,
            "order": "newest",
        }
        results, url = [], API_URL
        while url:
            page = self.request("GET", url, params=params).json()
            results.extend(page.get("results", []))
            url, params = page.get("next_page_url"), None  # next_page_url already has the params
        return results

    def full_text(self, doc: dict) -> str:
        return self.request("GET", doc["raw_text_url"]).text


def title_is_about_ai(title: str) -> bool:
    return bool(AI_PATTERN.search(title))


def text_is_about_ai(text: str) -> bool:
    mentions = len(AI_PATTERN.findall(text))
    words = max(len(text.split()), 1)
    return mentions >= MIN_MENTIONS and 1000 * mentions / words >= MIN_PER_1000_WORDS


def select_documents(
    presidential: list[dict], agency: list[dict], get_text: Callable[[dict], str]
) -> list[DocumentCandidate]:
    keep = []
    for doc in presidential:
        # Only download the full text when the title alone doesn't decide it.
        if title_is_about_ai(doc["title"]) or text_is_about_ai(get_text(doc)):
            keep.append(to_candidate(doc))
    for doc in agency:
        if title_is_about_ai(doc["title"]) and not SKIP_TITLES.search(doc["title"]):
            keep.append(to_candidate(doc))
    return keep


def to_candidate(doc: dict) -> DocumentCandidate:
    title = doc["title"].strip()
    if doc.get("executive_order_number"):
        title = f"EO {doc['executive_order_number']} — {title}"
    return DocumentCandidate(
        source="federal_register",
        title=title,
        url=doc["html_url"],
        framework="us_federal",
        date_published=date.fromisoformat(doc["publication_date"]),
        external_id=doc["document_number"],
        note=make_note(doc),
        categories=classify(f"{doc['title']} {doc.get('abstract') or ''}"),
    )


def make_note(doc: dict) -> str:
    agencies = [a["name"] for a in doc.get("agencies") or [] if a.get("name")]
    if doc["type"] == "Presidential Document":
        kind = doc.get("subtype") or "Presidential document"
        signed = doc.get("signing_date")
        if signed:
            d = date.fromisoformat(signed)
            return f"{kind}, signed {d:%b} {d.day}, {d.year}."
        return f"{kind} from the President."
    kind = TYPE_LABELS.get(doc["type"], doc["type"])
    return f"{kind} from {' / '.join(agencies[:2]) or 'a federal agency'}."
