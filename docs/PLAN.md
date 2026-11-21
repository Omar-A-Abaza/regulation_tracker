# Final-stretch plan: always online, updates itself weekly, fuse UI

Goal: finish the project for good. The dashboard stays online without the Pi,
updates itself once a week, and gets a new "fuse" look.

## 0. Setup (before the unattended run; needs Omar's approval)

- Conda env `regtracker` from `environment.yml` (Miniforge at `~/miniforge3`).
- `pip install -r requirements.txt`. No new packages. The fuse view is plain HTML/SVG/CSS/JS
  inside Streamlit (`st.components.v1.html`), so no npm and no new libraries.
- Build a local DB: `python main.py init-db && python main.py seed && python main.py scrape`.
  Summaries need `ANTHROPIC_API_KEY` in `.env`. Without it, the UI still works and shows
  "no AI summary yet".
- Run `pytest` to get a baseline (the README says 107 tests).

## 1. Always online: Streamlit Community Cloud

- Hosted free at `https://<name>.streamlit.app`, built from the GitHub repo's `main` branch.
  It redeploys on every push, so the Pi doesn't need to be on.
- Code changes:
  - `.streamlit/config.toml`: drop `address = "localhost"`, which blocks the cloud.
  - Commit the database: change `.gitignore` from `data/*.db` to keep `data/tracker.db`.
    It's the app's only data, and the "really new vs newly found" logic needs its history.
    First, check its size. If it's over ~50 MB, drop `raw_text` for big documents from the
    committed copy.
  - `dashboard/app.py`: read secrets from `st.secrets` as well as `.env`. The dashboard only
    reads the DB, so it needs no secrets at all.
- Omar does this once, by hand: share.streamlit.io → sign in with GitHub → New app →
  repo `Omar-A-Abaza/regulation_tracker`, branch `main`, file `dashboard/app.py`.
- Note: free apps go to sleep after a few days with no visitors. The first visitor after
  that clicks "wake up" and waits about 30 seconds. The data is unchanged.

## 2. Weekly update: GitHub Actions cron (replaces crontab)

`.github/workflows/weekly.yml`:
- `on: schedule: cron "0 7 * * 1"` (every Monday 07:00 UTC) plus `workflow_dispatch` for a manual run button.
- Steps: checkout → setup-python 3.12 → `pip install -r requirements.txt` →
  `python main.py weekly --yes` (scrape, summarize new items, email) → if `data/tracker.db`
  changed, commit it as "weekly update YYYY-MM-DD" and push. The push makes Streamlit redeploy.
- Secrets (Omar sets these with `gh secret set`): `ANTHROPIC_API_KEY`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`.
- `summarize` currently asks before spending. Add a `--yes` flag (or run without asking when
  there's no terminal) that still respects `SUMMARY_BUDGET_USD`.
- Failures: the job fails if every source fails, so GitHub emails Omar. If only some
  sources fail, that's still logged in `scrape_runs` and shown on the dashboard.
- Optional backup: a Pi crontab line running the same thing. Off by default.

## 3. New UI: the fuse board (home page)

Every item with a deadline is a **bomb with a lit fuse**:
- Items: every milestone in `data/timeline.yaml`, plus documents whose AI summary has a
  `key_deadline` in the future (marked as "from a document").
- Fuse length = time left. Use a log scale capped at ~3 years, so items 2 weeks out and
  2 years out both look right. A spark burns at the end of each fuse.
- Urgency: ≤30 days is red with a fast, bright spark; ≤90 days is orange; later is gray-blue
  with a slow spark.
- Passed deadlines are **exploded bombs**: a burst icon, "In force since Aug 2, 2025", and
  muted styling. They go in a collapsible "Already blew" row.
- Moved deadlines (Digital Omnibus) get a **spliced fuse**. A knot marks the old date, with
  the label "Extended +16 months by Reg. 2026/1744".
- **Hover (or tap on a phone)** shows a card with: title, date, days left or days since,
  plain-English summary, who's affected, actions to take, urgency badge, articles, and
  source link. For milestones, it also lists the linked documents (same framework or
  categories) with their AI bullets.
- Sorted by soonest first. Filter chips at the top: EU / US / state, and categories
  (GPAI, high-risk, …).
- Header strip: "Updated <last scrape date>" · new this week · needs action · source health
  dot (green, or red with the name of the failing source).
- Works in light and dark mode, on phones (fuses stack vertically, and tap opens the card),
  and with the keyboard (each bomb can be focused, and the card shows on focus).
  Respects `prefers-reduced-motion` (no spark animation).
- How it's built: `dashboard/fuse.py` turns milestones and documents into one JSON list and
  renders `dashboard/static/fuse.html` (inline SVG + CSS + small JS) with
  `components.html(...)`. The iframe height is worked out from the item count.
  Hover cards stay inside the iframe.

## 4. Second page: "All documents"

- Top: a compact fuse strip (same component, small mode) for the next 5 deadlines.
- Below: every document in the DB as a searchable, sortable list with: title (linked),
  source (EUR-Lex / EU AI Office / NIST / Federal Register / watched page / seed), framework,
  categories, published date, detected date, urgency badge, and "really new" marker.
  Click to expand the full AI summary.
- Keep the filters that `home.py` has today (framework, category, source, urgency, date
  range, search) and the shareable `?category=…` URL parameters.
- Navigation: "Fuse board" (default) and "All documents". The old Timeline page is merged
  into the fuse board. Keep `charts.py` only if something still uses it.

## 5. Tests, docs, finish

- Tests: fuse data building (log-scale length, urgency buckets, exploded and moved logic,
  documents with `key_deadline`), plus the `--yes` flag. Update `test_dashboard.py` for the
  new pages (Streamlit `AppTest`). The full suite must pass.
- Screenshots: render the new pages headless and replace `docs/images/home.png` and `timeline.png`.
- README: new screenshots, the live link, "updates every Monday automatically", and how to
  run the weekly job by hand.
- Commit on a branch `final-ui`, push, and open a PR. Omar merges it, then deploys on
  Streamlit Cloud.

## Done when

- [ ] Live URL works and shows the fuse board
- [ ] Hover/tap on any fuse shows its summary card
- [ ] "All documents" lists every document with its source
- [ ] Manual run of the weekly workflow succeeds and the site updates after it
- [ ] Tests pass, README updated
