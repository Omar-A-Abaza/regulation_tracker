# Day 4 Notes (Nov 2, 2026)

Day 4 teaches the tracker to notice **changes**, not just new documents.

## What was built

| Part | What it does | Files |
|---|---|---|
| **Page watcher** | Takes a fingerprint of 3 pages each run. If a page changes, it saves a "Page updated" entry that quotes the new text. | `scrapers/page_watcher.py`, `processors/differ.py`, `data/watched_pages.yaml` |
| **AI Act text versions** | Catches a new full-text version of the AI Act, which means the law's text changed. | `scrapers/eurlex.py` (`EurLexVersionsScraper`) |
| **"Really new" check** | Old documents found on a scraper's first run don't count as news. | `database/repository.py` (`get_new_documents`) |
| **Scrape log history** | Shows every run: when, how long, what it found, and any errors. | `main.py runs` |
| **Database upgrades** | New columns get added to an existing database automatically. | `database/repository.py` |

## Watched pages

| Page | Why |
|---|---|
| NIST AI Risk Management Framework | NIST says the AI RMF is being revised. The page changes when the new version comes out. |
| NIST AI RMF Playbook | The page says the Playbook will be updated after the RMF is revised. |
| Colorado SB 26-189 | Shows the bill's status and changes. |

**Not watched:** the California SB 53 page sits behind a bot check ("Just a moment..."). We don't try to get around bot checks. It's on the to-do list.

## How "really new" works

| Kind of document | Counts as new? |
|---|---|
| Starting data (picked by hand) | Never |
| Found on a scraper's **first** run that worked | No. It's old material the website already had (a "backfill"). |
| Found on any **later** run | Yes |
| A "Page updated" entry | Yes. The first time we see a page we only take a fingerprint, so every later entry is a real change. |

## Commands

```
python main.py scrape --source all     # all scrapers + the page watcher
python main.py scrape --source pages   # only the page watcher
python main.py new                     # what's really new (last 7 days)
python main.py new --days 30
python main.py runs                    # the scrape log
```

## Tested

- **44 automated tests pass.**
- **Real run, twice:** every website shows "success", and nothing was saved twice.
- **Fake change on a copy of the database:** the watcher caught it and quoted the full sentence.

## Moved to the to-do list

- **The daily schedule.** You'd rather not run it on your Mac every day. Options for later: an AWS EC2 server, or an AWS Lambda function on a timer.
- **Watching the California SB 53 page** (it's behind a bot check).
