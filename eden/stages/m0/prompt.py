"""M0 prompt: events across the story's threads, linked by causes, converging on the focal event."""

from ..mvp.prompt import SYSTEM  # same analyst and the same precision rules as the MVP

PROMPT_VERSION = "m0-1"
DEFAULT_COUNT = 20

TASK = """Pick exactly {count} significant events that lead to the focal event: Cal takes Aron to Kate's
house and reveals that Kate is their mother Cathy. Unlike a single chain, these events form a
cause-and-effect graph across the novel's parallel story threads, which converge on the focal event.

Rules:
- Order the events by when they happen in the story. The last event is the focal event itself, with
  is_focal_event=true; every other event has is_focal_event=false.
- causes lists the ids of earlier events in this list that directly cause or enable this event. Only
  list a cause when the link is real in the novel: without the earlier event, this one would not happen,
  or would happen very differently. Never add a link just to connect the graph.
- Every event must lead to the focal event through a chain of causes. If an event has no real path to
  the focal event, replace it with one that does.
- An event with no causes starts a thread. Most events should have at least one cause.
- thread is the story thread the event belongs to: "Trask" (Adam, Charles, Cal, Aron), "Cathy/Kate"
  (Cathy's own story), "Hamilton" (Samuel and his family) or "Lee". If several threads meet in one event,
  pick the thread of the character who drives it. Use at least two threads, and show where they meet.
- chapter is the chapter number (1-55) where the event happens.
- citation is a short, distinctive phrase (under 15 words) from that chapter that a reader can type into
  their ebook's search to find the scene. Only use a phrase you are confident appears in the book;
  otherwise use a few distinctive words from the scene.
- summary is your own words, two or three sentences. Do not paste long passages.
- rationale says why the focal event depends on this event."""
