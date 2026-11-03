"""Describe what changed between two versions of a page, in plain words."""
import difflib

MAX_QUOTE = 160


def changed_lines(old: str, new: str) -> tuple[list[str], list[str]]:
    """Lines that were added and removed (pages are stored one line per text block)."""
    added, removed = [], []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ "):
            added.append(line[2:])
        elif line.startswith("- "):
            removed.append(line[2:])
    return added, removed


def summarize_change(old: str, new: str) -> str:
    """One short note, e.g. 'New text: "…". Removed: "…".'"""
    added, removed = changed_lines(old, new)
    parts = []
    if added:
        parts.append(f"New text: {_quote(added)}")
    if removed:
        parts.append(f"Removed: {_quote(removed)}")
    return " ".join(parts) or "The page layout changed, but no text was added or removed."


def _quote(lines: list[str]) -> str:
    text = " … ".join(lines)
    if len(text) > MAX_QUOTE:
        text = text[: MAX_QUOTE - 1].rstrip() + "…"
    more = f" (+{len(lines) - 1} more)" if len(lines) > 1 else ""
    return f"“{text}”{more}."
