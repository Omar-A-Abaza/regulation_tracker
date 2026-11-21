"""Helpers shared by the dashboard pages: cached data loading and safe Markdown."""
import re

import streamlit as st
import streamlit.components.v1 as components

from dashboard import data
from database import repository as repo


@st.cache_resource
def get_engine():
    engine = repo.get_engine()
    repo.init_db(engine)
    return engine


@st.cache_data(ttl=300)
def cached_documents() -> list[data.DocRow]:
    return data.load_documents(get_engine())


@st.cache_data(ttl=300)
def cached_health() -> list[data.SourceHealth]:
    return data.load_health(get_engine())


@st.cache_data
def cached_milestones() -> list[dict]:
    return data.load_milestones()


def md(text: str) -> str:
    """Escape characters that Markdown would treat as formatting (e.g. "$" starts math)."""
    return re.sub(r"([\\`*_\[\]$<>#~|])", r"\\\1", text)


def safe_url(url: str) -> str:
    # Brackets in links (like EU CELEX numbers "R(04)") break Markdown links.
    return url.replace("(", "%28").replace(")", "%29").replace(" ", "%20")


def reload_button() -> None:
    if st.button("Reload data", help="Pages re-read the database every 5 minutes. Click to do it now."):
        st.cache_data.clear()
        st.rerun()


def show_html(html: str, fallback_height: int) -> None:
    """Show our own HTML page (never user input) in a frame that fits its content.
    Older Streamlit versions have no st.iframe; they get a fixed height worked out from the item count."""
    if hasattr(st, "iframe"):
        st.iframe(html, height="content")
    else:
        components.html(html, height=fallback_height, scrolling=True)
