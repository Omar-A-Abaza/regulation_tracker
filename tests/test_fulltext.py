"""Getting full text, tested with fake web responses (no real requests)."""
import httpx

from database.models import Document
from processors.fulltext import FullTextFetcher


def fetcher(routes: dict[str, httpx.Response]) -> FullTextFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        for prefix, response in routes.items():
            if str(request.url).startswith(prefix):
                return response
        return httpx.Response(404)
    f = FullTextFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)))
    f.min_interval = 0
    return f


def doc(**fields):
    return Document(**{"title": "T", "framework": "x", **fields})


def test_federal_register_uses_the_raw_text():
    f = fetcher({
        "https://www.federalregister.gov/api/v1/documents/2026-1.json":
            httpx.Response(200, json={"raw_text_url": "https://www.federalregister.gov/raw/2026-1.txt"}),
        "https://www.federalregister.gov/raw/2026-1.txt": httpx.Response(200, text="Executive   Order\n text"),
    })
    assert f.text_for(doc(source="federal_register", external_id="2026-1", url="u")) == "Executive Order text"


def test_eurlex_uses_the_eu_data_service():
    f = fetcher({"https://publications.europa.eu/resource/celex/32026R1744":
                 httpx.Response(200, text="<html><body><p>Article 1</p><p>Text</p></body></html>")})
    assert f.text_for(doc(source="eurlex", external_id="32026R1744", url="u")) == "Article 1\nText"


def test_nist_page_uses_the_main_content_only():
    html = '<nav>Menu</nav><div class="nist-page__content"><p>The news.</p></div><footer>F</footer>'
    f = fetcher({"https://www.nist.gov/news-events/news/x": httpx.Response(200, text=html)})
    assert f.text_for(doc(source="nist", url="https://www.nist.gov/news-events/news/x")) == "The news."


def test_documents_that_cant_be_fetched_return_none():
    f = fetcher({})
    assert f.text_for(doc(source="eu_ai_office", url="https://digital-strategy.ec.europa.eu/en/x")) is None
    assert f.text_for(doc(source="nist", url="https://doi.org/10.6028/NIST.AI.100-1")) is None
    page_update = doc(source="nist", url="https://www.nist.gov/itl/x#update-abc", external_id="page:abc")
    assert f.text_for(page_update) is None
