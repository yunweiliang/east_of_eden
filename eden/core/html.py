"""Small rendering helpers every stage's renderer can use. Model output is untrusted text, so escape it."""

from __future__ import annotations

import html
import re
import textwrap


def node_id(event_id: str) -> str:
    """Mermaid-safe node id: model ids may contain quotes or dots, or be a keyword like 'end'."""
    return "n_" + re.sub(r"\W", "_", event_id)


def mermaid_label(e) -> str:
    """A node label: the title plus its chapter, escaped so quotes and HTML characters can't break Mermaid."""
    return f"{html.escape(e.title, quote=False)}<br/><i>Ch. {e.chapter}</i>".replace('"', "#quot;")


def cell(text: str) -> str:
    """A Markdown table cell: newlines collapsed and pipes escaped, so model text can't break the table."""
    return re.sub(r"\s*\n\s*", " ", text).replace("|", "\\|")


def check_summary(events) -> str:
    """How many events the reader has checked, and how many of those were true: "20/20 checked, 19 true"."""
    checked = sum(e.user_verified is not None for e in events)
    true = sum(e.user_verified is True for e in events)
    return f"{checked}/{len(events)} checked by the reader" + (f", {true} true" if checked else "")


def verified_mark(e) -> str:
    return {True: "✓ checked", False: "✗ wrong"}.get(e.user_verified, "unchecked")


def wrapped(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width) or [""]
