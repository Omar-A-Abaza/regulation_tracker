import json
from datetime import date
from pathlib import Path

from scrapers.eurlex import is_relevant, parse_results, tidy_title

FIXTURE = Path(__file__).parent / "fixtures" / "eurlex_sparql.json"


def load_docs():
    return parse_results(json.loads(FIXTURE.read_text()))


def test_keeps_legal_acts_and_skips_parliament_opinions():
    docs = load_docs()
    ids = {d.external_id for d in docs}
    assert len(docs) == 8
    assert not any("IP" in i for i in ids)
    assert {"32026R1755", "32026R1744", "52026DC0234", "32025R0454"} <= ids


def test_one_document_per_celex():
    ids = [d.external_id for d in load_docs()]
    assert len(ids) == len(set(ids))


def test_corrections_get_readable_titles():
    titles = {d.external_id: d.title for d in load_docs()}
    assert titles["32024R1689R(04)"] == "Correction to the EU AI Act (No. 4)"


def test_enforcement_regulation_is_parsed_and_tagged():
    doc = next(d for d in load_docs() if d.external_id == "32026R1755")
    assert doc.date_published == date(2026, 7, 20)
    assert doc.framework == "eu_ai_act"
    assert "penalties" in doc.categories
    assert doc.url.endswith("CELEX:32026R1755")


def test_is_relevant():
    assert is_relevant("32026R1744")
    assert is_relevant("52026DC0234")
    assert not is_relevant("52026IP0066")


def test_tidy_title_fixes_all_caps():
    title = tidy_title("REPORT FROM THE COMMISSION ON PROHIBITED AI PRACTICES IN ANNEX III OF REGULATION (EU) 2024/1689")
    assert title == "Report from the Commission on prohibited AI practices in Annex III of Regulation (EU) 2024/1689"


def test_tidy_title_drops_eea_tail():
    assert tidy_title("Regulation X (Text with EEA relevance)") == "Regulation X"
