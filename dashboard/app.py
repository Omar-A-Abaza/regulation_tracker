"""The dashboard. Run from the project folder:

    streamlit run dashboard/app.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Streamlit only adds this file's folder to the import path; we need the project folder too.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")


def load_secrets() -> None:
    """On Streamlit Cloud, settings live in st.secrets instead of .env. The dashboard only reads
    the database, so it needs none, but DATABASE_URL (or anything else) can be set there."""
    try:
        secrets = dict(st.secrets)
    except Exception:  # no secrets file: that's normal
        return
    for key, value in secrets.items():
        if isinstance(value, str | int | float | bool):
            os.environ.setdefault(key, str(value))


load_secrets()

st.set_page_config(page_title="AI Regulation Tracker", page_icon="⚖️", layout="wide")

pages = [
    st.Page("fuse_board.py", title="Fuse board", icon="💣", default=True),
    st.Page("documents.py", title="All documents", icon="📄", url_path="documents"),
]
st.navigation(pages).run()
