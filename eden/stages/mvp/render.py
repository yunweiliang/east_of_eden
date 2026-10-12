"""MVP renderers: a linear timeline. The same events.json always produces the same files."""

from __future__ import annotations

import html
from pathlib import Path

from ...core.html import cell, check_summary, mermaid_label, node_id, verified_mark, wrapped
from .schema import Event

WIDTH_PER_EVENT = 190
HEIGHT = 330
AXIS_Y = 165
MARGIN = 80


def to_mermaid(events: list[Event]) -> str:
    lines = ["```mermaid", "flowchart LR"]
    for e in events:
        lines.append(f'    {node_id(e.id)}["{mermaid_label(e)}"]')
    for a, b in zip(events, events[1:]):
        lines.append(f"    {node_id(a.id)} --> {node_id(b.id)}")
    focal = next((e for e in events if e.is_focal_event), None)
    if focal:
        lines.append(f"    style {node_id(focal.id)} stroke-width:3px")
    lines.append("```")
    return "\n".join(lines)


def source_note(meta: dict) -> str:
    return "Picked from the model's knowledge of the novel, not the text; each event needs the reader's check"


def to_markdown(events: list[Event], meta: dict) -> str:
    out = [
        "# MVP: 10 linear events leading to Cal's reveal",
        "",
        f"{source_note(meta)}. Prompt `{meta.get('prompt_hash', '?')}`. {check_summary(events)}. "
        "Open `timeline.html` for the drawn plot line.",
        "",
        to_mermaid(events),
        "",
        "| # | Event | Ch. | Characters | Search phrase | Why it matters | Checked |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(events, 1):
        cells = [str(i), f"**{e.title}**", str(e.chapter), ", ".join(e.characters), f"“{e.citation}”", e.rationale, verified_mark(e)]
        out.append("| " + " | ".join(cell(c) for c in cells) + " |")
    return "\n".join(out) + "\n"


def to_svg(events: list[Event]) -> str:
    width = MARGIN * 2 + WIDTH_PER_EVENT * (len(events) - 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {HEIGHT}" width="{width}" height="{HEIGHT}" role="img" '
        f'aria-label="Linear plot line of {len(events)} events">',
        f'<line x1="{MARGIN}" y1="{AXIS_Y}" x2="{width - MARGIN}" y2="{AXIS_Y}" class="axis"/>',
    ]
    for i, e in enumerate(events):
        x = MARGIN + i * WIDTH_PER_EVENT
        above = i % 2 == 0
        stem_end = AXIS_Y - 40 if above else AXIS_Y + 40
        cls = "node focal" if e.is_focal_event else "node"
        block = wrapped(e.title, 24) + [f"Ch. {e.chapter}"]
        y0 = stem_end - 8 - 18 * (len(block) - 1) if above else stem_end + 22
        parts.append(f"<g><title>{html.escape(e.title)}: {html.escape(e.summary)}</title>")
        parts.append(f'<line x1="{x}" y1="{AXIS_Y}" x2="{x}" y2="{stem_end}" class="stem"/>')
        parts.append(f'<circle cx="{x}" cy="{AXIS_Y}" r="{11 if e.is_focal_event else 8}" class="{cls}"/>')
        for j, line in enumerate(block):
            klass = "chap" if j == len(block) - 1 else "title"
            parts.append(f'<text x="{x}" y="{y0 + 18 * j}" class="{klass}">{html.escape(line)}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


TABLE_HEAD = ("<thead><tr><th>#</th><th>Event</th><th>Ch.</th><th>Characters</th><th>Search phrase</th>"
              "<th>Why it matters</th><th>Checked</th></tr></thead>")


def table_rows(events: list[Event]) -> str:
    return "\n".join(
        f"<tr><td>{i}</td><td><strong>{html.escape(e.title)}</strong><br>{html.escape(e.summary)}</td>"
        f"<td>{e.chapter}</td><td>{html.escape(', '.join(e.characters))}</td>"
        f"<td>“{html.escape(e.citation)}”</td><td>{html.escape(e.rationale)}</td>"
        f"<td>{verified_mark(e)}</td></tr>"
        for i, e in enumerate(events, 1)
    )


def to_html(events: list[Event], meta: dict) -> str:
    rows = table_rows(events)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>East of Eden plot line</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1f1d1a; --muted:#6b665e; --line:#b9b2a6; --node:#3d6b8c; --focal:#a3402a; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#16150f; --fg:#ece8df; --muted:#a39d91; --line:#5a554c; --node:#7fb0d1; --focal:#e0806a; }}
}}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font:15px/1.5 Georgia, 'Times New Roman', serif; }}
main {{ max-width:1200px; margin:0 auto; }}
h1 {{ font-size:1.6rem; margin:0 0 4px; overflow-wrap:anywhere; }}
p.meta {{ color:var(--muted); margin:0 0 20px; font-size:.9rem; }}
.scroll {{ overflow-x:auto; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }}
svg {{ display:block; }}
.table-wrap {{ overflow-x:auto; }}
td:nth-child(2) {{ min-width:220px; }}
.axis, .stem {{ stroke:var(--line); stroke-width:2; }}
.node {{ fill:var(--node); }}
.node.focal {{ fill:var(--focal); }}
text {{ fill:var(--fg); text-anchor:middle; font-family:Georgia, serif; font-size:14px; }}
text.chap {{ fill:var(--muted); font-size:12px; font-style:italic; }}
table {{ border-collapse:collapse; width:100%; margin-top:24px; font-size:.92rem; }}
th, td {{ text-align:left; vertical-align:top; padding:8px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:normal; }}
</style>
</head>
<body>
<main>
<h1>East of Eden: the road to Cal's reveal</h1>
<p class="meta">{len(events)} linear events. {html.escape(source_note(meta))}.
Prompt {html.escape(meta.get('prompt_hash', '?'))}. Hover a node for its summary.</p>
<div class="scroll">
{to_svg(events)}
</div>
<div class="table-wrap">
<table>
{TABLE_HEAD}
<tbody>
{rows}
</tbody>
</table>
</div>
</main>
</body>
</html>
"""


def to_portfolio_timeline(events: list[Event]) -> str:
    """The same plot line and table as timeline.html, restyled with the portfolio site's CSS variables so
    it follows the site's light and dark themes. It breaks out of the narrow text column to the page width,
    and scrolls sideways on small screens."""
    checked = sum(e.user_verified is True for e in events)
    return "\n".join([
        '<figure class="eoe-timeline">',
        "  <style>",
        "    .eoe-timeline { position: relative; left: 50%; transform: translateX(-50%);",
        "      width: min(72rem, calc(100vw - 2rem)); margin: 2.5rem 0; }",
        "    .eoe-timeline .eoe-scroll { overflow-x: auto; border-top: 1px solid var(--faint);",
        "      border-bottom: 1px solid var(--faint); }",
        "    .eoe-timeline svg { display: block; }",
        "    .eoe-timeline .axis, .eoe-timeline .stem { stroke: var(--faint); stroke-width: 2; }",
        "    .eoe-timeline .node { fill: var(--muted); }",
        "    .eoe-timeline .node.focal { fill: var(--accent); }",
        "    .eoe-timeline text { fill: var(--text); text-anchor: middle; font-family: var(--serif); font-size: 14px; }",
        "    .eoe-timeline text.chap { fill: var(--muted); font-family: var(--sans); font-size: 11px; }",
        "    .eoe-timeline .eoe-table { overflow-x: auto; margin-top: 1.5rem; }",
        "    .eoe-timeline table { border-collapse: collapse; width: 100%; font-size: 0.9rem; line-height: 1.5; }",
        "    .eoe-timeline th, .eoe-timeline td { text-align: left; vertical-align: top; padding: 0.6rem 0.5rem;",
        "      border-bottom: 1px solid var(--faint); }",
        "    .eoe-timeline th { font-family: var(--sans); font-size: 0.75rem; font-weight: 600;",
        "      letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }",
        "    .eoe-timeline td:nth-child(2) { min-width: 16rem; }",
        "    .eoe-timeline td:nth-child(6) { min-width: 14rem; }",
        "    .eoe-timeline figcaption { margin-top: 0.75rem; font-family: var(--sans); font-size: 0.8125rem;",
        "      color: var(--muted); }",
        "  </style>",
        '  <div class="eoe-scroll">',
        to_svg(events),
        "  </div>",
        '  <div class="eoe-table">',
        f"  <table>{TABLE_HEAD}<tbody>",
        table_rows(events),
        "  </tbody></table>",
        "  </div>",
        f"  <figcaption>{len(events)} events picked by the agent from its knowledge of the novel; "
        f"{checked} of {len(events)} checked against the book by me. Hover a point for its summary.</figcaption>",
        "</figure>",
    ])


def render(events: list[Event], meta: dict, out_dir: Path) -> list[Path]:
    """Write every MVP output file and return their paths."""
    files = {"timeline.md": to_markdown(events, meta), "timeline.html": to_html(events, meta)}
    for name, text in files.items():
        (out_dir / name).write_text(text)
    return [out_dir / name for name in files]
