"""M1 prompts: one to propose the candidate pool, one to judge each candidate's significance."""

from ..mvp.prompt import SYSTEM as MVP_SYSTEM

PROMPT_VERSION = "m1-pool-1"
DEFAULT_COUNT = 35

# M0's one false event ("Cal borrows five thousand dollars from Kate") matches the 1955 film, not the novel.
SYSTEM = MVP_SYSTEM + """
Work from the novel only. The 1955 film and other adaptations change the plot; never use their scenes."""

TASK = """Propose a pool of exactly {count} candidate events that may lead to the focal event: Cal takes Aron
to Kate's house and reveals that Kate is their mother Cathy. A separate judge will later decide which of
them really matter, so include the major turning points and also smaller events whose importance is
debatable. Together they form a cause-and-effect graph across the novel's parallel story threads, which
converge on the focal event.

Rules:
- Order the events by when they happen in the story. The last event is the focal event itself, with
  is_focal_event=true; every other event has is_focal_event=false.
- causes lists the ids of earlier events in this list that directly cause or enable this event. Only
  list a cause when the link is real in the novel: without the earlier event, this one would not happen,
  or would happen very differently. Never add a link just to connect the graph.
- Every event must lead to the focal event through a chain of causes. If an event has no real path to
  the focal event, replace it with one that does.
- thread is the story thread the event belongs to: "Trask" (Adam, Charles, Cal, Aron), "Cathy/Kate"
  (Cathy's own story), "Hamilton" (Samuel and his family) or "Lee". If several threads meet in one event,
  pick the thread of the character who drives it. Use at least two threads, and show where they meet.
- chapter is the chapter number (1-55) where the event happens.
- citation is a short, distinctive phrase (under 15 words) from that chapter that a reader can type into
  their ebook's search to find the scene. Only use a phrase you are confident appears in the book;
  otherwise use a few distinctive words from the scene.
- summary is your own words, two or three sentences. Do not paste long passages.
- rationale says how this event feeds the path to the focal event."""

JUDGE_VERSION = "m1-judge-1"

JUDGE_SYSTEM = MVP_SYSTEM + """
Work from the novel only, never from its film or other adaptations. You are now judging, not proposing:
the events are given, and your job is to decide which of them the ending really depends on."""

JUDGE_TASK = """Below is a cause-and-effect graph of {count} events from East of Eden, in story order, ending
with the focal event: Cal takes Aron to Kate's house and reveals that Kate is their mother Cathy. Each
event lists its causes, the earlier events that cause or enable it.

Apply this significance test to every event, one at a time. Imagine the event removed from the novel,
with everything else as it was, and ask what happens to the path to the focal event:
- "path breaks": some later event, or the focal event itself, could no longer happen as it does.
- "key motive changes": the later events still happen, but a character does them for a different reason.
- "no real change": the story still reaches the focal event, for the same reasons.

Rules:
- Give exactly one verdict for every event, using its id. The focal event's effect is "path breaks"
  and its affects list is empty.
- affects lists the ids of the later events that would break or change without this one. They must be
  reachable from this event by following causes forward. Leave it empty for "no real change".
- Judge from the novel, not from the graph alone: an event can have several arrows out of it and still
  change nothing, because something else would have caused the same result.
- reason is one or two sentences in your own words: what breaks or changes, or why nothing does.
- There is no target number. Keep or cut each event on its own merits.

The graph, as JSON:
{pool}"""
