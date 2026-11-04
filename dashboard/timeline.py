"""Timeline page: when each rule starts, including the deadlines the EU moved."""
from datetime import date

import streamlit as st

from dashboard import data
from dashboard.charts import timeline_chart
from dashboard.common import cached_milestones, md, safe_url

STATE_BADGES = {"done": "green", "soon": "orange", "later": "gray"}


def render_milestone(m: dict, today: date) -> None:
    state = data.milestone_state(m, today)
    icon = data.MILESTONE_STATES[state].split(" ")[0]
    where = data.JURISDICTIONS.get(m["jurisdiction"], m["jurisdiction"])
    with st.container(border=True):
        st.markdown(f":{STATE_BADGES[state]}-badge[{icon} {data.days_label(m['date'], today)}] "
                    f"**{data.nice_date(m['date'])}** · {where}")
        st.markdown(f"**{md(m['title'])}**")
        st.markdown(md(m["summary"]))
        if m.get("original_date"):
            st.markdown(f":red-badge[Moved] Was ~~{data.nice_date(m['original_date'])}~~ "
                        f"· changed by {md(m['changed_by'])}")
        meta = [md(", ".join(m["articles"]))] if m.get("articles") else []
        meta.append(f"[Source ↗]({safe_url(m['source_url'])})")
        st.caption(" · ".join(meta))


# ---------------------------------------------------------------- data + filters

today = date.today()

with st.sidebar:
    st.header("Filters")
    st.caption("Leave a box empty to see everything.")
    jurisdictions = st.multiselect("Where", list(data.JURISDICTIONS), format_func=data.JURISDICTIONS.get,
                                   placeholder="All places")
    categories = st.multiselect("Category", [c for c in data.CATEGORIES if c != "other"],
                                format_func=data.CATEGORIES.get, placeholder="All categories")

milestones = data.filter_milestones(cached_milestones(), jurisdictions=jurisdictions, categories=categories)
upcoming = [m for m in milestones if data.milestone_state(m, today) != "done"]
in_force = [m for m in milestones if data.milestone_state(m, today) == "done"]
moved = data.moved_milestones(milestones)

# ---------------------------------------------------------------- page

st.title("Deadlines")
st.caption(f"When each rule starts. Worked out from today's date ({data.nice_date(today)}).")

cards = st.columns(3)
if upcoming:
    nxt = upcoming[0]
    cards[0].metric("Next deadline", f"{(nxt['date'] - today).days} days", help=nxt["summary"])
    cards[0].caption(f"**{data.nice_date(nxt['date'])}** · {md(nxt['title'])}")
else:
    cards[0].metric("Next deadline", "None")
cards[1].metric("Coming up", len(upcoming))
cards[2].metric("Already in force", len(in_force))

if not milestones:
    st.info("No deadlines match these filters.")
    st.stop()

st.altair_chart(
    timeline_chart(milestones, today, st.context.theme.type or "light"),
    width="stretch",
    alt="Timeline of AI law deadlines by place. The full list is below the chart.",
)
st.caption("Hover over a dot for details. A hollow gray dot and a dashed line show where a deadline used to be.")

if moved:
    st.subheader(f"Deadlines that moved ({len(moved)})")
    st.markdown("The EU's **Digital Omnibus on AI** (Regulation (EU) 2026/1744, in force July 27, 2026) "
                "pushed these back.")
    for m in moved:
        extra = (m["date"] - m["original_date"]).days
        with st.container(border=True):
            st.markdown(f"**{md(m['title'])}**")
            st.markdown(f"~~{data.nice_date(m['original_date'])}~~ → **{data.nice_date(m['date'])}** "
                        f"· {extra} more days · now {data.days_label(m['date'], today)}")

st.subheader(f"Coming up ({len(upcoming)})")
for m in upcoming:
    render_milestone(m, today)

st.subheader(f"Already in force ({len(in_force)})")
for m in reversed(in_force):  # most recent first
    render_milestone(m, today)
