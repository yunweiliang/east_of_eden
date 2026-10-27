# evidence-verifier

**Status:** not started.

## What it is

The guard between the labeler and everything after it. No label reaches the loop detector unless its citation
has been checked.

## What it does

For every cited claim in `episodes.json`, it checks that the passage exists and supports the claim.

- **Memory-only mode (the default for these three books).** The books are in copyright, so the repo has no text.
  The verifier produces a checklist for the user: chapter, search phrase, the claim, and what to look for. The
  user ticks each one in their own copy and the verifier reads the result back. The verifier never sets
  `user_verified` itself.
- **Loaded-text mode (only if a legal DRM-free text exists).** It string-matches the phrase and runs an
  entailment check on the surrounding passage. Never remove DRM.

Labels that fail are held back and listed, so downstream agents see only supported labels, with the
unchecked ones marked as such.

## Input

- `episodes.json` from the episode-labeler.
- Text mode, and the user's ticks (memory-only mode).

## Output

- A verification report: per label, `supported`, `unsupported` or `unchecked`, and the unsupported rate.
- `episodes.verified.json`, containing only labels that passed or are explicitly flagged.
- The checklist file for the user to work through.

## Evals

### Regression cases

- A citation with a chapter outside the book's range is rejected.
- A search phrase of 15 words or more is rejected.
- `user_verified` is only ever set from the user's input, never by a model.
- An unverified label never reaches the loop detector without an `unchecked` mark.
- The checklist renders identically from the same input.

### Capability cases

- **Planted bad citations.** Take 10 labels the user has confirmed and break each in one way (wrong chapter,
  real phrase but wrong claim, invented phrase). The verifier catches at least 9 of 10.
- **False rejections.** At most 10% of the user's confirmed labels are wrongly rejected.
- **Checklist quality.** On a sample, the user can verify a label from the checklist entry alone, without
  searching further.
- **Transfer.** Same measures on the second dev book and once on the held-out book.

### Gate

M2: unsupported labels at most 10% after verification, and at least 9 of 10 planted bad citations caught.
