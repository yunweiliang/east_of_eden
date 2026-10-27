# east_of_eden

An agent that reads a novel through one character's eyes and asks whether that character is stuck in a loop,
and who holds the key out of it. *East of Eden* is the dev set. The same agents are then applied to other books
without changing their prompts.

> **Plan revised 2026-10-27.** The earlier plan (alternate plots, divergence search, free-will classification)
> is parked; see [Parked](#parked). `CLAUDE.md` still holds the ground rules. Its milestone table describes the
> earlier plan and is superseded by this README.

## The research question

Cal Trask keeps reaching for something and keeps being turned away. This project treats that as a state
machine with a loop and a guarded exit:

- **Loop:** Cal seeks his father's approval, reads Adam's response as rejection, answers with resentment or
  harm, and reaches again.
- **Exit:** the way out depends on a condition Cal does not control.

**Hypothesis (to test, not a conclusion).** In Cal's own model, the exit condition is held by one other person,
Adam, and no exit attempt that bypasses Adam succeeds.

**It would be wrong if** an exit attempt through someone else (Abra, Lee) or by Cal alone breaks the loop, even
partly. It would also be weakened if most of its support is labels the model inferred instead of labels the text
states or shows.

**Open decision.** Whether the exit condition is Adam's approval (which keeps recurring) or his blessing (a
single scene that ends the loop). They give different loops, so it is settled before any labeling.

This is a claim about the book. The agents are the instrument, and their evals are quality control on it.

## What "correct" means

- **Layer 1, facts about the book (checkable).** Events, chapters, who knows what, and what each cited passage
  says. Correct means it matches the novel, as the user checks it in their own copy.
- **Layer 2, the reading (judged).** The loops and the exit analysis have no ground truth. Acceptable means all
  of these hold:
  1. Every label cites a passage and carries an evidence strength (`stated`, `shown`, `inferred`).
  2. The verifier passes the labels, and the claim rests on `stated` and `shown` labels, not `inferred` ones.
  3. The critic fails to break the claim after trying, and has itself been shown to find planted
     counterexamples.
  4. The user's own hand labels agree with the agents' on at least 80% of fields.
  5. The result is stable across repeated runs.
- **Any outcome is a finding.** Adam holds the exit; or someone else can; or there is no loop. The only failure
  is a critic or verifier that cannot be trusted, because then no verdict means anything.

## Books

| Role | Book | Rule |
|---|---|---|
| Dev set | *East of Eden* | Tune agents 1 to 7 here |
| Second dev set | *Something Wicked This Way Comes* | Write labels first; shows what the schema cannot express |
| Held-out test | *The Catcher in the Rye* | Freeze everything, write the user's labels first, run once, report whatever comes out |

The roles are a default and can be swapped. All three books are in copyright and the model works from memory, so
the user checks each citation in their own copy. This repo holds chapter numbers and short search phrases, never
passages. Never remove DRM. Because the held-out book is memory-only, a good result does not prove the model
reads without recall; it shows the method transfers.

## Agents

Each agent has its own folder with a README: what it is, what it does, input, output, and eval cases split into
regression and capability. Nothing below row 2 is implemented yet.

| # | Agent | One job | Status |
|---|---|---|---|
| 1 | [`event-extractor`](agents/event-extractor/) | Propose events that shape the focal character | Built |
| 2 | [`significance-judge`](agents/significance-judge/) | Keep or cut each event | Built |
| 3 | [`episode-labeler`](agents/episode-labeler/) | Turn each kept event into a labeled episode | Not started |
| 4 | [`evidence-verifier`](agents/evidence-verifier/) | Check every label against the text | Not started |
| 5 | [`loop-detector`](agents/loop-detector/) | Find repeated patterns | Not started |
| 6 | [`exit-analyzer`](agents/exit-analyzer/) | Find exit attempts and who holds the exit condition | Not started |
| 7 | [`adversarial-critic`](agents/adversarial-critic/) | Try to break the claim | Not started |
| 8 | [`report-builder`](agents/report-builder/) | Assemble the report | Not started |

```
book config ──► 1 extract ──► 2 judge ──► 3 label ──► 4 verify ──► 5 loops ──► 6 exits ──► 7 critic ──► 8 report
                                   gate between every stage: if it fails, nothing downstream runs
```

The orchestrator is plain Python, not a model. The focal character, chapter range and text mode come from a book
config, and no prompt names a character from any book. See [`agents/README.md`](agents/README.md) for the
conventions and for what regression and capability cases mean.

## Milestones and gates

A milestone is done only when every number in its gate is met. If a gate fails twice, change the design instead
of retuning the prompt. Each milestone gets its own branch and pull request, as before.

| Milestone | Agents | Gate |
|---|---|---|
| **P0: define correct** | none | Answer keys written by the user: reference picks grown to about 10, about 10 labeled episodes, the user's own cycle count, and the exit-condition decision above. Planted cases built. One command scores them. |
| **M1 close-out** | 1, 2 | Pool recall of the reference at least 90%. Judge keeps at least 80% of the reference. Run agreement at least 90%. Decoy test passes. |
| **M2: labels** | 3, 4 | At least 80% field agreement with the user's labels. At least 9 of 10 planted bad citations caught. Unsupported labels at most 10%. |
| **M3: loops** | 5 | Cycle count within one of the user's. At least 80% grouping agreement. |
| **M4: exits** | 6 | At least 80% recall on exit attempts. At least 80% agreement on who holds the exit condition. |
| **M5: critic** | 7 | At least 4 of 5 planted counterexamples found. At most one spurious flag on the clean baseline. |
| **M6: East of Eden report** | 8 | Claim, loop graph, evidence, critic findings and every eval number in one report. |
| **M7: transfer** | all, frozen | Second dev book tuned along the way. Held-out book run once on frozen prompts, scored against labels the user wrote first. Numbers reported as they come out. |

### Rough effort

About 60 hours, mostly the user's labeling and checking against the books, not building. This is an estimate,
not a commitment. At 8 hours a week it is about 8 weeks. M1 close-out through M2 has the most uncertainty.
The earlier milestones took about two days of agent work for about $4 of API spend.

## Parked

Not deleted. These come back only if the main line finishes.

- Alternate plot generation, the divergence search, and the pinned-ending experiments A and B.
- Free-will classification of divergences.
- Comparing models on the same task.
- A held-out novel the model has never seen, which needs text loading and a legal DRM-free copy. Commit
  `230312f` holds the old text loader.
- Related reading (Ryan, Dannenberg, Qin et al.) and a second opinion from an English professor. Both are best
  done before M2.

## Current implementation (MVP through M1)

What exists today is agents 1 and 2, built as stages `mvp`, `m0` and `m1`.

### MVP: 10 linear events leading to Cal's reveal

```
 ┌──────────────────────── the model ────────────────────────┐   ┌──────── plain Python ────────┐
 prompt ──► Claude picks 10 events, writes summaries ──► checks ──► events.json ──► timeline.html
            (can differ every time)                               (saved)        (same input → same picture)
```

#### Is the output deterministic?

Only partly. The **model** chooses the 10 events and writes their titles, summaries, search phrases and
reasons. That step is not deterministic: asking twice can give one or two different middle events and
differently worded summaries, and current models have no setting to turn the randomness off. Everything
after it is **plain Python** and fully repeatable.

How the project handles that:
1. **The answer is saved.** The picks are pinned in `events.json`. Running `extract` again reuses them
   instead of asking Claude, until you pass `--force` or change the prompt.
2. **Drawing is repeatable.** `render` turns the same `events.json` into exactly the same timeline every
   time, and a test checks this.
3. **Code catches broken answers,** such as the wrong count or a chapter outside 1–55, and sends them back
   to Claude to fix. Even a varied answer always has the right shape.

The variation is also a research signal. Milestone M1 runs extraction several times and compares the sets.
Events that appear every time are the model's confident turning points, and events that come and go are
borderline.

The model works from its own knowledge of the novel. No book text is sent. Each event gives a chapter and a
short search phrase. You look it up in your own copy and record the result in `output/mvp/events.json` by
setting `"user_verified": true` or `false`. Then re-render to update the "Checked" column.

Code checks that:
- there are exactly 10 events,
- the last one is the focal event,
- every chapter is in the range 1–55,
- every search phrase is under 15 words.

If a check fails, the model gets the errors and corrects its list (up to 2 times).

#### Run it

```bash
pip install -e '.[dev]'
export ANTHROPIC_API_KEY=...          # or `ant auth login`
python -m eden extract                # picks, checks, pins, renders
# check each event in your copy, then set "user_verified" in output/mvp/events.json
python -m eden render                 # redraw from the pinned picks only, with no model call
                                      # both take --stage mvp|m0|m1 (default: mvp)
python -m eden extract --stage m0     # M0: 20 events with causes, written to output/m0/
# M1: first write your own picks in output/m1/reference.json, then:
python -m eden extract --stage m1     # propose 30 events that shaped Cal; check each one in your copy
python -m eden judge --runs 5         # the significance test, 5 times over the same pool
pytest                                # uses a fake client, so it costs nothing
```

Outputs:
- `output/mvp/timeline.html`: the drawn plot line.
- `output/mvp/timeline.md`: the Mermaid version, which GitHub renders.
- `output/agent_runtime_costs.jsonl`: the agent's own API spend.

## License

The code is under the [MIT License](LICENSE). *East of Eden* is John Steinbeck's and remains under
copyright; so are the other two books named here. This repo holds no text from any of them, only chapter
numbers, short search phrases and the agent's own summaries.
