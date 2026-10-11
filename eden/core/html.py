"""Small rendering helpers every stage's renderer can use. Model output is untrusted text, so escape it."""

from __future__ import annotations

import re
import textwrap


def node_id(event_id: str) -> str:
    """Mermaid-safe node id: model ids may contain quotes or dots, or be a keyword like 'end'."""
    return "n_" + re.sub(r"\W", "_", event_id)


def cell(text: str) -> str:
    """A Markdown table cell: newlines collapsed and pipes escaped, so model text can't break the table."""
    return re.sub(r"\s*\n\s*", " ", text).replace("|", "\\|")


def verified_mark(e) -> str:
    return {True: "✓ checked", False: "✗ wrong"}.get(e.user_verified, "unchecked")


def wrapped(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width) or [""]
