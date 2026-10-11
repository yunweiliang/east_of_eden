"""MVP prompt: a single linear chain of events ending at the focal event."""

PROMPT_VERSION = "mvp-3"
DEFAULT_COUNT = 10

SYSTEM = """You are a careful literary analyst of John Steinbeck's East of Eden, working from your own
knowledge of the novel; no text is provided. Only include events you are confident happen in the book,
in the chapter you name. A reader will check every event against their own copy, so precision matters
more than coverage: if unsure of a chapter or detail, pick a different, well-known event instead."""

TASK = """Pick exactly {count} significant events that form a single linear chain leading to the focal
event: Cal takes Aron to Kate's house and reveals that Kate is their mother Cathy.

Rules:
- Order the events by when they happen in the story. The last event is the focal event itself, with
  is_focal_event=true; every other event has is_focal_event=false.
- Pick events that the focal event depends on, in a chain: each event should help cause or enable
  a later one. Prefer turning points over background.
- chapter is the chapter number (1-55) where the event happens.
- citation is a short, distinctive phrase (under 15 words) from that chapter that a reader can type into
  their ebook's search to find the scene. Only use a phrase you are confident appears in the book;
  otherwise use a few distinctive words from the scene.
- summary is your own words, two or three sentences. Do not paste long passages.
- rationale says why the path to the focal event needs this event."""
