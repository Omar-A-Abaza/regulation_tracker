"""The fuse board's data: fuse length, urgency, exploded and moved deadlines, document deadlines."""
import json
import re
from datetime import date, datetime, timedelta

import pytest

from dashboard import data, fuse
from dashboard.data import DocRow, SourceHealth

TODAY = date(2026, 11, 21)
NOW = datetime(2026, 11, 21, 12, 0)
MILESTONES = data.load_milestones()


def doc(n, *, deadline="", framework="eu_ai_act", categories=("gpai",), risk="Watch", summary=True, title=None,
        status="new", external_id=None):
    s = {"tldr": [f"Bullet {n}."], "who_is_affected": "GPAI providers", "key_deadline_date": deadline,
         "key_deadline": "Something is due." if deadline else "", "actions_required": ["Do a thing."],
         "risk_level": risk, "categories": list(categories)} if summary else None
    return DocRow(id=n, source="eurlex", title=title or f"Doc {n}", url=f"https://x/{n}",
                  date_published=TODAY - timedelta(days=n), date_detected=NOW, framework=framework, note="A note.",
                  status=status, categories=list(categories), summary=s, risk_level=risk if summary else None,
                  watched=bool(external_id and external_id.startswith("page:")))


def by_id(items):
    return {i["id"]: i for i in items}


# --- fuse length and urgency ------------------------------------------------

def test_fuse_length_is_a_capped_log_scale():
    assert fuse.fuse_length(-5) == fuse.fuse_length(0) == 0
    assert fuse.fuse_length(fuse.MAX_DAYS) == 1 == fuse.fuse_length(fuse.MAX_DAYS * 3)
    two_weeks, two_years = fuse.fuse_length(14), fuse.fuse_length(730)
    # Both readable: a 2-week fuse isn't a dot, and a 2-year fuse doesn't fill the track.
    assert 0.3 < two_weeks < 0.5 and 0.85 < two_years < 1
    lengths = [fuse.fuse_length(d) for d in (1, 7, 30, 90, 365, 1000)]
    assert lengths == sorted(lengths)


@pytest.mark.parametrize("days, bucket", [(-1, "blown"), (0, "red"), (30, "red"), (31, "orange"), (90, "orange"),
                                          (91, "later"), (900, "later")])
def test_urgency_buckets(days, bucket):
    assert fuse.urgency(days) == bucket


def test_months_between():
    assert fuse.months_between(date(2026, 8, 2), date(2027, 12, 2)) == 16
    assert fuse.months_between(date(2027, 8, 2), date(2028, 8, 2)) == 12
    assert fuse.months_between(date(2026, 1, 31), date(2026, 2, 28)) == 0


# --- milestones ---------------------------------------------------------------

def test_passed_deadlines_are_exploded():
    item = by_id(fuse.build_items(MILESTONES, [], TODAY))["m-aiact_gpai"]
    assert item["urgency"] == "blown" and item["fuse"] == 0
    assert item["blown_label"] == "In force since Aug 2, 2025"
    assert item["when"].endswith("days ago")


def test_the_two_omnibus_deadlines_get_a_spliced_fuse():
    items = fuse.build_items(MILESTONES, [], TODAY)
    moved = {i["id"]: i["moved"] for i in items if i["moved"]}
    assert set(moved) == {"m-aiact_high_risk_annex_iii", "m-aiact_high_risk_annex_i"}
    annex_iii = moved["m-aiact_high_risk_annex_iii"]
    assert annex_iii["label"] == "Extended +16 months by Reg. 2026/1744"
    assert annex_iii["from_label"] == "Aug 2, 2026"
    assert annex_iii["knot"] == 0  # the old date has passed: the knot sits at the bomb
    annex_i = moved["m-aiact_high_risk_annex_i"]
    assert annex_i["label"] == "Extended +12 months by Reg. 2026/1744"
    assert 0 < annex_i["knot"] < by_id(items)["m-aiact_high_risk_annex_i"]["fuse"]


def test_a_changed_by_without_an_old_date_is_not_moved():
    assert by_id(fuse.build_items(MILESTONES, [], TODAY))["m-omnibus_new_bans"]["moved"] is None


def test_milestone_card_fields_and_region():
    items = by_id(fuse.build_items(MILESTONES, [], TODAY))
    bans = items["m-omnibus_new_bans"]
    assert bans["urgency"] == "red" and bans["days"] == 11 and bans["when"] == "11 days left"
    assert bans["articles"] == ["Art. 5(1a)", "Art. 5(1b)", "Art. 50(2)"]
    assert bans["url"].startswith("https://eur-lex.europa.eu/")
    assert "fake nude images" in bans["summary"][0]
    assert items["m-co_sb26_189"]["region"] == "state" and items["m-co_sb26_189"]["urgency"] == "orange"
    assert bans["region"] == "EU"


def test_milestones_list_linked_documents_by_framework_and_category():
    docs = [doc(1, categories=["high_risk"]), doc(2, categories=["gpai"]), doc(3, framework="us_federal",
                                                                             categories=["high_risk"])]
    item = by_id(fuse.build_items(MILESTONES, docs, TODAY))["m-aiact_high_risk_annex_iii"]
    assert [d["title"] for d in item["linked"]] == ["Doc 1"]
    assert item["linked"][0]["bullets"] == ["Bullet 1."]
    # A milestone with no categories takes any document about the same law.
    assert len(by_id(fuse.build_items(MILESTONES, docs, TODAY))["m-aiact_in_force"]["linked"]) == 2


def test_linked_documents_put_summarized_ones_first_and_are_capped():
    docs = [doc(n, summary=n % 2 == 0) for n in range(1, 9)]
    linked = fuse.linked_documents({"framework": "eu_ai_act", "categories": ["gpai"]}, docs)
    assert len(linked) == fuse.LINKED_DOCS
    assert all(d["bullets"] for d in linked)


# --- documents with a deadline -----------------------------------------------

def test_documents_with_a_future_deadline_become_fuses():
    docs = [doc(1, deadline="2027-03-01", risk="Action Required"), doc(2, deadline="2026-01-01"),
            doc(3, deadline="not a date"), doc(4), doc(5, summary=False)]
    items = [i for i in fuse.build_items(MILESTONES, docs, TODAY) if i["kind"] == "document"]
    assert [i["id"] for i in items] == ["d-1"]
    item = items[0]
    assert item["date"] == "2027-03-01" and item["urgency"] == "later"
    assert item["ai_urgency"] == "Action Required"
    assert item["summary"] == ["Bullet 1."] and item["who"] == "GPAI providers"
    assert item["actions"] == ["Do a thing."] and item["deadline_note"] == "Something is due."


def test_a_deadline_today_still_counts():
    items = fuse.build_items([], [doc(1, deadline=TODAY.isoformat())], TODAY)
    assert items[0]["urgency"] == "red" and items[0]["when"] == "Today"


def test_items_are_sorted_soonest_first():
    items = fuse.build_items(MILESTONES, [doc(1, deadline="2026-12-15")], TODAY)
    dates = [i["date"] for i in items]
    assert dates == sorted(dates)
    upcoming = [i["id"] for i in items if i["urgency"] != "blown"]
    assert upcoming[:2] == ["m-omnibus_new_bans", "d-1"]


# --- header strip --------------------------------------------------------------

def health(key, status, error=None):
    return SourceHealth(key=key, label=data.RUN_SOURCES[key], status=status, last_checked=NOW - timedelta(hours=2),
                        new_count=0, error=error)


def test_header_counts_and_failing_sources():
    docs = [doc(1, risk="Action Required"), doc(2, status="backfill"), doc(3)]
    head = fuse.header(docs, [health("nist", "success"), health("eurlex", "failed", "down")], NOW, TODAY)
    assert head["updated"] == "Nov 21, 2026" and head["updated_ago"] == "2 hours ago"
    assert head["new_this_week"] == 2  # backfill doesn't count
    assert head["needs_action"] == 1
    assert head["failing"] == ["EUR-Lex"] and head["sources"] == 2


def test_header_before_any_scrape():
    head = fuse.header([], [], NOW, TODAY)
    assert head["updated"] == "" and head["sources"] == 0 and head["failing"] == []


# --- rendering ---------------------------------------------------------------

def payload(html):
    match = re.search(r"var DATA = (.*?);\n", html)
    return json.loads(match.group(1))


def test_render_embeds_the_items_safely():
    items = fuse.build_items(MILESTONES, [doc(1, deadline="2027-01-05", title="Evil </script><b>x</b>")], TODAY)
    html = fuse.render(items, head=fuse.header([], [], NOW, TODAY), theme="dark")
    assert "</script><b>" not in html
    assert 'data-theme="dark"' in html
    data_out = payload(html)
    assert data_out["mode"] == "full" and len(data_out["items"]) == len(items)
    assert any(i["title"] == "Evil </script><b>x</b>" for i in data_out["items"])
    assert [t["label"] for t in data_out["ticks"]] == list(fuse.TICKS)


def test_unknown_theme_follows_the_computer():
    assert 'data-theme="auto"' in fuse.render([], theme=None)


def test_frame_height_grows_with_the_items():
    items = fuse.build_items(MILESTONES, [doc(n, deadline="2027-06-01") for n in range(1, 30)], TODAY)
    assert fuse.frame_height(items) > fuse.frame_height(items[:8]) >= fuse.MIN_FULL_PX
    assert fuse.frame_height(items[:5], "small") < fuse.frame_height(items[:5])


def test_source_label():
    assert data.source_label(doc(1)) == "EUR-Lex"
    assert data.source_label(doc(2, status="seed")) == "Starting data"
    assert data.source_label(doc(3, external_id="page:https://x")) == "Watched page"
