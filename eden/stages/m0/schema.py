"""M0 event schema: the MVP event plus graph edges (causes) and a swimlane (thread)."""

from typing import Literal

from pydantic import BaseModel, Field

from ..mvp.schema import ModelEvent as MvpModelEvent

# The story's parallel strands, drawn as swimlanes.
Thread = Literal["Trask", "Cathy/Kate", "Hamilton", "Lee"]


class ModelEvent(MvpModelEvent):
    """The fields the model fills in: every MVP field, plus these two. Both are required."""

    causes: list[str] = Field(description="Ids of earlier events in this list that directly cause or enable "
                                          "this one. Empty only for an event that starts a thread")
    thread: Thread = Field(description="The story thread this event belongs to")


class Event(ModelEvent):
    """A stored event. user_verified is set by the user after checking the event in their copy of the book."""

    user_verified: bool | None = None


class EventList(BaseModel):
    events: list[ModelEvent]
