# Agents

Eight small agents, each with one job, one input and one output, so a failure points at one place. Nothing in
this folder is implemented yet. Each subfolder holds a README that fixes the contract and the eval cases
before any code is written.

```
book config ──► 1 event-extractor ──► 2 significance-judge ──► 3 episode-labeler ──► 4 evidence-verifier
                                                                                            │
   8 report-builder ◄── 7 adversarial-critic ◄── 6 exit-analyzer ◄── 5 loop-detector ◄──────┘
```

| # | Folder | One job | Status |
|---|---|---|---|
| 1 | [`event-extractor`](event-extractor/) | Propose events that shape the focal character | Built (stages `mvp`, `m0`, `m1`) |
| 2 | [`significance-judge`](significance-judge/) | Keep or cut each event | Built (`judge`, stage `m1`) |
| 3 | [`episode-labeler`](episode-labeler/) | Turn each kept event into a labeled episode | Not started |
| 4 | [`evidence-verifier`](evidence-verifier/) | Check every label against the text | Not started |
| 5 | [`loop-detector`](loop-detector/) | Find repeated patterns | Not started |
| 6 | [`exit-analyzer`](exit-analyzer/) | Find exit attempts and who holds the exit condition | Not started |
| 7 | [`adversarial-critic`](adversarial-critic/) | Try to break the claim | Not started |
| 8 | [`report-builder`](report-builder/) | Assemble the report from the other outputs | Not started |

The orchestrator is plain Python, not a model. It runs the agents in order and puts a gate between stages: if
an agent's gate fails, nothing downstream runs.

## Conventions every agent follows

- **Book-agnostic.** The focal character, chapter range and text mode come from a book config. No prompt
  names a character from any book. A lint test will enforce this.
- **One structured input, one structured output** (JSON). Schemas arrive with each agent's implementation.
- **Citations everywhere.** Every claim carries a chapter and a short search phrase (under 15 words), never
  book text. All three books are in copyright, so the repo holds no passages.
- **Evidence strength.** Labels are tagged `stated` (the text says it), `shown` (action or dialogue shows it)
  or `inferred` (the model's reading). Results count only the first two; `inferred` is reported separately.
- **Only the user sets `user_verified`.** A model never marks its own output as verified.
- **Outputs are archived, never replaced.**

## Eval cases: regression and capability

Every agent README lists eval cases at a high level, in two groups.

- **Regression cases** are things the agent must always get right: contract checks, determinism, cases it
  already passes, and "stay quiet" cases (a clean input must not produce flags). They are cheap, run on every
  change, and should pass 100%. A failure means something broke.
- **Capability cases** are harder tests that measure how good the agent is. They start with a low pass rate and
  are reported as a rate against the threshold in the agent's gate. A failure means the agent is not good
  enough yet, not that something broke.

Answer keys are written by the user, before a run, from their own copy of the book. They will live in
`evals/<book>/` and cite a chapter plus a short search phrase only. Planted cases (bad citations, false
counterexamples, decoy events) are built from the user's confirmed labels by changing one thing at a time, so
the correct answer is known by construction.

## Books

| Role | Book | Rule |
|---|---|---|
| Dev set | *East of Eden* | Tune agents 1 to 7 here |
| Second dev set | *Something Wicked This Way Comes* | Labels written first; shows what the schema cannot express |
| Held-out test | *The Catcher in the Rye* | Freeze everything, write labels first, run once, report whatever comes out |

These roles are a default and can be swapped. In every case the model works from memory, and the user checks
each citation in their own copy. Never remove DRM.
