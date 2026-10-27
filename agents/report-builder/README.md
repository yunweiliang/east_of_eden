# report-builder

**Status:** not started. Plain code, no model call.

## What it is

The last agent. It assembles the outputs of the others into one report and refuses to produce a claim without
its evidence.

## What it does

- States the claim and, next to it, what would have shown it wrong.
- Draws the loop graph and puts the episode table, exit table and the critic's counterexamples beside it.
- Reports every eval number for every agent, so a reader can see how much to trust each stage.
- For several books, builds one comparison table with the same metrics side by side.
- Leaves the interpretive prose to the user. The report has marked places for the user's own writing.

## Input

- All agent outputs for a book, and the eval results.
- For comparison: the same files for each book.

## Output

`report.html` and `report.md` per book, and a cross-book comparison table.

## Evals

### Regression cases

- The same inputs give an identical report.
- A claim with no loop graph or no citation fails the build.
- No book text beyond chapter numbers and short search phrases appears in the output (copyright check).
- No model identifiers appear in the output.
- The failure condition is always printed with the claim.

### Capability cases

- **Traceable.** A reader can go from claim to graph to episode to citation in no more than three steps.
- **Comparable.** The cross-book table puts the three books side by side with identical metrics, and shows
  missing numbers as missing.
- **Honest limits.** The report lists what was excluded (which books, memory-only mode, the number of
  labelers) without being asked.

### Gate

M6: the East of Eden report has the claim, graph, evidence, critic's findings and every eval number, and passes
all regression cases.
