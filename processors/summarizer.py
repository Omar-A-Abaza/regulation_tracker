"""AI summaries of documents, written by Claude Sonnet 5.5.

Each document is summarized once and saved. It's only redone if its text changes.
Money safety: an estimate before running, a size cap per document, and a spending cap per run.
"""
import json
import os
from dataclasses import dataclass
from datetime import date

from database.models import Document, utcnow
from processors.classifier import FALLBACK as FALLBACK_CATEGORY
from scrapers.page_watcher import fingerprint

MODEL = "claude-sonnet-5-5"
# Bump when the instructions change, so each summary records which version wrote it.
PROMPT_VERSION = 2
PRICE_PER_MILLION = {"input": 2.00, "output": 10.00}  # USD, Claude Sonnet 5.5
MAX_INPUT_TOKENS = 40_000  # bigger documents are whole laws; skipped unless asked for
DEFAULT_BUDGET_USD = 1.50
# Output (summary + the model's thinking) per document, used for estimates until we have real numbers.
DEFAULT_OUTPUT_TOKENS = 1_200

RISK_LEVELS = ["Action Required", "Watch", "Informational"]
CATEGORIES = ["gpai", "high_risk", "prohibited", "penalties", "transparency", "governance"]

SYSTEM_PROMPT = """You summarize AI laws, regulations and guidance for a compliance team at a company \
that builds and offers general-purpose AI models. The readers are compliance professionals, not lawyers \
or engineers.

Write in plain English with short sentences. Only use what the document says. If the document doesn't \
say something, leave that field empty rather than guessing.

Fields:
- tldr: exactly 3 bullets, each one sentence of at most 25 words. What the document is and what it does.
- who_is_affected: who has to care (for example "providers of general-purpose AI models", "deployers of \
high-risk AI systems", "US federal agencies"). One short sentence.
- key_deadline_date: the most important date in the document that a company must act by, as YYYY-MM-DD. \
Empty if there is none.
- key_deadline: what happens on that date, in one short sentence. Empty if there is none.
- actions_required: up to 3 concrete steps an AI company should take because of this document. \
Empty list if none.
- risk_level, for an AI company:
  - "Action Required": creates or changes binding obligations, or sets a deadline for them, that apply \
broadly to companies that build or offer AI models or AI products. For example: laws, regulations, \
official guidance on how a law applies, required templates, or a formal consultation on such rules. \
NOT for: agreements or contracts with one agency, calls for partners or proposals, grants or funding, \
webinars or events, research, or comment periods on a single project. Rate those "Watch" or \
"Informational", even if they have a deadline.
  - "Watch": could lead to obligations for AI companies later (proposals, drafts, voluntary frameworks \
and guidance, reviews of rules, enforcement against other companies), or a comment period or call for \
input an AI company may want to join.
  - "Informational": background, research, funding, events, partnerships, or corrections with no \
practical effect.
- categories: every one that fits: "gpai" (general-purpose AI models), "high_risk" (high-risk AI systems), \
"prohibited" (banned AI practices), "penalties" (fines and enforcement), "transparency" (telling people \
about AI, labeling AI content), "governance" (frameworks, standards, oversight bodies, policy). \
Empty list if none fit."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "tldr": {"type": "array", "items": {"type": "string"}},
        "who_is_affected": {"type": "string"},
        "key_deadline_date": {"type": "string"},
        "key_deadline": {"type": "string"},
        "actions_required": {"type": "array", "items": {"type": "string"}},
        "risk_level": {"type": "string", "enum": RISK_LEVELS},
        "categories": {"type": "array", "items": {"type": "string", "enum": CATEGORIES}},
    },
    "required": ["tldr", "who_is_affected", "key_deadline_date", "key_deadline",
                 "actions_required", "risk_level", "categories"],
    "additionalProperties": False,
}


class SummaryError(Exception):
    """The model didn't return a usable summary. Nothing is saved."""


@dataclass
class Plan:
    """What a summarize run would do, before spending anything."""
    docs: list[Document]
    tokens: dict[int, int]  # document id -> input tokens
    too_large: list[Document]
    exact: bool  # True: counted by the API. False: rough estimate (no key)

    def estimated_cost(self, output_tokens: int = DEFAULT_OUTPUT_TOKENS) -> float:
        return sum(cost(self.tokens[d.id], output_tokens) for d in self.docs)


def cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * PRICE_PER_MILLION["input"] + output_tokens * PRICE_PER_MILLION["output"]) / 1_000_000


def budget_from_env() -> float:
    try:
        return float(os.getenv("SUMMARY_BUDGET_USD") or DEFAULT_BUDGET_USD)
    except ValueError:
        return DEFAULT_BUDGET_USD


def build_input(doc: Document, today: date) -> str:
    """The message we send: facts about the document, then its text (or a note that we only have the description)."""
    published = doc.date_published.isoformat() if doc.date_published else "unknown"
    head = (f"Today's date: {today.isoformat()}\nTitle: {doc.title}\nSource: {doc.source}\n"
            f"Published: {published}\nLink: {doc.url}\nShort description: {doc.note or 'none'}\n\n")
    if doc.raw_text:
        return head + f"<document>\n{doc.raw_text}\n</document>"
    return head + ("The full text isn't available. Summarize from the title and description only, "
                   "and keep the summary short.")


def needs_summary(doc: Document) -> bool:
    """No summary yet, or the text changed since the last one."""
    if not doc.summary_json:
        return True
    return doc.summary_json.get("_meta", {}).get("input_hash") != fingerprint(_stable_input(doc))


def _stable_input(doc: Document) -> str:
    # The input without today's date, so a new day doesn't count as "changed".
    return build_input(doc, date.min)


def average_output_tokens(docs: list[Document]) -> int:
    """Real average from past summaries once there are a few; the default before that."""
    used = [d.summary_json["_meta"]["output_tokens"] for d in docs
            if d.summary_json and "_meta" in d.summary_json]
    return round(sum(used) / len(used)) if len(used) >= 3 else DEFAULT_OUTPUT_TOKENS


class Summarizer:
    def __init__(self, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client

    def count_tokens(self, doc: Document, today: date) -> int:
        return self.client.messages.count_tokens(
            model=MODEL,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_input(doc, today)}],
            output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        ).input_tokens

    def summarize(self, doc: Document, today: date) -> dict:
        """Ask the model for a summary. Returns the summary plus a "_meta" record of what it cost."""
        response = self.client.beta.messages.create(
            model=MODEL,
            max_tokens=16_000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_input(doc, today)}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            # If the model declines, the API retries on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise SummaryError("the model declined to summarize this document")
        if response.stop_reason == "max_tokens":
            raise SummaryError("the summary was cut off (hit the length limit)")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise SummaryError("the model returned no text")
        summary = validate(json.loads(text))
        usage = response.usage
        summary["_meta"] = {
            "model": response.model,
            "prompt_version": PROMPT_VERSION,
            "summarized_at": utcnow().isoformat(timespec="seconds"),
            "based_on": "full_text" if doc.raw_text else "description_only",
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": round(cost(usage.input_tokens, usage.output_tokens), 5),
            "input_hash": fingerprint(_stable_input(doc)),
        }
        return summary


def validate(data: dict) -> dict:
    """Check the answer has the shape we asked for, and tidy it."""
    if data.get("risk_level") not in RISK_LEVELS:
        raise SummaryError(f"unknown risk level: {data.get('risk_level')!r}")
    tldr = [str(b).strip() for b in data.get("tldr", []) if str(b).strip()]
    if not tldr:
        raise SummaryError("the summary has no bullets")
    return {
        "tldr": tldr[:3],
        "who_is_affected": str(data.get("who_is_affected", "")).strip(),
        "key_deadline_date": str(data.get("key_deadline_date", "")).strip(),
        "key_deadline": str(data.get("key_deadline", "")).strip(),
        "actions_required": [str(a).strip() for a in data.get("actions_required", []) if str(a).strip()][:3],
        "risk_level": data["risk_level"],
        "categories": [c for c in dict.fromkeys(data.get("categories", [])) if c in CATEGORIES],
    }


def apply_summary(doc: Document, summary: dict) -> None:
    doc.summary_json = summary
    doc.risk_level = summary["risk_level"]
    # The model's tags are better than keyword matching; keep the old ones if it found none.
    doc.categories = summary["categories"] or doc.categories or [FALLBACK_CATEGORY]
