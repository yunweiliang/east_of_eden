"""MVP checks: the shared ones, plus a warning when the linear chain jumps backward in the book."""

from __future__ import annotations

from ...core.checks import Report, common_checks
from .schema import Event


def validate(events: list[Event], expected_count: int) -> Report:
    r = common_checks(events, expected_count)
    # Story order can differ from page order (the book interleaves the Trask and Cathy threads),
    # so going backward in chapter number is worth flagging but is not an error.
    for prev, cur in zip(events, events[1:]):
        if cur.chapter < prev.chapter:
            r.warnings.append(f"[{cur.id}] Chapter {cur.chapter} comes before the previous event's chapter {prev.chapter}.")
    return r
