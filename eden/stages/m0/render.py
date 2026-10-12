"""M0 renderers: a Mermaid graph (graph.md) and a swimlane drawing (graph.html).

The same events.json always produces the same files.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import get_args

from ...core.html import cell, check_summary, mermaid_label, node_id, verified_mark, wrapped
from .schema import Event, Thread

# Swimlane layout, in SVG pixels. Time runs left to right: one column per event, in story order.
# Each thread gets a horizontal lane, and an event sits in its thread's lane, in its own column.
COL = 132           # width of one event's column
LANE = 150          # height of one lane
GUTTER = 112        # left margin for the lane names
NODE_Y = 46         # node centre, measured from the top of its lane; the label sits below it
R, R_FOCAL = 8, 12  # node radii
LABEL_CHARS = 17    # wrap titles at this many characters
LABEL_LINES = 4     # and keep at most this many lines
THREADS = get_args(Thread)  # fixed lane order, so lanes don't move between runs


def to_mermaid(events: list[Event]) -> str:
    lines = ["```mermaid", "flowchart LR"]
    threads = list(dict.fromkeys(e.thread for e in events))  # in order of first appearance
    for t in threads:
        lines.append(f'    subgraph lane_{node_id(t)}["{t}"]')
        for e in events:
            if e.thread == t:
                lines.append(f'        {node_id(e.id)}["{mermaid_label(e)}"]')
        lines.append("    end")
    for e in events:
        for cause in e.causes:
            lines.append(f"    {node_id(cause)} --> {node_id(e.id)}")
    focal = next((e for e in events if e.is_focal_event), None)
    if focal:
        lines.append(f"    style {node_id(focal.id)} stroke-width:3px")
    lines.append("```")
    return "\n".join(lines)


def caused_by(e: Event, by_id: dict[str, Event]) -> str:
    return ", ".join(by_id[c].title if c in by_id else c for c in e.causes) or "(starts a thread)"


def to_markdown(events: list[Event], meta: dict) -> str:
    by_id = {e.id: e for e in events}
    out = [
        f"# M0: {len(events)} events across the story's threads, converging on Cal's reveal",
        "",
        "Picked from the model's knowledge of the novel, not the text; each event needs the reader's check. "
        f"Prompt `{meta.get('prompt_hash', '?')}`. {check_summary(events)}. "
        "Open `graph.html` for the swimlanes.",
        "",
        to_mermaid(events),
        "",
        "| # | Event | Thread | Ch. | Caused by | Search phrase | Why it matters | Checked |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(events, 1):
        cells = [str(i), f"**{e.title}**", e.thread, str(e.chapter), caused_by(e, by_id), f"“{e.citation}”",
                 e.rationale, verified_mark(e)]
        out.append("| " + " | ".join(cell(c) for c in cells) + " |")
    return "\n".join(out) + "\n"


def label(title: str) -> list[str]:
    """A node's title, wrapped, cut to LABEL_LINES lines with an ellipsis. The hover text has it in full."""
    lines = wrapped(title, LABEL_CHARS)
    if len(lines) > LABEL_LINES:
        lines = lines[:LABEL_LINES]
        lines[-1] = lines[-1][:LABEL_CHARS - 1].rstrip() + "…"
    return lines


def edge_path(x1: int, y1: int, x2: int, y2: int) -> str:
    """An SVG path from a cause to its effect.

    Across lanes: an S-curve that leaves and arrives level, so you can see one lane flow into another.
    Within a lane: next-door events get a straight line. Longer jumps arc over the events in between,
    higher for longer jumps, so they don't run through other nodes.
    """
    if y1 == y2:
        if x2 - x1 <= COL:
            return f"M{x1},{y1} L{x2},{y2}"
        peak = min(NODE_Y - 6, 14 + 4 * (x2 - x1) / COL)
        lift = peak / 0.75  # a cubic curve only reaches 3/4 of the way to its control points
        return f"M{x1},{y1} C{x1},{y1 - lift:g} {x2},{y2 - lift:g} {x2},{y2}"
    dx = (x2 - x1) / 2
    return f"M{x1},{y1} C{x1 + dx:g},{y1} {x2 - dx:g},{y2} {x2},{y2}"


def arrow_marker(name: str, radius: int, cls: str) -> str:
    # refX pushes the tip back along the curve's final direction, so it stops at the node's edge
    # whichever way the curve arrives.
    return (f'<marker id="{name}" viewBox="0 0 10 10" refX="{10 + radius + 1}" refY="5" markerWidth="9" '
            f'markerHeight="9" markerUnits="userSpaceOnUse" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" class="{cls}"/></marker>')


def to_svg(events: list[Event]) -> str:
    threads = [t for t in THREADS if any(e.thread == t for e in events)]
    lane_of = {t: i for i, t in enumerate(threads)}
    pos = {e.id: (GUTTER + COL // 2 + i * COL, lane_of[e.thread] * LANE + NODE_Y) for i, e in enumerate(events)}
    by_id = {e.id: e for e in events}
    width, height = GUTTER + COL * len(events), LANE * len(threads)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="Cause-and-effect graph of {len(events)} events in {len(threads)} story threads">',
        "<defs>", arrow_marker("arrow", R, "tip"), arrow_marker("arrow-focal", R_FOCAL, "tip focal"), "</defs>",
    ]
    for i, t in enumerate(threads):
        y = i * LANE
        parts.append(f'<rect x="0" y="{y}" width="{width}" height="{LANE}" class="lane{i % 2}"/>')
        parts.append(f'<text x="12" y="{y + NODE_Y + 5}" class="lane-name t{THREADS.index(t)}">{html.escape(t)}</text>')

    # Arrows first, so nodes and labels are drawn on top of them.
    for e in events:
        x2, y2 = pos[e.id]
        for c in e.causes:
            if c not in pos:
                continue  # the validator reports unknown causes; draw what we can
            x1, y1 = pos[c]
            cls = "edge" + (" cross" if y1 != y2 else "") + (" focal" if e.is_focal_event else "")
            marker = "arrow-focal" if e.is_focal_event else "arrow"
            parts.append(f'<path d="{edge_path(x1, y1, x2, y2)}" class="{cls}" marker-end="url(#{marker})">'
                         f"<title>{html.escape(by_id[c].title)} → {html.escape(e.title)}</title></path>")

    for e in events:
        x, y = pos[e.id]
        hover = f"{e.title} (ch. {e.chapter}): {e.summary}\nCaused by: {caused_by(e, by_id)}"
        parts.append(f"<g><title>{html.escape(hover)}</title>")
        if e.is_focal_event:
            parts.append(f'<circle cx="{x}" cy="{y}" r="{R_FOCAL}" class="node focal"/>')
        else:
            parts.append(f'<circle cx="{x}" cy="{y}" r="{R}" class="node t{THREADS.index(e.thread)}"/>')
        block = label(e.title)
        for j, line in enumerate(block):
            parts.append(f'<text x="{x}" y="{y + 30 + 16 * j}" class="title">{html.escape(line)}</text>')
        parts.append(f'<text x="{x}" y="{y + 30 + 16 * len(block)}" class="chap">Ch. {e.chapter}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


def table_rows(events: list[Event]) -> str:
    by_id = {e.id: e for e in events}
    return "\n".join(
        f"<tr><td>{i}</td><td><strong>{html.escape(e.title)}</strong><br>{html.escape(e.summary)}</td>"
        f"<td>{html.escape(e.thread)}</td><td>{e.chapter}</td><td>{html.escape(caused_by(e, by_id))}</td>"
        f"<td>“{html.escape(e.citation)}”</td><td>{html.escape(e.rationale)}</td>"
        f"<td>{verified_mark(e)}</td></tr>"
        for i, e in enumerate(events, 1)
    )


def to_html(events: list[Event], meta: dict) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>East of Eden cause graph</title>
<style>
:root {{ --bg:#fbfaf7; --lane:#f2efe8; --fg:#1f1d1a; --muted:#6b665e; --line:#b9b2a6; --edge:#8f887c;
  --focal:#a3402a; --t0:#3d6b8c; --t1:#7a4f8f; --t2:#5f7f3a; --t3:#9a6a1f; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#16150f; --lane:#1f1e18; --fg:#ece8df; --muted:#a39d91; --line:#5a554c; --edge:#8a8478;
    --focal:#e0806a; --t0:#7fb0d1; --t1:#c39bd6; --t2:#9cc274; --t3:#d9a85a; }}
}}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font:15px/1.5 Georgia, 'Times New Roman', serif; }}
main {{ max-width:1200px; margin:0 auto; }}
h1 {{ font-size:1.6rem; margin:0 0 4px; overflow-wrap:anywhere; }}
p.meta {{ color:var(--muted); margin:0 0 20px; font-size:.9rem; }}
.scroll {{ overflow-x:auto; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }}
svg {{ display:block; }}
.lane0 {{ fill:var(--bg); }}
.lane1 {{ fill:var(--lane); }}
.lane-name {{ font-size:13px; font-weight:bold; }}
.edge {{ fill:none; stroke:var(--edge); stroke-width:1.5; opacity:.8; }}
.edge.cross {{ stroke-dasharray:5 3; }}
.edge.focal {{ stroke:var(--focal); stroke-width:2; opacity:1; }}
.tip {{ fill:var(--edge); }}
.tip.focal {{ fill:var(--focal); }}
.node {{ stroke:var(--bg); stroke-width:2; }}
.node.focal {{ fill:var(--focal); }}
.t0 {{ fill:var(--t0); }} .t1 {{ fill:var(--t1); }} .t2 {{ fill:var(--t2); }} .t3 {{ fill:var(--t3); }}
text {{ font-family:Georgia, serif; }}
text.title, text.chap {{ text-anchor:middle; paint-order:stroke; stroke:var(--bg); stroke-width:4px;
  stroke-linejoin:round; }}
text.title {{ fill:var(--fg); font-size:13px; }}
text.chap {{ fill:var(--muted); font-size:11px; font-style:italic; }}
.table-wrap {{ overflow-x:auto; }}
td:nth-child(2) {{ min-width:220px; }}
table {{ border-collapse:collapse; width:100%; margin-top:24px; font-size:.92rem; }}
th, td {{ text-align:left; vertical-align:top; padding:8px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:normal; }}
</style>
</head>
<body>
<main>
<h1>East of Eden: the threads that converge on Cal's reveal</h1>
<p class="meta">{len(events)} events in story order, left to right, one lane per thread. Arrows run from cause to
effect: dashed arrows cross between threads, and red arrows feed the reveal. Picked from the model's knowledge of
the novel, not the text; {check_summary(events)}. Prompt
{html.escape(meta.get('prompt_hash', '?'))}. Hover a node or an arrow for details.</p>
<div class="scroll">
{to_svg(events)}
</div>
<div class="table-wrap">
<table>
<thead><tr><th>#</th><th>Event</th><th>Thread</th><th>Ch.</th><th>Caused by</th><th>Search phrase</th>
<th>Why it matters</th><th>Checked</th></tr></thead>
<tbody>
{table_rows(events)}
</tbody>
</table>
</div>
</main>
</body>
</html>
"""


def render(events: list[Event], meta: dict, out_dir: Path) -> list[Path]:
    """Write every M0 output file and return their paths."""
    files = {"graph.md": to_markdown(events, meta), "graph.html": to_html(events, meta)}
    for name, text in files.items():
        (out_dir / name).write_text(text)
    return [out_dir / name for name in files]
