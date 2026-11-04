"""Home page: what changed this week, recent updates, and website status."""
from datetime import date

import pandas as pd
import streamlit as st

from dashboard import data
from dashboard.common import cached_documents, cached_health, cached_milestones, md, safe_url
from database.models import utcnow

STATUS_ICONS = {"success": "✅ Working", "partial": "⚠️ Partly working", "failed": "❌ Failed", "running": "⏳ Running"}


def render_doc(doc: data.DocRow) -> None:
    with st.container(border=True):
        top = [f":blue-badge[{data.SOURCES.get(doc.source, doc.source)}]"]
        if doc.is_new:
            top.append(":green-badge[New]")
        published = data.nice_date(doc.date_published) if doc.date_published else "Date unknown"
        top.append(published)
        if doc.status == "seed":
            top.append("· starting data")
        st.markdown(" ".join(top))
        st.markdown(f"**{md(doc.title)}**")
        if doc.note:
            st.markdown(md(doc.note))
        tags = " ".join(f":gray-badge[{data.CATEGORIES.get(c, c)}]" for c in doc.categories)
        st.markdown(f"{tags} &nbsp; [Open source ↗]({safe_url(doc.url)})")
        if doc.summary:
            with st.expander("AI summary"):
                st.json(doc.summary)


# ---------------------------------------------------------------- data

docs = cached_documents()
health = cached_health()
now, today = utcnow(), date.today()

# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.header("Filters")
    st.caption("Leave a box empty to see everything.")
    frameworks = st.multiselect("Framework", list(data.FRAMEWORKS), format_func=data.FRAMEWORKS.get,
                                placeholder="All frameworks")
    categories = st.multiselect("Category", list(data.CATEGORIES), format_func=data.CATEGORIES.get,
                                placeholder="All categories")
    sources = st.multiselect("Website", list(data.SOURCES), format_func=data.SOURCES.get,
                             placeholder="All websites")
    range_label = st.selectbox("Date range", list(data.DATE_RANGES))
    query = st.text_input("Search", placeholder="e.g. copyright, FTC, Omnibus")
    st.divider()
    if st.button("Reload data", help="The page re-reads the database every 5 minutes. Click to do it now."):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------- what changed this week

st.title("What changed this week")
if health:
    last_check = max(h.last_checked for h in health)
    st.caption(f"Today is {data.nice_date(today)} · Websites last checked {data.time_ago(last_check, now)}")
else:
    st.caption(f"Today is {data.nice_date(today)}")

fresh = data.new_this_week(docs, now)
failing = [h for h in health if h.status in ("failed", "partial")]

if not health:
    st.warning("The scrapers haven't run yet, so this page only shows the starting data. "
               "Run `python main.py scrape` to check the websites.")
elif failing:
    names = ", ".join(h.label for h in failing)
    st.warning(f"{'Nothing new this week' if not fresh else f'{len(fresh)} new this week'}, "
               f"but some checks failed: **{names}**. We might be missing something. See *Website status* below.")
elif not fresh:
    st.success(f"Nothing new this week. We checked {len(health)} sources and all are working.")

cards = st.columns(3)
cards[0].metric("New this week", len(fresh), help="Found by the scrapers in the last 7 days. "
                "Doesn't count starting data or old documents found the first time a scraper ran.")
cards[1].metric("Published in the last 30 days", len(data.filter_documents(docs, today=today, days=30)))
upcoming = data.next_milestone(cached_milestones(), today)
if upcoming:
    days_left = (upcoming["date"] - today).days
    cards[2].metric("Next deadline", f"{days_left} days", help=upcoming.get("summary"))
    cards[2].caption(f"**{data.nice_date(upcoming['date'])}** · {md(upcoming['title'])}")

if fresh:
    st.subheader(f"New this week ({len(fresh)})")
    for doc in fresh:
        render_doc(doc)

# ---------------------------------------------------------------- recent updates

shown = data.filter_documents(docs, today=today, frameworks=frameworks, categories=categories, sources=sources,
                              days=data.DATE_RANGES[range_label], query=query)
st.subheader(f"Recent updates · {range_label.lower()} ({len(shown)})")
if not shown:
    st.info("No updates match these filters. Try a longer date range or clear some filters.")
for doc in shown:
    render_doc(doc)

# ---------------------------------------------------------------- website status

st.divider()
st.subheader("Website status")
if health:
    table = pd.DataFrame([{
        "Source": h.label,
        "Status": STATUS_ICONS.get(h.status, h.status),
        "Last checked": data.time_ago(h.last_checked, now),
        "New on last check": h.new_count,
        "Problem": h.error or "",
    } for h in health])
    st.dataframe(table, hide_index=True)
else:
    st.caption("No checks yet.")
