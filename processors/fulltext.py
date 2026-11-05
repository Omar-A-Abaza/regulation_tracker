"""Get a document's full text, so the summarizer can read the whole thing.

Some documents can't be fetched (EU AI Office pages block programs, California is
behind a bot check, NIST's frameworks are PDFs). For those, the summarizer works
from the title and note instead.
"""
import warnings

from bs4 import XMLParsedAsHTMLWarning

from database.models import Document
from scrapers.base import BaseScraper
from scrapers.page_watcher import extract_text, fingerprint

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

EU_DATA_SERVICE = "https://publications.europa.eu/resource/celex/{celex}"
FEDERAL_REGISTER_DOC = "https://www.federalregister.gov/api/v1/documents/{number}.json"
# Which part of each page holds the text (skips menus and footers).
PAGE_SELECTORS = {
    "https://www.nist.gov/": ".nist-page__content",
    "https://leg.colorado.gov/": "main",
}


class FullTextFetcher(BaseScraper):
    name = "fulltext"
    label = "Full text"

    def text_for(self, doc: Document) -> str | None:
        """The document's full text, or None if this kind of document can't be fetched."""
        if (doc.external_id or "").startswith("page:"):
            return None  # a "Page updated" entry: its note already says what changed
        if doc.source == "eurlex" and doc.external_id:
            response = self.request("GET", EU_DATA_SERVICE.format(celex=doc.external_id),
                                    headers={"Accept": "application/xhtml+xml, text/html", "Accept-Language": "eng"})
            return extract_text(response.text, "body")
        if doc.source == "federal_register" and doc.external_id:
            meta = self.request("GET", FEDERAL_REGISTER_DOC.format(number=doc.external_id),
                                params={"fields[]": ["raw_text_url"]}).json()
            return " ".join(self.request("GET", meta["raw_text_url"]).text.split())
        for prefix, selector in PAGE_SELECTORS.items():
            if doc.url.startswith(prefix):
                response = self.request("GET", doc.url, headers={"Accept": "text/html,application/xhtml+xml"})
                return extract_text(response.text, selector)
        return None


def save_text(doc: Document, text: str) -> None:
    doc.raw_text = text
    doc.content_hash = fingerprint(text)
