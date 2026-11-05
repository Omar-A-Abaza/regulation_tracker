# Week 2 Notes (Nov 4, 2026)

Week 2 adds **AI summaries** (Claude Sonnet 5.5) and a **weekly update email**.

## How the summaries work

1. **Get the full text.** EUR-Lex through the EU data service, Federal Register through its API, NIST and Colorado from their pages. If a document can't be fetched (EU AI Office pages, NIST PDFs, a few EU corrections), the summary is written from the title and description, and it says so.
2. **Ask the model** for a fixed set of fields:
   - 3-bullet summary
   - who's affected
   - key deadline
   - actions required
   - urgency (🔴 Action Required, 🟡 Watch, ⚪ Informational)
   - tags
3. **Save it in the database.** It's never redone unless the document's text changes.

## Money safety rails

| Rail | What it does |
|---|---|
| **Estimate first** | `summarize` shows the cost and asks "Go ahead? (y/n)" |
| **Dry run** | `summarize --dry-run` only shows the estimate |
| **Spending cap** | Stops a run at $1.50. Change it with `SUMMARY_BUDGET_USD` in `.env`. |
| **Size cap** | Skips documents over 40,000 tokens (whole laws) unless you add `--include-large` |
| **Once per document** | Never pays twice for the same text |
| **No key = no spending** | Without `ANTHROPIC_API_KEY`, it explains how to add one and stops |
| **Low effort** | The model uses its "low" thinking setting, enough for summaries and cheaper |

## Dry run on the real database (no key, nothing spent)

- Full text downloaded for 71 of 76 documents.
- **72 documents to summarize, about $1.35** (rough estimate; the exact count needs the key).
- 4 skipped as too long: the full AI Act, its updated full text, the AI diffusion rule, and (on the rough estimate) the Omnibus. The exact count may bring the Omnibus under the limit.

## The weekly email

- `python main.py digest` emails everything **really new** since the last email. Starting data and first-run backfill are never emailed. Action Required goes first.
- Each document is emailed **once** (the `notified_at` column).
- **Nothing new = no email.**
- `--preview` prints it instead of sending. `--test` sends the 3 latest summaries to yourself without marking anything.
- Sent through Gmail with an app password, using Python's built-in email tools.

## The weekly command

`python main.py weekly` = scrape all sources → summarize only the new documents (no question asked; the spending cap still applies) → send the email. This is the one command a scheduled job on EC2 or Lambda would run.

## Dashboard

- Each document shows its **urgency badge** and **3-bullet summary**. **Details** opens who's affected, the deadline, and what to do.
- New **Action Required** number box (last 90 days) and an **Urgency** filter.

## Tests

104 tests pass. The summarizer is tested with a **fake AI** and the email with a **fake mail server**, so tests never spend credit or send mail.
