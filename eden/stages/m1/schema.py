"""M1 schema: a pool of candidate events, plus the judge's keep-or-cut verdict on each one.

M1 runs in two passes:
  1. Pool: the model proposes more events than M0 asks for, with causes and threads. The pool is pinned
     once and checked by the user, so every judge run sees exactly the same events and ids.
  2. Judge: the model applies the significance rule to every candidate and returns one Verdict each.
     It runs several times over the same pool; how often each event is kept measures stability.

Significance here means *character* significance (user decision, 2026-10-12): does the event explain why
Cal is the way he is when he takes Aron to Kate? The first version measured plot significance (would the
reveal still happen?), which kept nearly every early event; its pool and runs are archived.

A pool event is an M0 event plus `for_cal`, one plain sentence on what the event does to Cal.
"""

from typing import Literal

from pydantic import BaseModel, Field

from ..m0.schema import ModelEvent as M0ModelEvent


class ModelEvent(M0ModelEvent):
    """The fields the model fills in: every M0 field, plus what the event does to Cal."""

    for_cal: str = Field(description="One plain sentence, for a reader who doesn't know the novel: what Cal "
                                     "feels, learns, wants or fears because of this event")


class Event(ModelEvent):
    """A stored event. user_verified is set by the user after checking the event in their copy of the book."""

    user_verified: bool | None = None


class EventList(BaseModel):
    events: list[ModelEvent]


# The significance rule: imagine the event removed from the story. Who is Cal at the reveal without it?
Effect = Literal[
    "changes his choice",   # Cal wouldn't take Aron to Kate, or would do it for a different reason
    "changes who he is",    # he'd still do it, but would feel, believe, want or fear something different
    "no real change",       # Cal at the reveal is the same person, for the same reasons
]


class Verdict(BaseModel):
    """The judge's call on one candidate. Whether it's kept follows from `effect`, by the rule."""

    event_id: str = Field(description="Id of the candidate event this verdict is about")
    effect: Effect = Field(description="What would be different about Cal at the reveal if this event were removed")
    affects: list[str] = Field(description="Ids of the later events in the pool where Cal would think, feel or act "
                                           "differently without this one. Empty only for \"no real change\"")
    reason: str = Field(description="One or two sentences: what would be different about Cal, or why nothing would")

    @property
    def keep(self) -> bool:
        return self.effect != "no real change"


class VerdictList(BaseModel):
    verdicts: list[Verdict]
