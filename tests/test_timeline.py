from datetime import date
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from dashboard import data
from dashboard.charts import timeline_chart

PAGE = str(Path(__file__).resolve().parent.parent / "dashboard" / "timeline.py")
TODAY = date(2026, 11, 3)
MILESTONES = data.load_milestones()


def test_milestone_state():
    assert data.milestone_state({"date": date(2026, 8, 2)}, TODAY) == "done"
    assert data.milestone_state({"date": date(2026, 12, 2)}, TODAY) == "soon"
    assert data.milestone_state({"date": date(2027, 12, 2)}, TODAY) == "later"


def test_days_label():
    assert data.days_label(date(2026, 12, 2), TODAY) == "in 29 days"
    assert data.days_label(date(2026, 11, 2), TODAY) == "1 day ago"
    assert data.days_label(TODAY, TODAY) == "today"


def test_filter_milestones():
    eu = data.filter_milestones(MILESTONES, jurisdictions=["EU"])
    assert eu and all(m["jurisdiction"] == "EU" for m in eu)
    gpai = data.filter_milestones(MILESTONES, categories=["gpai"])
    assert {m["id"] for m in gpai} >= {"aiact_gpai", "aiact_legacy_gpai", "ca_sb53"}


def test_the_two_omnibus_deadlines_are_marked_as_moved():
    moved = {m["id"]: m for m in data.moved_milestones(MILESTONES)}
    assert set(moved) == {"aiact_high_risk_annex_iii", "aiact_high_risk_annex_i"}
    assert moved["aiact_high_risk_annex_iii"]["original_date"] == date(2026, 8, 2)
    assert moved["aiact_high_risk_annex_iii"]["date"] == date(2027, 12, 2)


def marks(spec):
    return [(layer["mark"]["type"], layer["mark"].get("yOffset", 0)) for layer in spec["layer"]]


def test_chart_gives_each_moved_deadline_its_own_lane():
    spec = timeline_chart(MILESTONES, TODAY).to_dict()
    assert marks(spec) == [
        ("rule", 0), ("text", 0),                     # Today line + label
        ("rule", 18), ("point", 18), ("point", 18),   # moved #1: dashed line, old date, new date
        ("rule", 36), ("point", 36), ("point", 36),   # moved #2, one lane lower
        ("point", 0),                                 # every other deadline, on its row
    ]


def test_chart_without_moved_deadlines():
    ca_only = data.filter_milestones(MILESTONES, jurisdictions=["US-CA"])
    assert marks(timeline_chart(ca_only, TODAY).to_dict()) == [("rule", 0), ("text", 0), ("point", 0)]


def test_chart_when_only_moved_deadlines_are_shown():
    moved_only = data.moved_milestones(MILESTONES)
    assert [m for m, _ in marks(timeline_chart(moved_only, TODAY).to_dict())][-1] == "point"


def run_page():
    st.cache_data.clear()
    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    return at


def test_timeline_page_loads():
    at = run_page()
    assert not at.exception
    assert at.title[0].value == "Deadlines"
    headers = [s.value for s in at.subheader]
    assert any(h.startswith("Deadlines that moved (2)") for h in headers)
    assert any(h.startswith("Coming up") for h in headers)
    assert any(h.startswith("Already in force") for h in headers)


def test_timeline_filter_with_no_matches():
    at = run_page()
    at.multiselect[0].select("US-CO").run()
    at.multiselect[1].select("prohibited").run()
    assert not at.exception
    assert any("No deadlines match" in i.value for i in at.info)
