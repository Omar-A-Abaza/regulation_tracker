"""Simple tagging by word matching. Week 2 replaces this with the AI model."""
import re

# Each category is tagged if any of its patterns appear in the text.
CATEGORY_PATTERNS = {
    # Not "super intelligence": since 2026 the US uses it to mean AI in general.
    # CAISI / AISI test frontier models, so their work counts as GPAI.
    "gpai": [r"general[- ]purpose", r"\bgpai\b", r"foundation model", r"frontier (ai|model)", r"\bcopyright", r"\bc?aisi\b"],
    "prohibited": [r"\bprohibit", r"\bbanned\b", r"\barticle 5\b"],
    "high_risk": [r"high[- ]risk", r"\bannex iii\b"],
    "penalties": [r"\bpenalt", r"\bfines?\b", r"\bproceedings\b", r"\benforcement\b", r"\bsanction", r"consent order"],
    "transparency": [r"\btransparen", r"\bwatermark", r"synthetic (content|audio|image|video|text)", r"deep ?fake", r"\barticle 50\b"],
    "governance": [r"scientific panel", r"\bai office\b", r"\bai board\b", r"\bgovernance\b", r"\bsandbox", r"risk management framework",
                   r"\bstandards?\b", r"policy statement", r"\bframework\b", r"action plan", r"\bguidelines?\b",
                   r"request for information", r"\brfi\b", r"consortium"],
}

FALLBACK = "other"


def classify(text: str) -> list[str]:
    """Return the matching categories, or ["other"] if none match."""
    text = text.lower()
    found = [cat for cat, patterns in CATEGORY_PATTERNS.items() if any(re.search(p, text) for p in patterns)]
    return found or [FALLBACK]
