# exit-analyzer

**Status:** not started. This is the agent that produces the project's central measurement.

## What it is

For each loop, it asks how the character could get out, what stopped them, and who held the key.

## What it does

For every loop from the loop-detector, it finds the exit attempts: episodes where the character tries to break
the pattern, or where someone or something offers a way out. For each attempt it records:

- the route: the character alone, a named other person, or circumstance,
- the exit condition: what would have had to be true (for example, an approval from a particular person),
- the outcome: none, partial or full,
- the citations behind each of these.

It then writes the loop's exit criteria in one sentence and tallies who held the exit condition across attempts.

## Input

- `loops.json` and `episodes.verified.json`.
- The list of characters from the book config (it may name only people who are in the book).

## Output

`exits.json`: per loop, the attempts, the exit criteria sentence, and the tally of exit-condition holders. The
tally is the evidence for the claim the report makes.

## Evals

### Regression cases

- Every attempt cites an episode that belongs to its loop.
- Outcome is one of none, partial, full; route is one of self, a named other, circumstance.
- A loop with no exit attempt says so, rather than inventing one.
- Every named holder is a character in the config.
- Same input and pinned output render identically.

### Capability cases

- **Recall of exit attempts.** At least 80% of the attempts the user identified are found.
- **Holder classification.** Agrees with the user's classification on at least 80% of attempts.
- **Partial versus full.** On cases where the user has judged an exit partial, the agent does not call it full
  or none.
- **Decoys.** A repeat of the loop (the character tries the same thing again) is not counted as an exit.
- **Transfer.** Same measures on the second dev book and once on the held-out book.

### Gate

M4: at least 80% recall on exit attempts and at least 80% agreement on who holds the exit condition.
