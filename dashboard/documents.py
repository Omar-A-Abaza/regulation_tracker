"""All documents: the next 5 deadlines as fuses, then every document in the database."""
from datetime import date

import pandas as pd
import streamlit as st

from dashboard import data, fuse
from dashboard.common import (cached_documents, cached_health, cached_milestones, md, reload_button,
                              safe_url, show_html)
from database.models import utcnow

STATUS_ICONS = {"success": "✅ Working", "partial": "⚠️ Partly working", "failed": "❌ Failed", "running": "⏳ Running"}
RISK_BADGES = {"Action Required": ":red-badge[🔴 Action Required]", "Watch": ":orange-badge[🟡 Watch]",
               "Informational": ":gray-badge[⚪ Informational]"}
RISK_ORDER = {"Action Required": 0, "Watch": 1, "Informational": 2}
SORTS = {
    "Newest published": lambda docs: data.sort_newest_first(docs),
    "Newest found": lambda docs: sorted(docs, key=lambda d: d.date_detected, reverse=True),
    "Most urgent": lambda docs: sorted(data.sort_newest_first(docs), key=lambda d: RISK_ORDER.get(d.risk_level, 3)),
    "Title A–Z": lambda docs: sorted(docs, key=lambda d: d.title.lower()),
}


def render_summary(summary: dict) -> None:
    with st.expander("Full AI summary"):
        if summary.get("tldr"):
            st.markdown("\n".join(f"- {md(b)}" for b in summary["tldr"]))
        if summary.get("who_is_affected"):
            st.markdown(f"**Who's affected:** {md(summary['who_is_affected'])}")
        if summary.get("key_deadline"):
            when = f"{summary['key_deadline_date']}: " if summary.get("key_deadline_date") else ""
            st.markdown(f"**Key deadline:** {md(when + summary['key_deadline'])}")
        if summary.get("actions_required"):
            st.markdown("**What to do:**\n" + "\n".join(f"- {md(a)}" for a in summary["actions_required"]))
        meta = summary.get("_meta", {})
        basis = "the full text" if meta.get("based_on") == "full_text" else "the title and description only"
        st.caption(f"Written by AI ({meta.get('model', 'Claude')}) from {basis}, "
                   f"on {meta.get('summarized_at', '')[:10]}. Check the source before acting.")


def render_doc(doc: data.DocRow) -> None:
    with st.container(border=True):
        top = [f":blue-badge[{md(data.source_label(doc))}]"]
        if doc.risk_level in RISK_BADGES:
            top.append(RISK_BADGES[doc.risk_level])
        if doc.is_new:
            top.append(":green-badge[Really new]")
        top.append(data.FRAMEWORKS.get(doc.framework, doc.framework))
        top.append("· Published " + (data.nice_date(doc.date_published) if doc.date_published else "date unknown"))
        top.append(f"· Found {data.nice_date(doc.date_detected.date())}")
        st.markdown(" ".join(top))
        st.markdown(f"**[{md(doc.title)}]({safe_url(doc.url)})**")
        bullets = (doc.summary or {}).get("tldr")
        if bullets:
            st.markdown(md(bullets[0]))
        elif doc.note:
            st.markdown(md(doc.note))
        tags = [f":gray-badge[{data.CATEGORIES.get(c, c)}]" for c in doc.categories if c != "other"]
        if not doc.summary:
            tags.append(":gray[*No AI summary yet.*]")
        if tags:
            st.markdown(" ".join(tags))
        if doc.summary:
            render_summary(doc.summary)


# ---------------------------------------------------------------- data

docs = cached_documents()
health = cached_health()
now, today = utcnow(), date.today()

# ---------------------------------------------------------------- sidebar

# Filters can be set from the link, e.g. ?category=gpai&urgency=Action Required&range=All time,
# so a filtered view can be shared.
link = st.query_params
linked_categories = [c for c in link.get_all("category") if c in data.CATEGORIES]
linked_urgency = [r for r in link.get_all("urgency") if r in data.RISK_LEVELS]
range_options = list(data.DATE_RANGES)
linked_range = range_options.index(link["range"]) if link.get("range") in range_options \
    else range_options.index("All time")

with st.sidebar:
    st.header("Filters")
    st.caption("Leave a box empty to see everything.")
    frameworks = st.multiselect("Framework", list(data.FRAMEWORKS), format_func=data.FRAMEWORKS.get,
                                placeholder="All frameworks")
    categories = st.multiselect("Category", list(data.CATEGORIES), format_func=data.CATEGORIES.get,
                                placeholder="All categories", default=linked_categories)
    sources = st.multiselect("Website", list(data.SOURCES), format_func=data.SOURCES.get,
                             placeholder="All websites")
    risk_levels = st.multiselect("Urgency", list(data.RISK_LEVELS), format_func=data.RISK_LEVELS.get,
                                 placeholder="Any urgency", default=linked_urgency)
    range_label = st.selectbox("Date range", range_options, index=linked_range)
    st.divider()
    reload_button()

# ---------------------------------------------------------------- next deadlines

st.title("All documents")
upcoming = [i for i in fuse.build_items(cached_milestones(), docs, today) if i["urgency"] != "blown"][:5]
st.caption("Next deadlines. Hover or tap a fuse for details; the Fuse board has them all.")
show_html(fuse.render(upcoming, mode="small", theme=st.context.theme.type),
          fallback_height=fuse.frame_height(upcoming, "small"))

# ---------------------------------------------------------------- the list

search_col, sort_col = st.columns([3, 1])
query = search_col.text_input("Search", placeholder="e.g. copyright, FTC, Omnibus")
sort_label = sort_col.selectbox("Sort by", list(SORTS))

shown = SORTS[sort_label](data.filter_documents(
    docs, today=today, frameworks=frameworks, categories=categories, sources=sources,
    days=data.DATE_RANGES[range_label], query=query, risk_levels=risk_levels))
st.subheader(f"{len(shown)} of {len(docs)} documents · {range_label.lower()}")
st.caption("“Really new” = found after a source's first check, so not old documents found the first time.")
if not shown:
    st.info("No documents match these filters. Try a longer date range or clear some filters.")
for doc in shown:
    render_doc(doc)

# ---------------------------------------------------------------- website status

st.divider()
st.subheader("Website status")
if health:
    st.dataframe(pd.DataFrame([{
        "Source": h.label,
        "Status": STATUS_ICONS.get(h.status, h.status),
        "Last checked": data.time_ago(h.last_checked, now),
        "New on last check": h.new_count,
        "Problem": h.error or "",
    } for h in health]), hide_index=True)
else:
    st.caption("No checks yet. Run `python main.py scrape` to check the websites.")
