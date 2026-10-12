"""M1 prompts: one to propose the candidate pool, one to judge each candidate's significance."""

from ..mvp.prompt import SYSTEM as MVP_SYSTEM

PROMPT_VERSION = "m1-pool-2"
DEFAULT_COUNT = 30

# M0's one false event ("Cal borrows five thousand dollars from Kate") matches the 1955 film, not the novel.
SYSTEM = MVP_SYSTEM + """
Work from the novel only. The 1955 film and other adaptations change the plot; never use their scenes.
Be exact about who does what: who tells whom, who gives what to whom. Crediting the right outcome to the
wrong character is the most common mistake a reader catches."""

TASK = """Propose a pool of exactly {count} candidate events that shaped Cal Trask into the person who
takes Aron to Kate's house and reveals that Kate is their mother Cathy. The question is not "what had to
happen for the plot to get there?" but "what explains why Cal is the way he is at that moment?": what he
feels, believes, wants and fears, and what has wounded him. A separate judge will later decide which of
them really matter, so include the formative moments and also smaller ones whose importance is debatable.

Rules:
- Center on Cal: moments he lives through, learns about, overhears or acts in. Include events from other
  characters' stories only when they reach Cal, for example by what he inherits, is told or is denied.
  Leave out events that only move the plot along without changing anything in Cal.
- Order the events by when they happen in the story. The last event is the focal event itself, with
  is_focal_event=true; every other event has is_focal_event=false.
- causes lists the ids of earlier events in this list that directly cause or enable this event, or
  that shape how Cal meets it. Only list a cause when the link is real in the novel. Never add a link
  just to connect the graph.
- Every event must lead to the focal event through a chain of causes. If an event has no real path to
  the focal event, replace it with one that does.
- thread is the story thread the event belongs to: "Trask" (Adam, Charles, Cal, Aron), "Cathy/Kate"
  (Cathy's own story), "Hamilton" (Samuel and his family) or "Lee". If several threads meet in one event,
  pick the thread of the character who drives it.
- chapter is the chapter number (1-55) where the event happens.
- citation is a short, distinctive phrase (under 15 words) from that chapter that a reader can type into
  their ebook's search to find the scene. Only use a phrase you are confident appears in the book;
  otherwise use a few distinctive words from the scene.
- summary is your own words, two or three sentences. Do not paste long passages.
- for_cal is one plain sentence for a reader who has never read the novel: what Cal feels, learns, wants
  or fears because of this event.
- rationale says how this event feeds Cal's state of mind at the focal event."""

JUDGE_VERSION = "m1-judge-2"

JUDGE_SYSTEM = MVP_SYSTEM + """
Work from the novel only, never from its film or other adaptations. You are now judging, not proposing:
the events are given, and your job is to decide which of them explain who Cal is when he makes his choice."""

JUDGE_TASK = """Below is a cause-and-effect graph of {count} events from East of Eden, in story order, ending
with the focal event: Cal takes Aron to Kate's house and reveals that Kate is their mother Cathy. Each
event lists its causes, the earlier events that cause or enable it.

Apply this test to every event, one at a time. Imagine the event removed from the novel, with everything
else as it was, and ask: who is Cal at the focal event without it?
- "changes his choice": Cal would not take Aron to Kate, or would do it for a different reason.
- "changes who he is": he would still do it, but would feel, believe, want or fear something different
  about himself, his father, his brother or his mother.
- "no real change": Cal at the focal event is the same person, for the same reasons.

Rules:
- Give exactly one verdict for every event, using its id. The focal event's effect is "changes his
  choice" and its affects list is empty.
- affects lists the ids of the later events where Cal would think, feel or act differently without this
  one. They must be reachable from this event by following causes forward. Leave it empty for "no real
  change".
- Plot is not enough. An event can be needed for the story to reach the focal event and still not shape
  Cal; if it only moves the plot, its effect is "no real change".
- Judge from the novel, not from the graph alone.
- reason is one or two sentences in your own words: what would be different about Cal, or why nothing
  would.
- There is no target number. Keep or cut each event on its own merits.

The graph, as JSON:
{pool}"""
