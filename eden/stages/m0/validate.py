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


def validate(events: list[Event], expected_count: int) -> Report:
    r = common_checks(events, expected_count)
    r.errors += causes_point_backward(events)
    return r
