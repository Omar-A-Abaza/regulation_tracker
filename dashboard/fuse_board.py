"""Fuse board (home page): every deadline is a bomb with a lit fuse. The fuse is the time left."""
from datetime import date

import streamlit as st

from dashboard import fuse
from dashboard.common import cached_documents, cached_health, cached_milestones, reload_button, show_html
from database.models import utcnow

docs = cached_documents()
health = cached_health()
now, today = utcnow(), date.today()

items = fuse.build_items(cached_milestones(), docs, today)

with st.sidebar:
    st.caption("The fuse board re-reads the database every 5 minutes.")
    reload_button()

st.title("Fuse board")
st.caption("Every AI-law deadline is a bomb, and its fuse is the time left. Hover, tap or tab to a fuse "
           "for its summary. Red: within 30 days. Orange: within 90 days.")
if not health:
    st.warning("The scrapers haven't run yet, so the board only shows the timeline and the starting data. "
               "Run `python main.py scrape` to check the websites.")

show_html(fuse.render(items, head=fuse.header(docs, health, now, today), theme=st.context.theme.type),
          fallback_height=fuse.frame_height(items))
