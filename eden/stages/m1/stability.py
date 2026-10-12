"""Stability across judge runs: how often each event is kept, and how much the runs agree."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations

from .runs import JudgeRun
from .schema import Effect, Verdict


@dataclass
class Tally:
    """Every verdict one event received, across runs."""

    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def kept(self) -> int:
        return sum(v.keep for v in self.verdicts)

    @property
    def runs(self) -> int:
        return len(self.verdicts)

    @property
    def effect(self) -> Effect | None:
        """The effect most runs gave. Ties go to the latest run among the tied effects."""
        if not self.verdicts:
            return None
        counts = Counter(v.effect for v in self.verdicts)
        top = max(counts.values())
        return next(v.effect for v in reversed(self.verdicts) if counts[v.effect] == top)

    @property
    def typical(self) -> Verdict | None:
        """The latest verdict with the most common effect: the reason shown on the page."""
        return next((v for v in reversed(self.verdicts) if v.effect == self.effect), None)


def tally(event_ids: list[str], runs: list[JudgeRun]) -> dict[str, Tally]:
    out = {i: Tally() for i in event_ids}
    for run in runs:
        for v in run.verdicts:
            if v.event_id in out:
                out[v.event_id].verdicts.append(v)
    return out


def consensus(tallies: dict[str, Tally]) -> set[str]:
    """Events kept by more than half the runs. This is the agent's answer to "which events matter"."""
    return {i for i, t in tallies.items() if t.runs and 2 * t.kept > t.runs}


def kept_sets(runs: list[JudgeRun]) -> list[set[str]]:
    return [{v.event_id for v in r.verdicts if v.keep} for r in runs]


def agreement(runs: list[JudgeRun]) -> float | None:
    """Average overlap of the kept sets over every pair of runs (Jaccard: shared / either). 1.0 = identical."""
    sets = kept_sets(runs)
    pairs = [len(a & b) / len(a | b) for a, b in combinations(sets, 2) if a | b]
    return round(sum(pairs) / len(pairs), 3) if pairs else None
