"""Shared tools for every scraper: a polite web client and the "found document" shape."""
import time
from dataclasses import dataclass, field
from datetime import date

import httpx

USER_AGENT = "ai-regulation-tracker/0.1 (compliance research project)"


@dataclass
class DocumentCandidate:
    """A document a scraper found. Not saved yet."""

    source: str
    title: str
    url: str
    framework: str
    date_published: date | None = None
    external_id: str | None = None
    note: str | None = None
    categories: list[str] = field(default_factory=list)


class BaseScraper:
    """Every scraper builds on this. Subclasses set `name` and write `fetch()`."""

    name = ""
    label = ""  # human-friendly name, e.g. "EUR-Lex"
    min_interval = 1.0  # seconds between requests (be polite)
    max_attempts = 3
    backoff = 2.0

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=90, follow_redirects=True
        )
        self._last_request = 0.0

    def fetch(self) -> list[DocumentCandidate]:
        raise NotImplementedError

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send a request. Waits between requests and retries if the site hiccups."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self._wait_turn()
            try:
                response = self.client.request(method, url, **kwargs)
                # 429 (too many requests) and 5xx (server trouble) are worth retrying.
                if response.status_code != 429 and response.status_code < 500:
                    response.raise_for_status()
                    return response
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code} from {url}", request=response.request, response=response
                )
            except httpx.TransportError as e:
                last_error = e
            if attempt < self.max_attempts:
                time.sleep(self.backoff * attempt)
        raise last_error

    def close(self) -> None:
        self.client.close()

    def _wait_turn(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
