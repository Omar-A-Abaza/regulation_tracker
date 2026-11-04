# To Read: 6 Articles of the EU AI Act

**Time:** about 45 minutes total.
**When:** any time this week. It doesn't block the build.

---

## First, the big picture (read this once)

### What the paper is
All 6 articles come from one law: the **EU AI Act**. Its official name is **Regulation (EU) 2024/1689**. It's the world's first big law that covers AI. It sorts AI into levels of risk and sets rules for each level.

### Who wrote it
- The **European Commission** (the EU's executive branch) proposed it in **April 2021**.
- The **European Parliament** (elected by EU citizens) and the **Council of the EU** (the 27 countries' governments) argued over it and changed it. Then they passed it.
- It was signed on **June 13, 2024** and became law on **August 1, 2024**.
- In **July 2026**, a second law changed some of it: the **Digital Omnibus on AI**, Regulation (EU) 2026/1744. It mostly pushed deadlines back and added new bans.

### Why it matters
- It applies to any company whose AI is **used in the EU**, even if the company is American. That includes American companies.
- The fines are huge: up to **7% of a company's yearly sales worldwide**.
- Other countries copy it. California's SB 53 borrows ideas from it.

### Where to read
- **Easiest:** [artificialintelligenceact.eu](https://artificialintelligenceact.eu/ai-act-explorer/). It shows one article per page. Each article below has its own link.
- **Official:** [EUR-Lex: the AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). This is the real legal text. It's very long. Press Cmd+F and search for "Article 53".
- **The July 2026 changes:** [EUR-Lex: the Digital Omnibus](https://eur-lex.europa.eu/eli/reg/2026/1744/oj).
- ⚠️ The easy site may not show the July 2026 changes yet. Where this matters, it's flagged below.

### Why you're reading these 6
A company that makes **GPAI** (general-purpose AI). It's an AI that can do many tasks, not just one. These 6 articles are the core of what a GPAI company must know:

| Article | One line |
|---|---|
| 5 | What AI is **banned** |
| 51 | When a GPAI model is "**systemic risk**" (the big-model rule) |
| 53 | What **every** GPAI company must do |
| 55 | What **big** GPAI companies must do on top of that |
| 99 | **Fines** in general |
| 101 | **Fines for GPAI** companies |

### What your bullet points should cover
Write **2–3 bullets per article, in your own words**. Use the "My notes" spot under each article. Try to cover:

1. **What it says.** One plain sentence, as if you were telling a friend.
2. **Does it apply to the company, and how?** Yes, no, or maybe, and why.
3. **The "so what".** One thing a compliance team would actually **do** because of this rule.

**Good example:**
> - Every GPAI company has to publish a summary of what data it trained on, using the EU's form.
> - Applies to the company: yes, if it trains or fine-tunes its own models.
> - So what: someone needs to own this summary and update it when the model changes.

**Not so good:** copying the law's wording. If you can't say it simply, read it again.

### Why the notes matter
- They become the **GPAI Hub** page of the tracker in Week 3.
- They go into the **README**, which the hiring manager will read.
- In an interview, you'll be able to explain these rules in your own words. That's the real goal.

---

## Article 5: Banned AI practices

**Link:** [Article 5 (easy)](https://artificialintelligenceact.eu/article/5/) · Official: EUR-Lex, search "Article 5"
**Length:** long (about 15 minutes)

**Quick summary:**
A list of AI uses that are **not allowed at all** in the EU, no matter what. Examples:
- AI that **tricks or manipulates** people in ways that harm them
- AI that **takes advantage of weak spots**, like age or disability
- **Social scoring**: rating people on how they behave, then treating them badly because of it
- Guessing if someone will **commit a crime** just from their personality
- **Scraping faces** from the internet to build face-recognition databases
- Reading **emotions** at work or school (with some medical and safety exceptions)
- Using faces or bodies to guess someone's race, religion, politics or sex life
- **Live face recognition** by police in public places (with narrow exceptions)

**New since July 2026:** bans on AI-made **fake nude images** and **child abuse images**. These start **Dec 2, 2026**. ⚠️ The easy site may not show these yet. Check the Omnibus.

**Started:** Feb 2, 2025.

**Why we chose it:** It's the strictest part of the law, with the biggest fines. Every AI company must check that its product can't be used for these things.

**What to look for:**
- The full list of bans. Count them.
- The **exceptions**, especially for police use.
- Could a general AI tool like this one be **misused** for any of these? (Think about the fake-image ban.)

**My notes:**
-
-
-

---

## Article 51: When a GPAI model is "systemic risk"

**Link:** [Article 51 (easy)](https://artificialintelligenceact.eu/article/51/) · Official: EUR-Lex, search "Article 51"
**Length:** short (about 5 minutes)

**Quick summary:**
Some GPAI models are so powerful that the EU says they carry **"systemic risk"**. That means they could cause harm on a big scale. A model counts if:
- It has "high-impact" abilities, judged by tests and benchmarks, **or**
- The EU Commission decides it does.

The key rule: if training used more than **10²⁵ computing operations** (FLOPs), the model is **presumed** to be systemic risk. The EU can change this number later.

**Why we chose it:** This is the line between "normal" GPAI duties (Article 53) and "big model" duties (Article 55). Knowing which side a model is on is the first question for any GPAI company.

**What to look for:**
- The word **"presumed"**. Being over 10²⁵ doesn't make it automatic forever. What does that mean?
- The **two ways** a model can become systemic risk.
- Who can **change the threshold**.
- Bonus: Article 52 (right after it) says a company must **tell the EU within 2 weeks** once it crosses the line.

**Watch out:** the spec put the 10²⁵ rule in Article 55. It's actually here, in Article 51(2).

**My notes:**
-
-
-

---

## Article 53: Duties for every GPAI company

**Link:** [Article 53 (easy)](https://artificialintelligenceact.eu/article/53/) · Official: EUR-Lex, search "Article 53"
**Length:** short (about 7 minutes)

**Quick summary:**
Every company that makes a GPAI model must:
1. Keep **technical documents** about the model (how it was trained and tested). Give them to the EU when asked. (The details are in Annex XI.)
2. Give **information to other companies** that build products on top of the model. (The details are in Annex XII.)
3. Have a **copyright policy**, including respecting websites that say "don't use my content for AI training".
4. **Publish a summary of the training data**, using the EU's official form.

**Exception:** truly **open-source** models skip duties 1 and 2, unless they're systemic risk.

**Started:** Aug 2, 2025. (Models already out before then have until Aug 2, 2027.)

**Why we chose it:** **This is the main checklist for a GPAI company.** It's the most important article for this job.

**What to look for:**
- The **4 duties**. Could you list them from memory?
- The **open-source exception**, and when it doesn't apply.
- The mention of **codes of practice**. Following the EU's GPAI Code of Practice is one way to show you comply.
- Think: a company may use other companies' models **and** may build its own. When is it a "provider"?

**Watch out:** the spec said "report energy consumption" was an Article 55 duty. Energy use is actually part of the **technical documents** in Annex XI, which ties to this article.

**My notes:**
-
-
-

---

## Article 55: Extra duties for big (systemic-risk) models

**Link:** [Article 55 (easy)](https://artificialintelligenceact.eu/article/55/) · Official: EUR-Lex, search "Article 55"
**Length:** short (about 5 minutes)

**Quick summary:**
On top of Article 53, systemic-risk model makers must:
1. **Test the model**, including "adversarial testing" (trying to break it on purpose, also called red-teaming).
2. **Find and reduce** risks that could hit the whole EU.
3. **Report serious incidents** to the EU AI Office quickly, and say what they did to fix them.
4. Keep strong **cybersecurity** for the model and the computers it runs on.

**Started:** Aug 2, 2025.

**Why we chose it:** If a model crosses the Article 51 line, these duties kick in. Big AI labs (OpenAI, Anthropic, Google) are in this group. A GPAI company needs to know whether it is.

**What to look for:**
- The **4 extra duties**.
- What counts as a **"serious incident"**. (Hint: check the definitions in Article 3.)
- How this connects to the **safety chapter** of the GPAI Code of Practice.

**My notes:**
-
-
-

---

## Article 99: Fines (general)

**Link:** [Article 99 (easy)](https://artificialintelligenceact.eu/article/99/) · Official: EUR-Lex, search "Article 99"
**Length:** medium (about 8 minutes)

**Quick summary:**
Each EU country sets its own fines, within these caps. It's whichever amount is **higher**:

| What you did wrong | Max fine |
|---|---|
| Used a **banned** AI practice (Article 5) | **€35 million or 7%** of yearly worldwide sales |
| Broke **most other rules** | **€15 million or 3%** |
| Gave **wrong or misleading information** to officials | **€7.5 million or 1%** |

For **small companies and startups**, it's whichever is **lower**.

**Why we chose it:** Fines are what make a law real. The hiring manager will expect you to know these numbers.

**What to look for:**
- The **3 levels** above.
- **Who** gives these fines (each country, not the EU itself).
- What they consider when **deciding the amount** (how bad, how long, did the company cooperate).

**Watch out:** the spec said €35M / 7% for everything. That's only for **banned** uses.

**My notes:**
-
-
-

---

## Article 101: Fines for GPAI companies

**Link:** [Article 101 (easy)](https://artificialintelligenceact.eu/article/101/) · Official: EUR-Lex, search "Article 101"
**Length:** short (about 5 minutes)

**Quick summary:**
GPAI companies are fined by the **EU Commission directly**, not by each country. The cap is **€15 million or 3%** of yearly worldwide sales, whichever is higher. They can be fined for (on purpose or by carelessness):
- Breaking the GPAI rules
- Not handing over documents or information, or giving wrong information
- Not following the EU's orders
- Not letting the EU test the model

**Started:** Aug 2, 2026. This is a year **after** the GPAI rules started. That gap gave companies time to get ready.

**Why we chose it:** **This is the fine that applies to a GPAI company.** Since Aug 2, 2026, the EU can actually use it.

**What to look for:**
- **Who** fines (the Commission) and the **cap** (€15M / 3%).
- The **4 kinds** of wrongdoing.
- The company's **right to be heard** before a fine.
- Bonus: our scraper found **Implementing Regulation (EU) 2026/1755** (July 20, 2026), which sets out how the Commission runs its cases under the AI Act. It's likely linked to how these fines get decided. Worth a skim.

**My notes:**
-
-
-
