"""M1 renderers: the graph of the events the judge keeps, plus every keep-or-cut reason (graph.md, graph.html).

The same pool, judge runs and reference set always produce the same files.
"""

from __future__ import annotations

import html
from pathlib import Path

from ...core.html import cell, check_summary, mermaid_label, node_id, verified_mark
from ..m0.render import STYLE, to_svg
from .graph import without
from .judge import judge_hash, judged_pool
from .runs import load_judge_runs, load_reference
from .schema import Event
from .stability import Tally, agreement, consensus, kept_sets, tally


class Summary:
    """Everything the M1 page shows, worked out once from the pool, the runs and the reference set."""

    def __init__(self, events: list[Event], out_dir: Path):
        self.pool = events
        self.judged = judged_pool(events)
        self.hash = judge_hash(self.judged)
        self.runs = load_judge_runs(out_dir, self.hash)
        self.tallies = tally([e.id for e in self.judged], self.runs)
        self.kept = consensus(self.tallies) if self.runs else {e.id for e in self.judged}
        self.kept_graph = without(self.judged, {e.id for e in self.judged} - self.kept)
        self.by_id = {e.id: e for e in events}
        self.reference = load_reference(out_dir)

    def headline(self) -> str:
        n = len(self.judged)
        if not self.runs:
            return (f"Not judged yet: {n} candidates, all shown. Run `python -m eden judge` to apply the "
                    "significance test.")
        per_run = ", ".join(str(len(s)) for s in kept_sets(self.runs))
        agree = agreement(self.runs)
        agree_text = f"; runs agree {agree:.0%} on average (shared keeps / all keeps, per pair)" if agree is not None else ""
        return (f"{len(self.runs)} judge run(s) over {n} candidates. Kept per run: {per_run}{agree_text}. "
                f"Kept by most runs: **{len(self.kept)} of {n}**, drawn below.")

    def recall_lines(self) -> list[str]:
        """How the agent's picks compare with the reader's own list, if the reader has written one."""
        ref = self.reference
        if ref is None:
            return ["No reference set yet (`output/m1/reference.json`)."]
        if not ref:
            return ["The reference set is empty: add your own picks to `output/m1/reference.json`."]
        matched = [r for r in ref if r.pool_id in self.by_id]
        kept = [r for r in matched if r.pool_id in self.kept]
        listed = {r.pool_id for r in matched}
        extra = [e for e in self.kept_graph if e.id not in listed and not e.is_focal_event]  # the reveal is always kept
        verdict = f"the judge keeps {len(kept)}" if self.runs else "the judge hasn't ruled yet"
        lines = [
            f"Your reference set has {len(ref)} events. The pool contains {len(matched)} of them "
            f"(recall {len(matched) / len(ref):.0%}), and {verdict}.",
        ]
        missing = [r for r in ref if r.pool_id not in self.by_id]
        if missing:
            lines.append("Not in the pool: " + "; ".join(f"{r.title} (ch. {r.chapter or '?'})" for r in missing) + ".")
        if not self.runs:
            return lines  # nothing is kept or cut until the judge has run
        cut = [r for r in matched if r.pool_id not in self.kept]
        if cut:
            lines.append("In the pool but cut by the judge: " + "; ".join(self.by_id[r.pool_id].title for r in cut) + ".")
        if extra:
            lines.append("Kept by the judge but not on your list: " + "; ".join(e.title for e in extra) + ".")
        return lines


def kept_mark(event: Event, t: Tally | None) -> str:
    if event.user_verified is False:
        return "not judged (marked false)"
    if t is None or not t.runs:
        return "not judged yet"
    return f"{t.kept}/{t.runs}"


def affects_titles(t: Tally | None, by_id: dict[str, Event]) -> str:
    if t is None or t.typical is None:
        return ""
    return ", ".join(by_id[a].title if a in by_id else a for a in t.typical.affects)


def to_mermaid(s: Summary) -> str:
    lines = ["```mermaid", "flowchart LR"]
    for e in s.judged:
        lines.append(f'    {node_id(e.id)}["{mermaid_label(e)}"]')
    for e in s.judged:
        for c in e.causes:
            lines.append(f"    {node_id(c)} --> {node_id(e.id)}")
    cut = [node_id(e.id) for e in s.judged if e.id not in s.kept]
    if cut:
        lines.append("    classDef cut stroke-dasharray:4 3,opacity:0.45")
        lines.append(f"    class {','.join(cut)} cut")
    focal = next((e for e in s.judged if e.is_focal_event), None)
    if focal:
        lines.append(f"    style {node_id(focal.id)} stroke-width:3px")
    lines.append("```")
    return "\n".join(lines)


def to_markdown(s: Summary, meta: dict) -> str:
    out = [
        "# M1: the events the ending really depends on",
        "",
        "Pool picked from the model's knowledge of the novel, not the text; "
        f"{check_summary(s.pool)}. Pool prompt `{meta.get('prompt_hash', '?')}`, judge input `{s.hash}`.",
        "",
        s.headline(),
        "",
        *[line + "\n" for line in s.recall_lines()],
        "The full pool; faded, dashed boxes are the events most runs cut. Open `graph.html` for the swimlanes "
        "of the kept events only.",
        "",
        to_mermaid(s),
        "",
        "| # | Event | Thread | Ch. | Kept | Effect if removed | Affects | Judge's reason | Checked |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(s.pool, 1):
        t = s.tallies.get(e.id)
        reason = t.typical.reason if t and t.typical else ""
        effect = (t.effect or "") if t else ""
        cells = [str(i), f"**{e.title}**", e.thread, str(e.chapter), kept_mark(e, t), effect,
                 affects_titles(t, s.by_id), reason, verified_mark(e)]
        out.append("| " + " | ".join(cell(c) for c in cells) + " |")
    return "\n".join(out) + "\n"


def table_rows(s: Summary) -> str:
    rows = []
    for i, e in enumerate(s.pool, 1):
        t = s.tallies.get(e.id)
        reason = t.typical.reason if t and t.typical else ""
        effect = (t.effect or "") if t else ""
        cls = "" if e.id in s.kept else ' class="cut"'
        rows.append(
            f"<tr{cls}><td>{i}</td><td><strong>{html.escape(e.title)}</strong><br>{html.escape(e.summary)}</td>"
            f"<td>{html.escape(e.thread)}</td><td>{e.chapter}</td><td>{html.escape(kept_mark(e, t))}</td>"
            f"<td>{html.escape(effect)}</td><td>{html.escape(affects_titles(t, s.by_id))}</td>"
            f"<td>{html.escape(reason)}</td><td>{verified_mark(e)}</td></tr>")
    return "\n".join(rows)


def md_inline(text: str) -> str:
    """Escape, then turn the two Markdown marks the headline uses (**bold** and `code`) into HTML."""
    out = html.escape(text)
    for mark, tag in (("**", "strong"), ("`", "code")):
        parts = out.split(mark)
        out = "".join(p if j % 2 == 0 else f"<{tag}>{p}</{tag}>" for j, p in enumerate(parts))
    return out


def to_html(s: Summary, meta: dict) -> str:
    recall = "\n".join(f"<p>{md_inline(line)}</p>" for line in s.recall_lines())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>East of Eden significant events</title>
<style>
{STYLE}tr.cut td {{ color:var(--muted); }}
tr.cut strong {{ font-weight:normal; text-decoration:line-through; }}
p.lead {{ margin:0 0 12px; }}
</style>
</head>
<body>
<main>
<h1>East of Eden: the events the ending really depends on</h1>
<p class="meta">Pool picked from the model's knowledge of the novel, not the text; {check_summary(s.pool)}.
Pool prompt {html.escape(meta.get('prompt_hash', '?'))}, judge input {s.hash}. Arrows run from cause to effect;
where the judge cut an event, its arrows are joined up so the path stays visible.</p>
<p class="lead">{md_inline(s.headline())}</p>
{recall}
<div class="scroll">
{to_svg(s.kept_graph)}
</div>
<div class="table-wrap">
<table>
<thead><tr><th>#</th><th>Event</th><th>Thread</th><th>Ch.</th><th>Kept</th><th>Effect if removed</th>
<th>Affects</th><th>Judge's reason</th><th>Checked</th></tr></thead>
<tbody>
{table_rows(s)}
</tbody>
</table>
</div>
</main>
</body>
</html>
"""


def render(events: list[Event], meta: dict, out_dir: Path) -> list[Path]:
    """Write every M1 output file and return their paths."""
    s = Summary(events, out_dir)
    files = {"graph.md": to_markdown(s, meta), "graph.html": to_html(s, meta)}
    for name, text in files.items():
        (out_dir / name).write_text(text)
    return [out_dir / name for name in files]

