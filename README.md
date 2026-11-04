# AI Regulation Tracker

> Automatic monitoring of AI regulation across the EU and the US, with a dashboard that answers one question first: **what changed this week?**

![The "What's new" page](docs/images/home.png)

## Why this exists

AI rules change fast, and they don't come from one place. An EU guidance document lands on one website, a US executive order on another, and a deadline quietly moves in a third. Compliance teams can't check every source every day, and when one is missed, the gap usually shows up at the worst time.

This tracker watches the official sources for you. It collects new laws, guidance and enforcement actions, notices when a law's text or a key page changes, and shows everything in a dashboard a non-specialist can read in two minutes. It's built with **general-purpose AI (GPAI) providers** in mind: companies that build or offer large AI models and fall under the EU AI Act's GPAI rules.

## What it tracks

| Source | What it watches | How |
|---|---|---|
| **EUR-Lex** (EU law) | Amendments, corrections, implementing rules and reports linked to the EU AI Act, plus new full-text versions of the Act | The EU Publications Office's official data service (SPARQL) |
| **EU AI Office** | Guidance, standards and consultations about the AI Act | The site's official news feed (RSS) |
| **NIST** | AI Risk Management Framework updates, model evaluations, AI guidance | NIST's topic news feeds (RSS) |
| **Federal Register** | White House AI executive orders, and agency AI rules and notices (FTC, Commerce, and others) | The Federal Register's official API |
| **Watched pages** | The NIST AI RMF page, the AI RMF Playbook, and the Colorado SB 26-189 bill page | A fingerprint of each page, compared on every run |

The database starts with **14 hand-checked documents** (the AI Act, the GPAI Code of Practice and guidelines, NIST's AI RMF and Generative AI Profile, key executive orders, and the California and Colorado laws). On its first run it finds about **60 more** on its own.

## What it does

- **Finds new documents automatically**, from official sources only.
- **Spots changes, not just new items.** For example, when a watched page changes, it saves an update that quotes the new text, and when the EU publishes a new full-text version of the AI Act, it flags it.
- **Tells "really new" apart from "old but newly found".** The first time a source is checked, everything looks new. The tracker only counts later finds as news, so the weekly view stays honest.
- **Filters the noise.** A Federal Register search for "artificial intelligence" returns 450+ documents since 2025, and most only mention AI once. The tracker keeps the ~33 that are actually about AI, using rules tested against real documents.
- **Shows its own health.** Every run is logged. If a source fails, the dashboard says so, so "nothing new" never hides "something broke".
- **Tracks deadlines**, including ones that moved.

## The dashboard

**What's new:** the status message, new items this week, the next deadline, and every recent update with its source, date, a plain-English note and tags. You can filter by framework, category (GPAI, high-risk, banned uses, fines and enforcement, and more), website, date range and search.

**Timeline:** every AI Act phase-in date plus key US state deadlines, with days left or days since. Deadlines the EU pushed back are shown with their old and new dates.

![The Timeline page](docs/images/timeline.png)

## GPAI focus

The EU AI Act has a separate chapter for general-purpose AI models. Since **Aug 2, 2025**, every GPAI provider must keep technical documentation, inform companies that build on its model, follow a copyright policy that respects opt-outs, and publish a training-data summary (Article 53). Models trained with more than 10²⁵ FLOPs are presumed to carry **systemic risk** (Article 51) and have extra duties: adversarial testing, risk mitigation, serious-incident reporting and cybersecurity (Article 55). Since **Aug 2, 2026**, the European Commission can fine GPAI providers directly, up to **€15M or 3%** of worldwide turnover (Article 101).

The dashboard's **GPAI** filter pulls out documents about these rules. A plain-English summary of the key articles is in [docs/TO_READ.md](docs/TO_READ.md).

## Facts are checked against the source

Every deadline and starting document links to its official source. Building this surfaced several commonly repeated "facts" that are now out of date:

- **The EU high-risk deadline is no longer Aug 2, 2026.** The Digital Omnibus on AI (Regulation (EU) 2026/1744) moved it to **Dec 2, 2027** (Annex III) and **Aug 2, 2028** (Annex I).
- **€35M / 7% is not the fine for everything.** It applies to banned practices only. GPAI fines are €15M / 3%.
- **The 10²⁵ FLOP threshold is in Article 51**, not Article 55.
- **Colorado's AI Act (SB 24-205) never took effect.** It was replaced by SB 26-189, with duties starting Jan 1, 2027.
- **The UK AI Safety Institute** is now the **AI Security Institute**.

Details are in [docs/day1_findings.md](docs/day1_findings.md).

## How it works

```mermaid
flowchart LR
    subgraph Sources
        A[EUR-Lex<br/>data service]
        B[EU AI Office<br/>news feed]
        C[NIST<br/>news feeds]
        D[Federal Register<br/>API]
        E[Watched pages]
    end
    A & B & C & D --> S[Scrapers<br/>+ AI filters + tagging]
    E --> W[Page watcher<br/>+ change summary]
    S & W --> DB[(SQLite database<br/>documents · page fingerprints · scrape log)]
    DB --> UI[Streamlit dashboard<br/>What's new · Timeline]
```

## Setup

You need [conda](https://docs.conda.io/) (or any Python 3.12 setup).

```bash
conda create -n regtracker python=3.12
conda activate regtracker
pip install -r requirements.txt

python main.py init-db    # create the database (data/tracker.db)
python main.py seed       # load the 14 starting documents
python main.py scrape     # check every source (about 30 seconds)

streamlit run dashboard/app.py    # open http://localhost:8501
```

### Commands

| Command | What it does |
|---|---|
| `python main.py scrape` | Check every source and watched page |
| `python main.py scrape --source nist` | Check one source (`eurlex`, `eurlex_versions`, `eu_ai_office`, `nist`, `federal_register`, `pages`) |
| `python main.py new` | List what's really new (last 7 days; `--days 30` for more) |
| `python main.py list` | List the latest documents |
| `python main.py runs` | Show the scrape log, including any errors |

## Project structure

```
scrapers/      one file per source, plus shared tools (polite HTTP client, RSS reader)
processors/    tagging (classifier.py) and change summaries (differ.py)
database/      the 3 tables and the helper functions everything uses
dashboard/     the Streamlit app: pages, data loading, and charts
data/          the timeline, the starting documents, and the list of watched pages
tests/         66 automated tests, using saved copies of real responses
docs/          build notes, the fact check, and the AI Act summary
main.py        the commands above
```

## Testing

```bash
pytest
```

The tests run offline, against saved copies of real responses from each source. They cover the parsers, the AI filters, de-duplication, change detection, the "really new" logic, the scrape log, and both dashboard pages end to end.

## Design choices

- **Official channels first.** Each source is read through its API, data service or news feed where one exists, so nothing depends on a fragile page layout.
- **Polite, and no getting around blocks.** Requests are rate-limited and identify the tracker, and every address it uses was checked by hand against that site's robots.txt rules. When a site blocks automated access (like the California legislature's bill pages), it's left out rather than worked around.
- **Every number has a source.** Deadlines and starting documents are hand-checked against the official text and link to it.
- **Honest empty states.** "Nothing new" is only shown when every source was checked successfully.

## Limitations and roadmap

**Not built yet:**
- **AI summaries.** Each new document will get a short summary: who it affects, key deadlines, required actions, and an urgency level. The database is already set up for this.
- **A cross-framework map** linking EU AI Act articles to NIST AI RMF and ISO/IEC 42001.
- **A GPAI compliance checklist** and a 10²⁵ FLOP threshold calculator.
- **An enforcement tracker** (fines and investigations under AI laws).
- **Alerts** (Slack, Teams or email) and **a daily schedule**, to run on a server (EC2 or a scheduled cloud function).
- **More sources:** the UK AI Security Institute, the FTC, state legislatures, and the OECD.

**Known limits:**
- **The EU AI Office feed only holds its 10 newest items**, so the tracker needs to run at least every week or two not to miss any.
- **Tagging is keyword-based for now**, so about a third of documents are tagged "Other". The AI summaries will replace it.
- **California's bill pages are behind a bot check**, so SB 53 is tracked through the starting data only.

## Disclaimer

This is a monitoring tool, not legal advice. Always check the official source before acting on anything it shows.
