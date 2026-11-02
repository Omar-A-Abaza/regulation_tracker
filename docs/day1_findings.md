# Day 1 Findings (Oct 26, 2026)

What we checked, and what changed from the original spec.

## Facts that changed

| Topic | The spec said | What's true now | Source |
|---|---|---|---|
| EU high-risk deadline | Aug 2, 2026 | **Dec 2, 2027** (Annex III) and **Aug 2, 2028** (Annex I). Moved by the Digital Omnibus on AI. | [Reg. (EU) 2026/1744](https://eur-lex.europa.eu/eli/reg/2026/1744/oj) |
| New EU bans | — | AI-made fake nude images and child abuse images banned from **Dec 2, 2026** | Reg. (EU) 2026/1744 |
| Fines | €35M / 7% | That's only for **banned AI uses** (Art. 99(3)). GPAI fines are **€15M / 3%** (Art. 101), from Aug 2, 2026. | [AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |
| 10²⁵ threshold | Art. 55 | It's in **Art. 51(2)**. Art. 55 lists the extra duties. | AI Act |
| Older GPAI models | — | Models on the market before Aug 2, 2025 have until **Aug 2, 2027** (Art. 111(3)) | AI Act |
| Colorado | SB 24-205, GPAI law | It was **not** about GPAI, and it was **replaced** by **SB 26-189** (signed May 14, 2026). Main duties start Jan 1, 2027. | [leg.colorado.gov](https://leg.colorado.gov/bills/sb26-189) |
| California | AB 2930 failed, others active | **SB 53** (frontier AI) signed Sep 29, 2025, in effect Jan 1, 2026. Uses a **10²⁶** threshold. | [leginfo](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB53) |
| UK | AI Safety Institute | Now called the **AI Security Institute** | — |
| US orders | — | EO 14110 cancelled (Jan 2025). Current ones: EO 14179, 14365, 14409, 14434. | [Federal Register](https://www.federalregister.gov) |

## What we learned about the websites

| Website | Result | What it means |
|---|---|---|
| Federal Register | ✅ Data feed works | Easy. But a search for "artificial intelligence" also pulls in orders that only *mention* AI (veterans, nuclear). We need a stricter filter. |
| NIST | ✅ Pages load | Normal scraping should work. |
| EUR-Lex (way 1: read page) | ❌ Blocked (bot check) | As expected. |
| EUR-Lex (way 2: EU data service) | ✅ Works | We use this on Day 2. No to-do needed. |
| EU AI Office | ❌ Blocked (403 error) | New problem for Day 3. |
