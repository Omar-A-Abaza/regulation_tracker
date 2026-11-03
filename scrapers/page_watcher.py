"""Page watcher: fetches watched pages and turns them into comparable text.

Comparing with the last fingerprint happens in main.py, since it needs the database.
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper

PAGES_FILE = Path(__file__).resolve().parent.parent / "data" / "watched_pages.yaml"
# Tags that sit inside a sentence. We unwrap them so a link doesn't split its sentence in two.
INLINE_TAGS = ["a", "abbr", "b", "code", "em", "i", "small", "span", "strong", "sub", "sup", "time", "u"]


@dataclass
class WatchedPage:
    name: str
    url: str
    selector: str
    source: str
    framework: str
    why: str = ""


def load_pages(path: Path = PAGES_FILE) -> list[WatchedPage]:
    return [WatchedPage(**row) for row in yaml.safe_load(path.read_text())["pages"]]


def extract_text(html: str, selector: str) -> str:
    """The page's main text, one line per block, with extra spaces removed."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    node = soup.select_one(selector)
    if node is None:
        raise ValueError(f"'{selector}' not found on the page (the layout may have changed)")
    for tag in node.find_all(INLINE_TAGS):
        tag.unwrap()
    node.smooth()  # join the text pieces left behind by unwrap()
    lines = (" ".join(line.split()) for line in node.get_text("\n").splitlines())
    text = "\n".join(line for line in lines if line)
    if not text:
        raise ValueError(f"'{selector}' is empty (the layout may have changed)")
    return text


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class PageWatcher(BaseScraper):
    name = "pages"
    label = "Watched pages"

    def page_text(self, page: WatchedPage) -> str:
        response = self.request("GET", page.url, headers={"Accept": "text/html,application/xhtml+xml"})
        return extract_text(response.text, page.selector)
