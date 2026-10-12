"""M1 checks. The pool is checked exactly like M0's events; the judge's verdicts get checks of their own."""

from __future__ import annotations

from ...core.checks import Report
from ..m0.validate import validate  # noqa: F401  (the pool is an M0 graph, so it gets M0's checks)
from .graph import downstream
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


def claims_follow_the_graph(events: list[Event], verdicts: list[Verdict]) -> list[str]:
    """A keep must name what it affects, and everything it names must be downstream of it in the graph.

    The graph is the evidence for a significance claim: removing an event can only break or change events
    its arrows lead to. A cut ("no real change") names nothing.
    """
    errors = []
    pool = {e.id for e in events}
    focal = {e.id for e in events if e.is_focal_event}
    for v in verdicts:
        if v.event_id not in pool:
            continue  # one_verdict_each reports it
        if v.keep and not v.affects and v.event_id not in focal:  # the reveal has nothing after it
            errors.append(f"[{v.event_id}] says \"{v.effect}\" but names no affected event.")
        if not v.keep and v.affects:
            errors.append(f"[{v.event_id}] says \"no real change\" but names affected events; leave affects empty.")
        later = downstream(events, v.event_id)
        for a in v.affects:
            if a not in later:
                errors.append(f"[{v.event_id}] names '{a}' as affected, but no chain of causes leads from "
                              f"{v.event_id} to it.")
    return errors


def validate_verdicts(events: list[Event], verdicts: list[Verdict]) -> Report:
    r = Report()
    r.errors += one_verdict_each(events, verdicts)
    r.errors += reveal_is_kept(events, verdicts)
    r.errors += claims_follow_the_graph(events, verdicts)
    return r
