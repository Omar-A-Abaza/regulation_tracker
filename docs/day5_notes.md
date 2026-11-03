# Day 5 Notes (Nov 2, 2026)

The real dashboard Home page is built. It reads the real database and the real scrape log.

## How to open it

```
conda activate regtracker
streamlit run dashboard/app.py
```
Then open http://localhost:8501. Only your computer can open it, because `.streamlit/config.toml` limits it to localhost.

## What's on the page

| Part | What it shows |
|---|---|
| **Status message** | Green: "Nothing new this week. We checked 6 sources and all are working." Yellow: a source failed, so we might be missing something. Yellow: the scrapers haven't run yet. |
| **3 number boxes** | New this week (really new only) · Published in the last 30 days · Days to the next deadline |
| **New this week** | Shown only when something is really new, with a green "New" badge |
| **Recent updates** | Each document: website, date, title, plain-English note, tags, link |
| **Filters (left side)** | Framework, category, website, date range, and search. An empty box means "everything". |
| **Website status** | Each source: working or not, last checked, new items on the last check, and any problem |

## Files

| File | What it does |
|---|---|
| `dashboard/app.py` | The entry point, and the page menu (Timeline joins on Day 6) |
| `dashboard/home.py` | The Home page |
| `dashboard/data.py` | Loading and filtering the data (no Streamlit, so it's easy to test) |
| `.streamlit/config.toml` | Theme, hides the "Deploy" button, localhost only |
| `tests/test_dashboard.py` | 14 tests, including 3 that run the whole page |

## Fixed along the way

- **Search for "FTC" found nothing**, because the documents say "Federal Trade Commission". The search now understands common short forms: FTC, EO, CAISI, FDA, DOE, DHS.
- **Dollar signs in titles** would have turned into math formatting. Titles are now escaped.
- **Links with brackets** (EU numbers like `R(04)`) would have broken. Fixed.
- **The dashboard was reachable from other computers** on the network. It's now limited to this Mac.

## Tested

- **57 automated tests pass.**
- **Checked against the real database:** 76 documents for all time, 16 tagged GPAI, and 2 found by searching "FTC".
- **Screenshots of the live page** look right.

## Not on the page (on purpose)

- **AI summaries:** a section appears automatically once Week 2 adds them. No "coming soon" placeholder, so the app doesn't look unfinished.
- **Moved deadlines and the "GPAI only" button:** still parked ideas. The Category filter already does "GPAI only".
