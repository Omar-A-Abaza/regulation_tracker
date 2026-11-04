"""Charts for the dashboard (no page code here, so they're easy to test)."""
from datetime import date

import altair as alt
import pandas as pd

from dashboard import data

# Status colors (from the charting guide's fixed status palette) and a neutral gray for "later".
# They read the same in light and dark mode. Each state also has its own shape and label,
# so color is never the only clue.
STATE_COLORS = {"done": "#0ca30c", "soon": "#fab219", "later": "#898781"}
STATE_SHAPES = {"done": "circle", "soon": "diamond", "later": "square"}
MOVED_COLOR = "#898781"
TODAY_COLORS = {"light": "#5d6475", "dark": "#b4b9c6"}
SURFACES = {"light": "#ffffff", "dark": "#0e1117"}  # Streamlit's page background, for the ring around dots
ROW_HEIGHT = 70
LANE_GAP = 18  # each moved deadline gets its own lane this many pixels below its row


def _point_rows(milestones: list[dict], today: date) -> pd.DataFrame:
    return pd.DataFrame([{
        "Date": pd.Timestamp(m["date"]),
        "Where": data.JURISDICTIONS.get(m["jurisdiction"], m["jurisdiction"]),
        "Status": data.MILESTONE_STATES[data.milestone_state(m, today)],
        "Deadline": m["title"],
        "When": f"{data.nice_date(m['date'])} ({data.days_label(m['date'], today)})",
    } for m in milestones])


def timeline_chart(milestones: list[dict], today: date, theme: str = "light") -> alt.LayerChart:
    """One row per place, a dot per deadline, and a "Today" line. A deadline that moved sits in
    its own lane under its row, with a dashed line back to a hollow dot at its old date."""
    places = [p for p in data.JURISDICTIONS.values()
              if p in {data.JURISDICTIONS.get(m["jurisdiction"], m["jurisdiction"]) for m in milestones}]
    state_labels = [data.MILESTONE_STATES[s] for s in data.MILESTONE_STATES]
    x = alt.X("Date:T", title=None, axis=alt.Axis(format="%b %Y", grid=False, labelAngle=0))
    y = alt.Y("Where:N", title=None, sort=places, axis=alt.Axis(labelFontSize=13, ticks=False, domain=False))
    ring = SURFACES.get(theme, SURFACES["light"])
    today_color = TODAY_COLORS.get(theme, TODAY_COLORS["light"])

    def dots(rows: pd.DataFrame, y_offset: int = 0) -> alt.Chart:
        return alt.Chart(rows).mark_point(size=170, filled=True, opacity=1, strokeWidth=2, stroke=ring,
                                          yOffset=y_offset).encode(
            x=x, y=y,
            color=alt.Color("Status:N", scale=alt.Scale(domain=state_labels, range=list(STATE_COLORS.values())),
                            legend=alt.Legend(orient="top", title=None, labelFontSize=13)),
            shape=alt.Shape("Status:N", scale=alt.Scale(domain=state_labels, range=list(STATE_SHAPES.values()))),
            tooltip=["Deadline", "When", "Where", "Status"],
        )

    today_df = pd.DataFrame({"Date": [pd.Timestamp(today)], "label": ["Today"]})
    layers = [
        alt.Chart(today_df).mark_rule(strokeWidth=2, color=today_color).encode(x="Date:T"),
        alt.Chart(today_df).mark_text(align="left", dx=5, dy=-6, fontSize=12, fontWeight="bold", color=today_color)
        .encode(x="Date:T", y=alt.value(0), text="label"),
    ]

    moved = data.moved_milestones(milestones)
    lanes: dict[str, int] = {}
    for m in moved:
        where = data.JURISDICTIONS.get(m["jurisdiction"], m["jurisdiction"])
        lanes[where] = lanes.get(where, 0) + 1
        offset = LANE_GAP * lanes[where]
        move = pd.DataFrame([{
            "From": pd.Timestamp(m["original_date"]), "To": pd.Timestamp(m["date"]), "Where": where,
            "Deadline": m["title"], "Original date": data.nice_date(m["original_date"]),
            "Moved by": m.get("changed_by", ""),
        }])
        layers += [
            alt.Chart(move).mark_rule(strokeDash=[4, 3], strokeWidth=2, color=MOVED_COLOR, yOffset=offset)
            .encode(x="From:T", x2="To:T", y=y),
            alt.Chart(move).mark_point(size=110, filled=False, strokeWidth=2, color=MOVED_COLOR, yOffset=offset)
            .encode(x="From:T", y=y, tooltip=["Deadline", "Original date", "Moved by"]),
            dots(_point_rows([m], today), offset),
        ]

    unmoved = [m for m in milestones if m not in moved]
    if unmoved:
        layers.append(dots(_point_rows(unmoved, today)))
    return alt.layer(*layers).properties(height=ROW_HEIGHT * len(places) + LANE_GAP * max(lanes.values(), default=0) + 50)
