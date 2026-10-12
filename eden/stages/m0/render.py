"""M0 renderers. For now a Mermaid graph with one box per thread; the swimlane HTML comes next."""

from __future__ import annotations

from pathlib import Path

from ...core.html import cell, mermaid_label, node_id, verified_mark
from .schema import Event


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


def to_markdown(events: list[Event], meta: dict) -> str:
    done = sum(e.user_verified is True for e in events)
    by_id = {e.id: e for e in events}
    out = [
        f"# M0: {len(events)} events across the story's threads, converging on Cal's reveal",
        "",
        "Picked from the model's knowledge of the novel, not the text; each event needs the reader's check. "
        f"Prompt `{meta.get('prompt_hash', '?')}`. {done}/{len(events)} events checked by the reader.",
        "",
        to_mermaid(events),
        "",
        "| # | Event | Thread | Ch. | Caused by | Search phrase | Why it matters | Checked |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(events, 1):
        causes = ", ".join(by_id[c].title if c in by_id else c for c in e.causes) or "(starts a thread)"
        cells = [str(i), f"**{e.title}**", e.thread, str(e.chapter), causes, f"“{e.citation}”", e.rationale,
                 verified_mark(e)]
        out.append("| " + " | ".join(cell(c) for c in cells) + " |")
    return "\n".join(out) + "\n"


def render(events: list[Event], meta: dict, out_dir: Path) -> list[Path]:
    """Write every M0 output file and return their paths."""
    path = out_dir / "graph.md"
    path.write_text(to_markdown(events, meta))
    return [path]
