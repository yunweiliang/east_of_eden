"""Event schema shared by every milestone. MVP fields only; later milestones add fields."""

from pydantic import BaseModel, Field


class Event(BaseModel):
    id: str = Field(description="Short stable slug, e.g. 'cathy-shoots-adam'")
    title: str = Field(description="One-line name of the event")
    chapter: int = Field(description="Chapter number where the event happens")
    characters: list[str] = Field(description="Characters directly involved")
    summary: str = Field(description="Two or three sentences in your own words")
    citation: str = Field(description="A verbatim quote of one sentence or less from the cited chapter")
    rationale: str = Field(description="Why this event is needed for the path to the focal event")
    is_focal_event: bool = Field(description="True only for the final event: Cal reveals Cathy/Kate to Aron")


class EventList(BaseModel):
    events: list[Event]
