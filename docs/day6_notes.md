# Day 6 Notes (Nov 3, 2026)

The Timeline page is built. Open the dashboard and click **📅 Timeline** in the menu.

## What's on the page

| Part | What it shows |
|---|---|
| **3 number boxes** | Next deadline (29 days: Dec 2, 2026) · Coming up (5) · Already in force (6) |
| **Timeline chart** | One row per place (EU, California, Colorado), a dot per deadline, and a "Today" line. Hover a dot for details. |
| **Deadlines that moved** | The 2 EU deadlines the Omnibus pushed back: old date crossed out → new date, and how many extra days. |
| **Coming up** | Soonest first, with "in X days" |
| **Already in force** | Most recent first, with "X days ago" |
| **Filters** | Where (EU / California / Colorado) and Category (e.g. GPAI) |

## How the chart shows things

| What | How |
|---|---|
| In force | ✅ green circle |
| Within 90 days | ⏳ amber diamond |
| Later | 🗓️ gray square |
| A moved deadline | Its own lane under its row: a hollow gray dot at the old date, a dashed line, then the dot at the new date |

Each state has its **own shape and label**, not just a color, so colorblind readers can tell them apart. The colors come from the charting guide's fixed status colors and work in light and dark mode.

## Files

| File | What it does |
|---|---|
| `dashboard/timeline.py` | The Timeline page |
| `dashboard/charts.py` | The timeline chart (separate, so it can be tested) |
| `dashboard/common.py` | Helpers both pages share (moved out of `home.py`, so importing them doesn't draw the Home page) |
| `dashboard/data.py` | New timeline helpers: state, "in X days", filters, moved deadlines |
| `tests/test_timeline.py` | 11 tests, including 2 that run the whole page |

## Fixed along the way

- **The two moved-deadline lines overlapped** on the EU row and looked like one long line. Each moved deadline now has its own lane.
- **Dark mode didn't work.** Setting a custom color in `.streamlit/config.toml` locks Streamlit into light mode, so that setting is removed. The dashboard now follows the computer's light/dark setting (Home page too).
- **The "Today" line was faint in dark mode.** It's now a lighter gray there.

## Known quirk

If you open the `/timeline` link directly as the **very first visit** after starting the dashboard, a "Page not found" pop-up appears over the (correctly loaded) Timeline page. Streamlit only learns the page names after the app's first run. Clicking **Timeline** in the menu, or any later visit, doesn't show it.

## Tested

- **66 automated tests pass.**
- **Screenshots of the live page** in light and dark mode look right.
