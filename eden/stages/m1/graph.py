"""Graph helpers for M1: walking forward from an event, and removing events without losing paths."""

from __future__ import annotations

from .schema import Event


def downstream(events: list[Event], start: str) -> set[str]:
    """Every event that `start` leads to by following arrows forward, from cause to effect."""
    effects = {e.id: [] for e in events}  # cause id -> the events that list it as a cause
    for e in events:
        for c in e.causes:
            effects.setdefault(c, []).append(e.id)
    reached, to_visit = set(), [start]
    while to_visit:
        for nxt in effects.get(to_visit.pop(), []):
            if nxt not in reached:
                reached.add(nxt)
                to_visit.append(nxt)
    return reached


def without(events: list[Event], removed: set[str]) -> list[Event]:
    """The graph with some events taken out, keeping every path that ran through them.

    An arrow into a removed event is bridged: a kept event that listed it as a cause now lists that
    event's own causes instead (and theirs, if they were removed too). So a -> b -> c with b removed
    becomes a -> c. Events are copies; the originals are untouched.
    """
    by_id = {e.id: e for e in events}

    def kept_causes(event_id: str) -> list[str]:
        out = []
        for c in by_id[event_id].causes:
            if c not in by_id:
                continue
            out += [c] if c not in removed else kept_causes(c)
        return out

    return [e.model_copy(update={"causes": list(dict.fromkeys(kept_causes(e.id)))})
            for e in events if e.id not in removed]
