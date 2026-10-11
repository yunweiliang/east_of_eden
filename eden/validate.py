"""Deterministic checks on the model's event picks. Errors trigger a repair turn; warnings are reported."""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import Event
from .source import Book, normalize_for_match

MAX_QUOTE_WORDS = 40
BOOK_CHAPTERS = 55  # East of Eden has 55 chapters across four parts


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(events: list[Event], book: Book | None, expected_count: int) -> Report:
    """With book=None (memory mode) citations can't be checked; the user verifies them instead."""
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
            r.errors.append(f"[{e.id}] Citation is {words} words; keep it to one sentence, under {MAX_QUOTE_WORDS} words.")
        if book is None:
            if not 1 <= e.chapter <= BOOK_CHAPTERS:
                r.errors.append(f"[{e.id}] Chapter {e.chapter} is outside 1-{BOOK_CHAPTERS}.")
            continue
        chapter = book.chapter(e.chapter)
        if chapter is None:
            r.errors.append(f"[{e.id}] Chapter {e.chapter} does not exist.")
        elif normalize_for_match(e.citation) not in normalize_for_match(chapter.text):
            r.errors.append(f"[{e.id}] Citation not found verbatim in chapter {e.chapter}: {e.citation!r}")

    # Story order can differ from page order (the book interleaves the Trask and Cathy threads),
    # so going backward in chapter number is worth flagging but is not an error.
    for prev, cur in zip(events, events[1:]):
        if cur.chapter < prev.chapter:
            r.warnings.append(f"[{cur.id}] Chapter {cur.chapter} comes before the previous event's chapter {prev.chapter}.")
    return r
