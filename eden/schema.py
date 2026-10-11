"""Event schema shared by every milestone. Later milestones add fields."""

from typing import Literal

from pydantic import BaseModel, Field

# The story's parallel strands, drawn as swimlanes from M0 on.
Thread = Literal["Trask", "Cathy/Kate", "Hamilton", "Lee"]


class ModelEvent(BaseModel):
    """The fields the model fills in (MVP)."""

    id: str = Field(description="Short stable slug, e.g. 'cathy-shoots-adam'")
    title: str = Field(description="One-line name of the event")
    chapter: int = Field(description="Chapter number where the event happens")
    characters: list[str] = Field(description="Characters directly involved")
    summary: str = Field(description="Two or three sentences in your own words")
    citation: str = Field(description="A short phrase or sentence from the cited chapter, one sentence or less")
    rationale: str = Field(description="Why this event is needed for the path to the focal event")
    is_focal_event: bool = Field(description="True only for the final event: Cal reveals Cathy/Kate to Aron")


class M0ModelEvent(ModelEvent):
    """M0 adds graph edges and swimlanes. Both are required, so the model must fill them in."""

    causes: list[str] = Field(description="Ids of earlier events in this list that directly cause or enable this one")
    thread: Thread = Field(description="The story thread this event belongs to")


class Event(ModelEvent):
    """A stored event. Fields from later milestones are optional so older runs still load."""

    causes: list[str] = []
    thread: Thread | None = None
    user_verified: bool | None = None  # set by the user after checking the event in their copy of the book


class EventList(BaseModel):
    events: list[ModelEvent]


class M0EventList(BaseModel):
    events: list[M0ModelEvent]
