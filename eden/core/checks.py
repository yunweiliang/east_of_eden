"""Deterministic checks every stage shares. Errors trigger a repair turn; warnings are only reported.

A stage's own validate() calls common_checks() and then adds checks that only make sense for that stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_QUOTE_WORDS = 15
BOOK_CHAPTERS = 55  # East of Eden has 55 chapters across four parts


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def common_checks(events: list, expected_count: int) -> Report:
    """Checks that need no book text. Whether each event really happens is checked by the user."""
    r = Report()
    if len(events) != expected_count:
        r.errors.append(f"Expected exactly {expected_count} events, got {len(events)}.")

    ids = [e.id for e in events]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        r.errors.append(f"Duplicate event ids: {', '.join(dupes)}.")

    focal = [e.id for e in events if e.is_focal_event]
    if not events or not events[-1].is_focal_event or len(focal) != 1:
        r.errors.append("Exactly one event, the last one, must have is_focal_event=true (Cal reveals Kate to Aron).")

    for e in events:
        words = len(e.citation.split())
        if words > MAX_QUOTE_WORDS:
            r.errors.append(f"[{e.id}] Search phrase is {words} words; keep it under {MAX_QUOTE_WORDS}.")
        if not 1 <= e.chapter <= BOOK_CHAPTERS:
            r.errors.append(f"[{e.id}] Chapter {e.chapter} is outside 1-{BOOK_CHAPTERS}.")
    return r
