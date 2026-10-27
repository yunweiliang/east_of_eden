# loop-detector

**Status:** not started. Mostly plain code, with a model used only to compare patterns.

## What it is

The agent that finds out whether the focal character repeats the same pattern, and how many times.

## What it does

Takes the verified episodes in story order and groups them by pattern: the shape of `state_in`, `action` and
`state_out`. A loop is a group of two or more episodes where the character starts in a similar state, acts in
a similar way, and ends in a similar state. It reports:

- each loop, its member episodes, and a one-line description of the pattern,
- the cycle count,
- where the pattern breaks (episodes that look similar but end differently).

## Input

- `episodes.verified.json` from the evidence-verifier.

## Output

`loops.json` with loop id, member episodes in order, pattern description, cycle count and break points, plus a
loop graph (Mermaid and HTML). Every loop is drawn, because a claim needs its graph.

## Evals

### Regression cases

- Same input gives the same groups, every time.
- Episodes are ordered by chapter.
- No loop has fewer than two episodes.
- An input with no repeated pattern (a synthetic set of unrelated episodes) returns zero loops.
- Every episode in a loop exists in the input.

### Capability cases

- **Cycle count.** Within one of the user's own count on the dev book.
- **Pattern groups.** At least 80% of the user's hand-grouped episodes land in the same loops.
- **Decoys.** Two episodes that look alike but have different meanings (different trigger or different
  `state_out`) are not merged.
- **Two loops.** From a set mixing two distinct patterns, the detector returns two loops, not one.
- **Transfer.** Same measures on the second dev book and once on the held-out book.

### Gate

M3: cycle count within one of the user's, with at least 80% grouping agreement.
