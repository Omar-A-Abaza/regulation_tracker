# Day 3 Notes (Nov 2, 2026)

All 4 websites now have working scrapers. The database has **74 documents**.

## How each website is read

| Website | How we get in | What we keep | Found on first run |
|---|---|---|---|
| EUR-Lex | EU data service (SPARQL) | Changes, corrections, rules and reports linked to the AI Act | 8 |
| EU AI Office | The site's news feed (RSS) | AI items only, not events or funding calls | 2 |
| NIST | NIST's topic news feeds (RSS) | News with an AI word in the title. No events, staff spotlights or job posts. | 22 |
| Federal Register | Official data service (API) | See the AI filter below | 33 |

## The Federal Register AI filter

A search for "artificial intelligence" returns **40 White House documents** and **412 agency documents** since 2025. Most only mention AI once.

- **White House documents:** keep if the title is about AI, **or** the full text says "AI" at least 8 times and at least 5 times per 1,000 words.
  - Real numbers from Day 3: orders about AI had 8 to 194 mentions (10+ per 1,000 words). Orders that only mention AI had 0 to 6.
  - Example: "Launching the Genesis Mission" has no AI in the title, but its text is about AI, so it's kept.
- **Agency documents:** keep only if AI is in the title. Skip routine paperwork (information collections, meeting notices).
- **Result:** 33 kept (10 White House, 23 agency).

## Things we learned

- **The EU AI Office web pages block programs (error 403), but its news feed is open.** The site's robots.txt allows the feed. The feed only holds the **10 newest items** across all EU digital topics. So we need to run at least every week or two, or we may miss things.
- **The US government now says "super intelligence" for AI.** NIST renamed its "artificial intelligence" topic to "super intelligence" (2026), in line with EO 14434. Our filters look for both terms.
- **Important finds:**
  - **EU:** the first harmonised standard supporting the AI Act was published (Oct 19, 2026).
  - **FTC:** a policy statement on AI systems that suppress accuracy (Jul 7, 2026), and an enforcement case against an AI content company (Workado, May 2025).
  - **NIST / CAISI:** safety tests of frontier models (DeepSeek V4 Pro, Kimi K2 and K3), and guidance on incident response for AI training.

## Still rough

- **26 of 74 documents are tagged "other".** Word matching only goes so far. The AI model takes over tagging in Week 2.
- **A few NIST items are research news**, like an AI model for fire evacuation. They're not rules. The Week 2 AI summary will rate them "Informational".
