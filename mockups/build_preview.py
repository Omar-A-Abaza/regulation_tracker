"""Builds dashboard_preview.html from the template and the real data files.

Run: python mockups/build_preview.py
"""
import json
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "mockups"


def to_json(rows):
    # YAML turns dates into date objects; the page wants plain "YYYY-MM-DD" strings.
    return json.dumps(rows, default=lambda v: v.isoformat() if isinstance(v, date) else str(v), indent=1)


docs = yaml.safe_load((ROOT / "data/seed_documents.yaml").read_text())["documents"]
milestones = yaml.safe_load((ROOT / "data/timeline.yaml").read_text())["milestones"]

html = (HERE / "dashboard_preview.template.html").read_text()
html = html.replace("/*SEED_DOCS*/", to_json(docs)).replace("/*TIMELINE*/", to_json(milestones))
(HERE / "dashboard_preview.html").write_text(html)
print(f"Wrote {HERE / 'dashboard_preview.html'} ({len(docs)} docs, {len(milestones)} milestones)")
