# event-extractor

**Status:** built, in `eden/stages/mvp`, `m0` and `m1`. To do: take the focal character from a book config instead
of hard-coding it.

## What it is

The first agent. It reads the book from the model's memory and proposes the events that matter for the focal
character, each with a citation the user can check.

## What it does

- Proposes a pool of about 30 candidate events that shape the focal character, in story order.
- Gives each event a chapter, a short search phrase, the characters involved, a one-line summary, the events
  that caused it, a thread (storyline), and one plain sentence on what it does to the focal character.
- Checks its own output in code (count, chapter range, phrase length, causes point backward) and repairs up to
  twice.
- Pins the answer, so rerunning reuses it until the prompt changes or the user forces a new run.

## Input

- Book config: title, focal character, chapter range, text mode (memory-only for now).
- Prompt version.

## Output

`events.json` for the stage, with id, title, chapter, characters, summary, citation (search phrase),
causes, thread, `for_focal`, and `user_verified` (set only by the user, `null` until then).

## Evals

### Regression cases

- Output passes the schema checks: chapter within the book's range, phrase under 15 words, causes acyclic and
  pointing backward, every event reaches the focal event.
- Rerunning with unchanged pinned picks makes no model call and renders identical output.
- Changing the prompt invalidates the pin.
- Lint: no prompt names a character from any book.
- A forced rerun archives the old picks instead of overwriting them.

### Capability cases

- **Recall of the user's reference picks.** Of the user's roughly 10 hand-written picks, at least 90% appear in
  the pool.
- **Grounding.** At least 90% of events are marked `user_verified: true` by the user, and invented scenes are
  counted separately.
- **Transfer.** With prompts unchanged, the same recall and grounding measures are reported on the second dev
  book and, once, on the held-out book.

### Gate

M1 close-out: pool recall of the reference set at least 90%.
