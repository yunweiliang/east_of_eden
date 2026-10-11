"""Deterministic renderers: the same events.json always produces the same timeline files."""

from __future__ import annotations

import html
import re
import textwrap

from .schema import Event

WIDTH_PER_EVENT = 190
HEIGHT = 330
AXIS_Y = 165
MARGIN = 80


def node_id(event_id: str) -> str:
    """Mermaid-safe node id: model ids may contain quotes or dots, or be a keyword like 'end'."""
    return "n_" + re.sub(r"\W", "_", event_id)


def cell(text: str) -> str:
    return re.sub(r"\s*\n\s*", " ", text).replace("|", "\\|")


def to_mermaid(events: list[Event]) -> str:
    lines = ["```mermaid", "flowchart LR"]
    for e in events:
        label = f"{html.escape(e.title, quote=False)}<br/><i>Ch. {e.chapter}</i>".replace('"', "#quot;")
        lines.append(f'    {node_id(e.id)}["{label}"]')
    for a, b in zip(events, events[1:]):
        lines.append(f"    {node_id(a.id)} --> {node_id(b.id)}")
    focal = next((e for e in events if e.is_focal_event), None)
    if focal:
        lines.append(f"    style {node_id(focal.id)} stroke-width:3px")
    lines.append("```")
    return "\n".join(lines)


def source_note(meta: dict) -> str:
    return "Picked from the model's knowledge of the novel, not the text; each event needs the reader's check"


def verified_mark(e: Event) -> str:
    return {True: "✓ checked", False: "✗ wrong"}.get(e.user_verified, "unchecked")


def to_markdown(events: list[Event], meta: dict) -> str:
    done = sum(e.user_verified is True for e in events)
    out = [
        "# MVP: 10 linear events leading to Cal's reveal",
        "",
        f"{source_note(meta)}. Prompt `{meta.get('prompt_hash', '?')}`. {done}/{len(events)} events checked by the "
        "reader. Open `timeline.html` for the drawn plot line.",
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


def _wrapped(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width) or [""]


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
        block = _wrapped(e.title, 24) + [f"Ch. {e.chapter}"]
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


def to_html(events: list[Event], meta: dict) -> str:
    rows = "\n".join(
        f"<tr><td>{i}</td><td><strong>{html.escape(e.title)}</strong><br>{html.escape(e.summary)}</td>"
        f"<td>{e.chapter}</td><td>{html.escape(', '.join(e.characters))}</td>"
        f"<td>“{html.escape(e.citation)}”</td><td>{html.escape(e.rationale)}</td>"
        f"<td>{verified_mark(e)}</td></tr>"
        for i, e in enumerate(events, 1)
    )
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
<thead><tr><th>#</th><th>Event</th><th>Ch.</th><th>Characters</th><th>Search phrase</th><th>Why it matters</th><th>Checked</th></tr></thead>
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
    """A vertical timeline fragment for the portfolio site. It uses the site's own CSS variables, so it
    follows the site's light and dark themes and fits its narrow text column on a phone."""
    items = []
    for i, e in enumerate(events, 1):
        cls = ' class="eoe-focal"' if e.is_focal_event else ""
        items.append(
            f"    <li{cls}>\n"
            f'      <p class="eoe-title"><span class="eoe-num">{i}</span>{html.escape(e.title)}</p>\n'
            f'      <p class="eoe-meta">Chapter {e.chapter} · {html.escape(", ".join(e.characters))}</p>\n'
            f'      <p class="eoe-summary">{html.escape(e.summary)}</p>\n'
            "    </li>"
        )
    checked = sum(e.user_verified is True for e in events)
    return "\n".join([
        '<figure class="eoe-timeline">',
        "  <style>",
        "    .eoe-timeline { margin: 2rem 0; }",
        "    .eoe-timeline ol { list-style: none; margin: 0; padding: 0 0 0 1.5rem; border-left: 2px solid var(--faint); }",
        "    .eoe-timeline li { position: relative; margin: 0 0 1.5rem; }",
        "    .eoe-timeline li::before { content: ''; position: absolute; left: calc(-1.5rem - 6px); top: 0.45rem;",
        "      width: 10px; height: 10px; border-radius: 50%; background: var(--muted); }",
        "    .eoe-timeline li.eoe-focal::before { width: 14px; height: 14px; left: calc(-1.5rem - 8px); background: var(--accent); }",
        "    .eoe-timeline p { margin: 0; }",
        "    .eoe-title { font-size: 1.1rem; line-height: 1.4; }",
        "    .eoe-focal .eoe-title { color: var(--accent); }",
        "    .eoe-num { font-family: var(--sans); font-size: 0.75rem; color: var(--muted); margin-right: 0.5rem; }",
        "    .eoe-meta { font-family: var(--sans); font-size: 0.8125rem; color: var(--muted); margin-top: 0.15rem; }",
        "    .eoe-summary { font-size: 0.95rem; line-height: 1.55; margin-top: 0.35rem; }",
        "    .eoe-timeline figcaption { font-family: var(--sans); font-size: 0.8125rem; color: var(--muted); }",
        "  </style>",
        "  <ol>",
        *items,
        "  </ol>",
        f"  <figcaption>{len(events)} events picked by the agent from its knowledge of the novel; "
        f"{checked} of {len(events)} checked against the book by me.</figcaption>",
        "</figure>",
    ])


TIMELINE_START = "<!-- eden:timeline:start -->"
TIMELINE_END = "<!-- eden:timeline:end -->"


def splice_timeline(page: str, fragment: str) -> str:
    """Replace only the text between the timeline markers, so hand-written text around it is kept."""
    start, end = page.index(TIMELINE_START) + len(TIMELINE_START), page.index(TIMELINE_END)
    return page[:start] + "\n" + fragment + "\n" + page[end:]
