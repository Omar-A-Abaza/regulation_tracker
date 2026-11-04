"""The dashboard. Run from the project folder:

    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Streamlit only adds this file's folder to the import path; we need the project folder too.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

st.set_page_config(page_title="AI Regulation Tracker", page_icon="⚖️", layout="wide")

pages = [
    st.Page("home.py", title="What's new", icon="🏠", default=True),
    st.Page("timeline.py", title="Timeline", icon="📅", url_path="timeline"),
]
st.navigation(pages).run()
