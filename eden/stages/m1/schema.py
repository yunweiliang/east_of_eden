"""M1 schema: a pool of candidate events, plus the judge's keep-or-cut verdict on each one.

M1 runs in two passes:
  1. Pool: the model proposes more events than M0 asks for, with causes and threads. The pool is pinned
     once and checked by the user, so every judge run sees exactly the same events and ids.
  2. Judge: the model applies the significance rule to every candidate and returns one Verdict each.
     It runs several times over the same pool; how often each event is kept measures stability.

The pool's events are M0 events, so this stage reuses M0's classes instead of defining new ones.
"""

from typing import Literal

from pydantic import BaseModel, Field

from ..m0.schema import Event, EventList, ModelEvent  # noqa: F401  (the pool's schema, re-exported)

# The significance rule: imagine the event removed from the story. What happens to the path to the reveal?
Effect = Literal[
    "path breaks",          # some later event in the graph, or the reveal itself, could no longer happen
    "key motive changes",   # the path survives, but a character's reason for acting on it is different
    "no real change",       # the story still reaches the reveal for the same reasons
]


class Verdict(BaseModel):
    """The judge's call on one candidate. Whether it's kept follows from `effect`, by the rule."""

    event_id: str = Field(description="Id of the candidate event this verdict is about")
    effect: Effect = Field(description="What happens to the path to the reveal if this event is removed")
    reason: str = Field(description="One or two sentences: what breaks or changes without it, or why nothing does")

    @property
    def keep(self) -> bool:
        return self.effect != "no real change"


class VerdictList(BaseModel):
    verdicts: list[Verdict]
