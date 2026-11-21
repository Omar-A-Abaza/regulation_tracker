"""The fuse board: every deadline is a bomb with a lit fuse.

This file turns timeline milestones and documents into one list of items (plain data, no
Streamlit, so it's easy to test) and fills in the HTML template in static/fuse.html.
"""
import json
import math
from datetime import date, datetime
from pathlib import Path

from dashboard import data

TEMPLATE = Path(__file__).resolve().parent / "static" / "fuse.html"

# Fuse length = time left, on a log scale capped at about 3 years, so a deadline 2 weeks
# out and one 2 years out both get a readable fuse.
MAX_DAYS = 3 * 365
RED_DAYS = 30
ORANGE_DAYS = 90
URGENCY_LABELS = {"red": f"Within {RED_DAYS} days", "orange": f"Within {ORANGE_DAYS} days",
                  "later": "Later", "blown": "In force"}
# Marks along the fuse track, so the log scale can be read.
TICKS = {"1 wk": 7, "1 mo": 30, "3 mo": 90, "1 yr": 365, "3 yr": MAX_DAYS}
REGIONS = {"EU": "EU", "US": "US federal", "state": "US states"}
FRAMEWORK_REGIONS = {"eu_ai_act": "EU", "nist_ai_rmf": "US", "us_federal": "US", "us_state": "state"}
LINKED_DOCS = 4  # most documents listed on a milestone's card

# Rough pixel sizes, to size the frame before its own script measures the real height.
ROW_PX = {"full": 56, "small": 48}
MOVED_EXTRA_PX = 14
MIN_FULL_PX = 460  # room for an open card even when only a few fuses are shown


def fuse_length(days: int) -> float:
    """0 (about to blow) to 1 (3 years or more away), on a log scale."""
    if days <= 0:
        return 0.0
    return min(1.0, math.log1p(days) / math.log1p(MAX_DAYS))


def urgency(days: int) -> str:
    if days < 0:
        return "blown"
    if days <= RED_DAYS:
        return "red"
    if days <= ORANGE_DAYS:
        return "orange"
    return "later"


def months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - 1 if end.day < start.day else months


def short_law(name: str) -> str:
    return name.replace("Regulation (EU) ", "Reg. ")


def when_text(when: date, today: date) -> str:
    days = (when - today).days
    if days == 0:
        return "Today"
    if days > 0:
        return f"{days} day{'s' if days != 1 else ''} left"
    return f"{-days} day{'s' if days != -1 else ''} ago"


def _region(jurisdiction: str | None, framework: str) -> str:
    if jurisdiction:
        return "EU" if jurisdiction == "EU" else "state" if jurisdiction.startswith("US-") else "US"
    return FRAMEWORK_REGIONS.get(framework, "US")


def _base(*, item_id: str, kind: str, title: str, when: date, today: date, region: str,
          categories: list[str], url: str) -> dict:
    days = (when - today).days
    state = urgency(days)
    return {
        "id": item_id, "kind": kind, "title": title,
        "date": when.isoformat(), "date_label": data.nice_date(when),
        "days": days, "when": when_text(when, today),
        "urgency": state, "urgency_label": URGENCY_LABELS[state],
        "fuse": round(fuse_length(days), 4),
        "region": region,
        "categories": [c for c in categories if c in data.CATEGORIES and c != "other"],
        "url": url,
        "summary": [], "who": "", "actions": [], "articles": [], "ai_urgency": None,
        "moved": None, "linked": [], "blown_label": "",
    }


def _doc_bullets(doc: data.DocRow) -> list[str]:
    return list((doc.summary or {}).get("tldr") or [])


def linked_documents(milestone: dict, docs: list[data.DocRow]) -> list[dict]:
    """Documents about the same law (same framework), narrowed to the milestone's categories
    when it has any. Summarized documents first, then newest."""
    cats = set(milestone.get("categories", []))
    found = [d for d in docs if d.framework == milestone["framework"] and (not cats or cats & set(d.categories))]
    found.sort(key=lambda d: (d.summary is None, -(d.date_published or date.min).toordinal()))
    return [{
        "title": d.title, "url": d.url,
        "date_label": data.nice_date(d.date_published) if d.date_published else "",
        "bullets": _doc_bullets(d),
        "note": "" if d.summary else (d.note or ""),
    } for d in found[:LINKED_DOCS]]


def milestone_item(m: dict, docs: list[data.DocRow], today: date) -> dict:
    item = _base(item_id=f"m-{m['id']}", kind="milestone", title=m["title"], when=m["date"], today=today,
                 region=_region(m.get("jurisdiction"), m["framework"]), categories=m.get("categories", []),
                 url=m.get("source_url", ""))
    item["summary"] = [" ".join(m.get("summary", "").split())]
    item["articles"] = list(m.get("articles", []))
    item["where"] = data.JURISDICTIONS.get(m.get("jurisdiction"), m.get("jurisdiction", ""))
    if item["urgency"] == "blown":
        item["blown_label"] = f"In force since {data.nice_date(m['date'])}"
    if m.get("original_date"):
        original = m["original_date"]
        months = months_between(original, m["date"])
        label = f"Extended +{months} month{'s' if months != 1 else ''}"
        if m.get("changed_by"):
            label += f" by {short_law(m['changed_by'])}"
        item["moved"] = {
            "from": original.isoformat(), "from_label": data.nice_date(original), "label": label,
            "knot": round(fuse_length((original - today).days), 4),
        }
    item["linked"] = linked_documents(m, docs)
    return item


def document_deadline(doc: data.DocRow) -> date | None:
    raw = ((doc.summary or {}).get("key_deadline_date") or "").strip()
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def document_item(doc: data.DocRow, when: date, today: date) -> dict:
    summary = doc.summary or {}
    item = _base(item_id=f"d-{doc.id}", kind="document", title=doc.title, when=when, today=today,
                 region=_region(None, doc.framework), categories=doc.categories, url=doc.url)
    item["summary"] = _doc_bullets(doc)
    if summary.get("key_deadline"):
        item["deadline_note"] = summary["key_deadline"]
    item["who"] = summary.get("who_is_affected", "")
    item["actions"] = list(summary.get("actions_required") or [])
    item["ai_urgency"] = doc.risk_level
    item["source"] = data.source_label(doc)
    return item


def build_items(milestones: list[dict], docs: list[data.DocRow], today: date) -> list[dict]:
    """Every milestone, plus documents whose AI summary has a deadline still ahead. Soonest first."""
    items = [milestone_item(m, docs, today) for m in milestones]
    for doc in docs:
        when = document_deadline(doc)
        if when and when >= today:
            items.append(document_item(doc, when, today))
    return sorted(items, key=lambda i: (i["date"], i["kind"] != "milestone", i["title"]))


def header(docs: list[data.DocRow], health: list[data.SourceHealth], now: datetime, today: date) -> dict:
    failing = [h.label for h in health if h.status in ("failed", "partial")]
    last = max((h.last_checked for h in health), default=None)
    action = data.filter_documents(docs, today=today, days=90, risk_levels=["Action Required"])
    return {
        "updated": data.nice_date(last.date()) if last else "",
        "updated_ago": data.time_ago(last, now) if last else "",
        "new_this_week": len(data.new_this_week(docs, now)),
        "needs_action": len(action),
        "sources": len(health),
        "failing": failing,
    }


def ticks() -> list[dict]:
    return [{"label": label, "at": round(fuse_length(days), 4)} for label, days in TICKS.items()]


def frame_height(items: list[dict], mode: str = "full") -> int:
    """A first guess at the frame height; the page's script then fits it to the real content."""
    if mode == "small":
        return 40 + ROW_PX["small"] * len(items)
    upcoming = [i for i in items if i["urgency"] != "blown"]
    rows = ROW_PX["full"] * len(upcoming) + MOVED_EXTRA_PX * sum(1 for i in upcoming if i["moved"])
    return max(MIN_FULL_PX, 190 + rows)


def to_json(payload: dict) -> str:
    # Safe inside a <script> tag: "</" can't close it.
    return json.dumps(payload, ensure_ascii=True).replace("</", "<\\/")


def render(items: list[dict], *, head: dict | None = None, mode: str = "full", theme: str | None = None) -> str:
    payload = {"items": items, "header": head, "mode": mode, "ticks": ticks(),
               "regions": REGIONS, "categories": {k: v for k, v in data.CATEGORIES.items() if k != "other"}}
    html = TEMPLATE.read_text()
    html = html.replace("__THEME__", theme if theme in ("light", "dark") else "auto")
    return html.replace("/*__DATA__*/null", to_json(payload))
