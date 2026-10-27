# adversarial-critic

**Status:** not started. Replaces the old consistency critic and plot-hole detector (M5), repointed from alternate
plots to the claim.

## What it is

A second agent whose only job is to break the claim the report is about to make. It does not edit other agents'
outputs.

## What it does

Given the claim ("the exit condition for this loop is held by one other person") and the evidence, it looks for:

- **Counterexamples:** an exit attempt that worked, even partly, without the named holder.
- **Rival readings:** another explanation that fits the same episodes.
- **Over-reading:** a claim that rests mostly on `inferred` labels.
- **Plot holes in the labels:** a character acting on something they cannot yet know, a choice with no setup,
  events out of order, a thread that should fire and is ignored.

It ends with a verdict: the claim stands, is weakened, or fails.

## Input

- `exits.json`, `loops.json`, `episodes.verified.json`.
- The claim statement and the failure condition written in advance.

## Output

`critique.json`: counterexamples with citations, rival readings, an audit of how much of the claim's support is
`inferred`, plot-hole flags pinned to episodes, and the verdict.

## Evals

### Regression cases

- On a clean baseline (labels the user has confirmed), at most one spurious flag.
- Every counterexample and flag cites an episode.
- The critic never changes another agent's output file.
- Every plot hole flagged is one of the defined hole types.
- Same input and pinned output render identically.

### Capability cases

- **Planted counterexamples.** Insert 5 false exit successes that do not involve the named holder into the
  user's confirmed labels. The critic finds at least 4.
- **Planted over-reading.** Replace supporting labels with `inferred` ones; the critic flags that the claim now
  rests on inference.
- **Rival reading.** Produces at least one rival reading that the user rates as plausible.
- **Stable.** The verdict is the same in 3 of 3 runs.
- **Transfer.** Same measures on the second dev book and once on the held-out book.

### Gate

M5: at least 4 of 5 planted counterexamples found, with at most one spurious flag on the clean baseline.
