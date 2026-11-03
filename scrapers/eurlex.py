"""EUR-Lex scraper.

EUR-Lex web pages block bots, so we ask the EU's official data service (SPARQL)
instead: "Which documents are linked to the AI Act?"
"""
import re
from datetime import date, datetime

from processors.classifier import classify
from scrapers.base import BaseScraper, DocumentCandidate

SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"
AI_ACT_CELEX = "32024R1689"

# How a document can be linked to the AI Act, and the plain-English note we show for it.
RELATIONS = {
    "resource_legal_amends_resource_legal": "Changes the text of the EU AI Act.",
    "resource_legal_corrects_resource_legal": "Fixes errors in the published text of the EU AI Act.",
    "resource_legal_based_on_resource_legal": "Made under the EU AI Act.",
    "resource_legal_implements_resource_legal": "Detailed rules for applying the EU AI Act.",
}

QUERY = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?rel ?celex ?date ?title WHERE {{
  ?act cdm:resource_legal_id_celex "{AI_ACT_CELEX}"^^<http://www.w3.org/2001/XMLSchema#string> .
  ?work ?rel ?act .
  FILTER(?rel IN ({", ".join("cdm:" + r for r in RELATIONS)}))
  ?work cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?work cdm:work_date_document ?date }}
  OPTIONAL {{
    ?expr cdm:expression_belongs_to_work ?work ;
          cdm:expression_title ?title ;
          cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  }}
}} ORDER BY DESC(?date)
"""

# Consolidated versions: the full AI Act text with all changes merged in.
# CELEX looks like 02024R1689-20260727 (the date that version applies from).
VERSIONS_QUERY = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex WHERE {{
  ?work cdm:resource_legal_id_celex ?celex .
  FILTER(STRSTARTS(STR(?celex), "0{AI_ACT_CELEX[1:]}-"))
}}
"""

# Words to keep capitalised when we tidy an ALL-CAPS title.
_KEEP_CASE = ["European Parliament", "European Union", "Council", "Commission", "Regulation", "Article", "(EU)", "AI"]


class EurLexScraper(BaseScraper):
    name = "eurlex"
    label = "EUR-Lex"

    def fetch_raw(self) -> dict:
        response = self.request(
            "POST", SPARQL_URL, data={"query": QUERY}, headers={"Accept": "application/sparql-results+json"}
        )
        return response.json()

    def fetch(self) -> list[DocumentCandidate]:
        return parse_results(self.fetch_raw())


class EurLexVersionsScraper(BaseScraper):
    """Catches a new full-text version of the AI Act, i.e. the law's text changed."""

    name = "eurlex_versions"
    label = "EUR-Lex (AI Act text versions)"

    def fetch_raw(self) -> dict:
        response = self.request(
            "POST", SPARQL_URL, data={"query": VERSIONS_QUERY}, headers={"Accept": "application/sparql-results+json"}
        )
        return response.json()

    def fetch(self) -> list[DocumentCandidate]:
        return parse_versions(self.fetch_raw())


def parse_versions(payload: dict) -> list[DocumentCandidate]:
    docs = []
    for row in payload["results"]["bindings"]:
        celex = row["celex"]["value"]
        match = re.match(r"^0\d{4}R\d{4}-(\d{8})$", celex)
        if not match:
            continue
        applies_from = datetime.strptime(match.group(1), "%Y%m%d").date()
        docs.append(
            DocumentCandidate(
                source="eurlex",
                title=f"Full text of the EU AI Act, version of {applies_from.day} {applies_from:%b} {applies_from.year}",
                url=f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
                framework="eu_ai_act",
                date_published=applies_from,
                external_id=celex,
                note="The full AI Act text with all changes up to this date merged in. A new version means the law's text changed.",
                categories=["other"],
            )
        )
    return sorted(docs, key=lambda d: d.date_published, reverse=True)


def is_relevant(celex: str) -> bool:
    """Keep legal acts and corrections (CELEX starts with 3) and Commission
    documents (5yyyyDC/PC/SC). Skip Parliament opinions and other mentions."""
    return celex.startswith("3") or re.match(r"^5\d{4}(DC|PC|SC)", celex) is not None


def parse_results(payload: dict) -> list[DocumentCandidate]:
    """Turn the data service's answer into documents. One per CELEX number."""
    seen: dict[str, DocumentCandidate] = {}
    for row in payload["results"]["bindings"]:
        celex = row["celex"]["value"]
        if not is_relevant(celex):
            continue
        title = row.get("title", {}).get("value")
        if celex in seen:
            # Same document again (another link type). Keep the first, but fill in a missing title.
            if title and seen[celex].title.startswith("EU document "):
                seen[celex].title = tidy_title(title)
            continue

        relation = row["rel"]["value"].split("#")[-1]
        title = make_title(celex, title)
        note = RELATIONS.get(relation)
        if celex[5:7] == "DC":
            note = "Commission report linked to the EU AI Act."
        raw_date = row.get("date", {}).get("value")
        seen[celex] = DocumentCandidate(
            source="eurlex",
            title=title,
            url=f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
            framework="eu_ai_act",
            date_published=date.fromisoformat(raw_date[:10]) if raw_date else None,
            external_id=celex,
            note=note,
            categories=classify(title),
        )
    return list(seen.values())


def make_title(celex: str, title: str | None) -> str:
    # Corrections have no title in the data service. CELEX looks like 32024R1689R(04).
    correction = re.match(rf"^{AI_ACT_CELEX}R\((\d+)\)$", celex)
    if correction:
        return f"Correction to the EU AI Act (No. {int(correction.group(1))})"
    if not title:
        return f"EU document {celex}"
    return tidy_title(title)


def tidy_title(title: str) -> str:
    """Drop the "(Text with EEA relevance)" tail and fix ALL-CAPS titles."""
    title = re.sub(r"\s*\(Text with EEA relevance\)\s*$", "", title.strip(), flags=re.IGNORECASE)
    if title.isupper():
        title = title.capitalize()
        for word in _KEEP_CASE:
            title = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", word, title, flags=re.IGNORECASE)
        title = re.sub(r"\bannex ([ivx]+)\b", lambda m: f"Annex {m.group(1).upper()}", title, flags=re.IGNORECASE)
    return title
