# significance-judge

**Status:** built, in `eden/stages/m1` (`python -m eden judge`). To do: take the focal character from a book
config, and add the decoy test below.

## What it is

The second agent. It decides which candidate events actually explain the focal character's behavior, so the
rest of the pipeline works on a short, defensible list.

## What it does

For each candidate, it applies one test: if this event had not happened, would the focal character make a
different choice at the focal moment, or be a different person? Each run gives every candidate a verdict
(changes the choice, changes who they are, or no real change) plus the later events it affects. It repeats the
test several times over the same pool and keeps the events that most runs keep. Events the user marked false
are left out, with paths bridged around them.

## Input

- The pinned pool from the event-extractor.
- Number of runs (default 5).
- The user's reference picks, for scoring.

## Output

- One file per run in `output/m1/judge/`, compared only when their `judge_hash` (everything the judge saw)
  matches.
- The kept set, each event's keep rate and the judge's reason for it.
- Agreement across runs, and recall against the user's reference picks.

## Evals

### Regression cases

- Runs with different `judge_hash` values are never compared.
- Events marked false by the user never appear in the kept set.
- Every "affects" link points to a later event in the graph.
- Same pool, same runs: the report renders identically.
- Old runs are archived, not replaced.

### Capability cases

- **Keeps the reference.** The judge keeps at least 80% of the user's reference picks.
- **Stable.** Average agreement across 5 runs is at least 90%. Agreement alone is not enough, because a model
  can consistently agree with itself while being wrong, so it is always reported next to recall.
- **Decoys.** Add 5 real but irrelevant events to the pool; the judge cuts at least 4.
- **Pivotal event.** On a hand-picked event the user considers essential, the verdict is "changes the choice" or
  "changes who they are" in all runs.

### Gate

M1 close-out: keeps at least 80% of the reference picks, with at least 90% run agreement.
