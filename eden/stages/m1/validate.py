"""M1 checks. The pool is checked exactly like M0's events; the judge's verdicts get checks of their own."""

from __future__ import annotations

from ...core.checks import Report
from ..m0.validate import validate  # noqa: F401  (the pool is an M0 graph, so it gets M0's checks)
from .schema import Event, Verdict


def one_verdict_each(events: list[Event], verdicts: list[Verdict]) -> list[str]:
    """The judge must rule on every candidate exactly once, and only on candidates that exist."""
    errors = []
    pool = {e.id for e in events}
    seen = set()
    for v in verdicts:
        if v.event_id not in pool:
            errors.append(f"[{v.event_id}] is not a candidate in the pool.")
        elif v.event_id in seen:
            errors.append(f"[{v.event_id}] has more than one verdict; give exactly one.")
        seen.add(v.event_id)
    errors += [f"[{e.id}] has no verdict." for e in events if e.id not in seen]
    return errors


def reveal_is_kept(events: list[Event], verdicts: list[Verdict]) -> list[str]:
    """Removing the reveal removes the ending itself, so it can never be "no real change"."""
    focal = {e.id for e in events if e.is_focal_event}
    return [f"[{v.event_id}] is the reveal itself; it can't be cut." for v in verdicts
            if v.event_id in focal and not v.keep]


def validate_verdicts(events: list[Event], verdicts: list[Verdict]) -> Report:
    r = Report()
    r.errors += one_verdict_each(events, verdicts)
    r.errors += reveal_is_kept(events, verdicts)
    return r
