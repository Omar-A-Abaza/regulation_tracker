# The 6 Key EU AI Act Articles: Plain-English Summary

**Time:** about 20 minutes.
**You don't need to read the law itself.** This summary was written from the official text, including the July 2026 changes. Links to the real text are there if you ever want them.

---

## If you only remember 5 things

1. **Some AI is simply banned** (Article 5). The fine is the biggest in the law: **€35M or 7%** of yearly worldwide sales.
2. **Every company that makes a general-purpose AI model (GPAI)** must do **4 things** (Article 53): keep technical documents, inform companies that build on the model, have a copyright policy, and publish a training data summary.
3. **Very big models** (trained with more than **10²⁵** computing operations) are presumed **"systemic risk"** (Article 51) and have **4 extra duties** (Article 55): testing, risk management, incident reporting, cybersecurity.
4. **GPAI companies are fined by the EU Commission directly**: up to **€15M or 3%** (Article 101). This power started on **Aug 2, 2026**.
5. **New since July 2026:** AI that makes **fake nude images** or **child abuse images** is banned from **Dec 2, 2026**. This matters a lot for any company with image tools.

---

## The big picture

### What the law is
The **EU AI Act**, officially **Regulation (EU) 2024/1689**. It's the world's first big AI law. It sorts AI by risk and sets rules for each level:

| Level | Example | Rule |
|---|---|---|
| **Banned** | Social scoring | Not allowed at all (Article 5) |
| **High-risk** | AI that screens job applicants | Strict rules (mostly start Dec 2027) |
| **Transparency** | Chatbots, AI-made images | Tell people it's AI (Article 50) |
| **GPAI models** | Large language models | Their own chapter (Articles 51–56) |

### Who wrote it
- **Proposed** by the European Commission (the EU's executive branch) in **April 2021**.
- **Negotiated and passed** by the European Parliament (elected by EU citizens) and the Council of the EU (the 27 countries' governments).
- **Signed June 13, 2024. Became law August 1, 2024.**
- **Changed in July 2026** by the **Digital Omnibus on AI** (Regulation (EU) 2026/1744). It pushed deadlines back and added new bans.

### Why it matters
- It applies to **any company whose AI is used in the EU**, even an American one.
- The fines are some of the biggest in any tech law.
- Other places copy it. California's SB 53 borrows ideas from it.

### Words to know
| Word | Meaning |
|---|---|
| **Provider** | The company that **makes** the AI and puts it on the market under its name |
| **Deployer** | A company that **uses** someone else's AI in its work |
| **GPAI model** | A general-purpose AI model: one that can do many different tasks (like a large language model) |
| **Systemic risk** | Risk of harm on a big scale, across society, from a very powerful model |
| **AI Office** | The EU team, inside the Commission, that supervises GPAI models |
| **Placing on the market** | Making the AI available in the EU for the first time |
| **Turnover** | A company's yearly sales (revenue), worldwide |

---

## Article 5: Banned AI practices

**In one line:** a list of AI uses that are **not allowed at all** in the EU.
**Applies since:** Feb 2, 2025. The 2 new bans apply from **Dec 2, 2026**.
**Fine if broken:** up to **€35M or 7%** of yearly worldwide sales, whichever is higher.

### What's banned (the original 8)
1. **Manipulation.** AI that uses hidden ("subliminal") or deceptive tricks to change what people do, in a way that causes them **significant harm**.
2. **Exploiting weak spots.** AI that takes advantage of people because of their **age, disability, or social or economic situation**, causing significant harm.
3. **Social scoring.** Rating people over time based on their behavior or personality, then treating them badly **in unrelated situations**, or **out of proportion** to what they did.
4. **Predicting crime from personality.** Guessing if someone will commit a crime **only** from profiling or personality traits. (Allowed if it supports a human review based on real facts.)
5. **Scraping faces.** Building face-recognition databases by **collecting face photos from the internet or CCTV without targeting**.
6. **Reading emotions at work or school.** Not allowed, except for **medical or safety** reasons.
7. **Guessing sensitive traits from bodies or faces.** Using biometric data to guess someone's **race, politics, union membership, religion, sex life or sexual orientation**.
8. **Live face recognition by police in public.** Banned, with **narrow exceptions**: searching for kidnapping or trafficking victims or missing people, stopping an imminent threat or terror attack, or finding suspects of serious crimes. Even then, it needs **a judge's (or independent authority's) approval**, with 24 hours to get it in an emergency.

### The 2 new bans (added July 2026, apply from Dec 2, 2026)
9. **Fake intimate images.** AI that creates or edits realistic images, videos or audio of a **real, identifiable person's intimate parts or sexual activity, without their clear consent**.
10. **Child sexual abuse material.** AI that creates or edits it.

**When is the company that made the AI responsible?** This detail is very important:
- If making this material is **what the AI is for**, it's banned.
- **Or** if the AI **can easily and reliably** produce it, without major technical changes, **and** the company **doesn't have reasonable safety measures** to stop it (including against foreseeable misuse) and to fix misuse when it's reported.
- A **user** breaks the ban only if they **use** the AI on purpose to make this material.
- Edits that don't reveal more of the body or change the sexual nature (like changing a background) don't count.

### What it means for a GPAI company
- Its general AI isn't *made* for any of these things, so most bans won't apply directly.
- **But the new image bans can.** A general tool that can make images must have **strong safety filters**, and a process to **fix misuse when it's reported**. Without them, the company itself breaks the ban.
- Compliance work: test that the product **can't easily be used** for these practices, and keep records of the safety measures.

**Say it in an interview:**
> "Article 5 bans a short list of AI uses outright. For a general AI company, the most important part is the new ban on AI-made intimate images, from December 2026. If your tool can produce them and you don't have solid safeguards, you're liable, not just the user."

---

## Article 51: When a GPAI model is "systemic risk"

**In one line:** the rule that decides if a model is so powerful it gets **extra duties**.
**Applies since:** Aug 2, 2025.
**Length of the real text:** very short ([read it](https://artificialintelligenceact.eu/article/51/)).

### What it says
A GPAI model is **"systemic risk"** if **either**:
1. It has **"high-impact capabilities"**: measured by technical tests and benchmarks. **Or**
2. **The EU Commission decides** it has similar capabilities or impact. It can decide on its own, or after a warning from its panel of independent scientists. It uses a list of criteria (in Annex XIII), like the number of users and how capable the model is.

**The 10²⁵ rule:** if training took more than **10²⁵ computing operations** (called "FLOPs"), the model is **presumed** to have high-impact capabilities.
- "Presumed" means it's assumed, but the company can argue it isn't.
- For a sense of scale: this is roughly the level of the biggest frontier models.

**The EU can change the number** later, as computers get faster and training gets more efficient.

**Related, Article 52:** a company must **tell the Commission within 2 weeks** once its model crosses the line, or once it knows it will.

### What it means for a GPAI company
- **First question for any GPAI company:** "Are we over the line?" That decides whether Article 55 applies.
- A company that only **uses** someone else's big model isn't the "provider" of that model. But if it **trains or substantially changes** its own model, it needs to know its training compute.

**Say it in an interview:**
> "Article 51 sets the systemic-risk line. Models trained with over 10²⁵ FLOPs are presumed systemic risk, and the Commission can also designate models. Crossing it means notifying the Commission within two weeks and taking on Article 55's extra duties."

---

## Article 53: Duties for every GPAI company

**In one line:** the **main checklist** for any company that makes a GPAI model.
**Applies since:** Aug 2, 2025. Models already on the market before then have until **Aug 2, 2027**. Fines possible since **Aug 2, 2026**.
**Length of the real text:** short ([read it](https://artificialintelligenceact.eu/article/53/)). **The one article worth reading in full.**

### The 4 duties
1. **Technical documents.** Write and keep up to date documents about the model: how it was **trained and tested**, and the **test results**. The minimum content is in Annex XI (it includes things like the model's design, training data, compute used and **energy use**). Hand them over when the AI Office or national authorities ask.
2. **Information for companies that build on the model.** Give companies that put the model into their own products enough information to **understand what it can and can't do**, and to meet their own legal duties (minimum content in Annex XII). Trade secrets can be protected.
3. **A copyright policy.** Have a policy to follow EU copyright law. In particular, **respect websites and creators who say "don't use my content for AI training"** (the "opt-out"), using up-to-date technology to detect it.
4. **A public training data summary.** Publish a **detailed enough summary of the content used to train the model**, using the **AI Office's official form** (template).

### Other important points
- **Open-source exception.** Truly open-source models (with public weights and a free license) **skip duties 1 and 2**. **But not if they're systemic risk.** And they still need duties 3 and 4.
- **Cooperate with the authorities** when asked.
- **The Code of Practice is a shortcut.** A company can follow the EU's **GPAI Code of Practice** (published July 10, 2025) to show it complies, until official technical standards exist. A company that doesn't follow the code must prove compliance **another way**, which is harder.
- **Trade secrets** handed over stay confidential.
- **Related, Article 54:** a GPAI company **based outside the EU** must name an **authorized representative inside the EU** before putting its model on the EU market.

### What it means for a GPAI company
- This is **the core compliance work**: someone has to own each of the 4 duties and keep them current **every time the model changes**.
- **Copyright opt-outs** are a hot topic: the company must be able to show how its data collection respects them.
- Signing the **Code of Practice** is the simplest way to show compliance.

**Say it in an interview:**
> "Article 53 has four duties for every GPAI provider: technical documentation, information for downstream providers, a copyright policy that respects opt-outs, and a public training-data summary on the AI Office's template. The Code of Practice is the easiest way to show compliance."

---

## Article 55: Extra duties for systemic-risk models

**In one line:** what the **biggest** models must do **on top of** Article 53.
**Applies since:** Aug 2, 2025.
**Length of the real text:** very short ([read it](https://artificialintelligenceact.eu/article/55/)).

### The 4 extra duties
1. **Test the model** with standard, up-to-date methods, **including adversarial testing** (trying to break it on purpose, also called **red-teaming**), and document the tests.
2. **Find and reduce risks** that could cause harm across the EU, including where those risks come from (how the model is built, released or used).
3. **Track and report serious incidents** to the AI Office **without undue delay**, plus what's being done to fix them.
4. **Strong cybersecurity** for the model **and** the buildings and computers it runs on.

**"Serious incident"** (defined in Article 3) means an AI problem that leads to: **death or serious harm to health**, **serious damage to critical infrastructure**, **a breach of fundamental rights**, or **serious damage to property or the environment**.

**The Code of Practice** (its **safety and security** chapter) can be used to show compliance here too.

### What it means for a GPAI company
- If its own model is over the line, it needs: a **red-teaming program**, a **risk management process**, an **incident reporting process**, and **security controls**.
- Even if it's under the line, these are **good practice**, and customers and partners increasingly expect them.

**Say it in an interview:**
> "Article 55 adds four duties for systemic-risk models: adversarial testing, EU-level risk assessment and mitigation, serious-incident reporting to the AI Office, and cybersecurity for the model and its infrastructure."

---

## Article 99: Fines (general)

**In one line:** the **maximum fines** for breaking the AI Act, set by **each EU country**.
**Applies since:** Aug 2, 2025.

### The 3 levels (whichever is higher)
| What went wrong | Max fine |
|---|---|
| Using a **banned AI practice** (Article 5) | **€35 million or 7%** of yearly worldwide sales |
| Breaking **most other rules** (for example: high-risk duties, or **telling people they're talking to an AI**, Article 50) | **€15 million or 3%** |
| Giving **wrong or misleading information** to authorities | **€7.5 million or 1%** |

### Smaller companies
- **Startups and small companies (SMEs):** the **lower** of the two amounts, not the higher.
- **New since July 2026: small mid-sized companies ("SMCs")**, a new EU size group just above SMEs, also get the **lower** amount for the €15M and €7.5M levels.

### How the amount is decided
Authorities look at: how **serious** and how **long** the problem was, how many people were **harmed**, the company's **size**, whether it **cooperated**, whether it **reported the problem itself**, whether it was **on purpose or careless**, and what it did to **reduce the harm**.

### Who fines
**Each EU country** sets up its own fines, within these limits. **GPAI model fines are different**: see Article 101.

### What it means for a GPAI company
- The **7%** level is for **banned uses** only. Mixing this up is a common mistake.
- **Reporting problems yourself and cooperating** lowers fines, so having a clear internal process matters.

**Say it in an interview:**
> "Article 99 sets three fine levels: 7% for banned practices, 3% for most other breaches, and 1% for misleading information to authorities. National authorities impose them, and self-reporting and cooperation count in your favor."

---

## Article 101: Fines for GPAI companies

**In one line:** the fines the **EU Commission itself** can give **GPAI model makers**.
**Applies since:** **Aug 2, 2026**, a year after the GPAI rules started. That gap gave companies time to get ready.
**Length of the real text:** short ([read it](https://artificialintelligenceact.eu/article/101/)).

### The fine
Up to **€15 million or 3%** of yearly worldwide sales, **whichever is higher**.

### What it can be for (on purpose or by carelessness)
1. **Breaking the GPAI rules** (like Articles 53 and 55).
2. **Not handing over documents or information** when asked, or giving **wrong or misleading** information.
3. **Not following measures the Commission ordered.**
4. **Not giving the Commission access to the model** so it can test it.

### The company's protections
- Before fining, the Commission must **share its findings** and give the company a **chance to respond**.
- The **EU Court of Justice** can review the fine and **cancel, lower or raise** it.
- The Commission considers **commitments the company made**, including in the **Code of Practice**.
- The detailed procedure is set in a separate rule. Our tracker found **Implementing Regulation (EU) 2026/1755** (July 20, 2026) on how the Commission runs these cases.

### What it means for a GPAI company
- **This is the fine that applies to GPAI model makers**, and it's been usable since **Aug 2, 2026**.
- The Commission is **one central enforcer** for all GPAI models, not 27 different countries.
- Following the Code of Practice **helps** if there's ever a case.

**Say it in an interview:**
> "Article 101 lets the Commission fine GPAI providers directly, up to 3% or €15 million, since August 2026. It covers breaking the GPAI rules, failing to provide information, ignoring Commission measures, or refusing model access for evaluation, and the company has a right to be heard first."

---

## Check yourself (optional)

If you can answer these without looking, you're ready:

1. What are the **4 duties** every GPAI company has?
2. What's the **computing number** that makes a model "systemic risk"? Which article?
3. What are the **4 extra duties** for systemic-risk models?
4. What's the max fine for a **GPAI company**? Since when, and **who** gives it?
5. When is the **7%** fine used?
6. What **new ban** starts on **Dec 2, 2026**, and when is the **company** (not just the user) responsible?

## Where to find the real text
- **Easy to read:** [artificialintelligenceact.eu](https://artificialintelligenceact.eu/ai-act-explorer/) (one article per page). It may not show the July 2026 changes yet.
- **Official:** [the AI Act on EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- **The July 2026 changes:** [the Digital Omnibus on EUR-Lex](https://eur-lex.europa.eu/eli/reg/2026/1744/oj)
