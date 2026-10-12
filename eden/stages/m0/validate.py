"""M0 checks: the shared ones, plus checks that the causes form a proper graph."""

from __future__ import annotations

from ...core.checks import Report, common_checks
from .schema import Event


def causes_point_backward(events: list[Event]) -> list[str]:
    """Every cause must be an event that comes earlier in the list.

    The list is in story order, so this also rules out loops: an arrow can only go back in time,
    and you can't get back to where you started by only going backward.
    """
    errors = []
    all_ids = {e.id for e in events}
    earlier = set()  # ids of the events we've already walked past
    for e in events:
        for cause in e.causes:
            if cause == e.id:
                errors.append(f"[{e.id}] lists itself as a cause.")
            elif cause not in all_ids:
                errors.append(f"[{e.id}] cause '{cause}' is not an event in this list.")
            elif cause not in earlier:
                errors.append(f"[{e.id}] cause '{cause}' comes later in the list; causes must come earlier.")
        earlier.add(e.id)
    return errors


def all_lead_to_reveal(events: list[Event]) -> list[str]:
    """Every event must be connected to the focal event by a chain of causes.

    Start at the reveal and walk backward along the arrows, collecting every event we can reach.
    Anything never reached is a dead end: it doesn't help cause the reveal.
    """
    by_id = {e.id: e for e in events}
    focal = next((e for e in events if e.is_focal_event), None)
    if focal is None:
        return []  # common_checks already reports a missing focal event
    reached = {focal.id}
    to_visit = [focal.id]  # events whose causes we still have to look at
    while to_visit:
        current = by_id[to_visit.pop()]
        for cause in current.causes:
            if cause in by_id and cause not in reached:
                reached.add(cause)
                to_visit.append(cause)
    return [f"[{e.id}] doesn't lead to the reveal: no chain of causes connects it to the focal event. "
            "List it as a cause of a later event, or replace it."
            for e in events if e.id not in reached]


def validate(events: list[Event], expected_count: int) -> Report:
    r = common_checks(events, expected_count)
    r.errors += causes_point_backward(events)
    r.errors += all_lead_to_reveal(events)
    return r
