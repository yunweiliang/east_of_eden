# East of Eden agent

An agent that dissects John Steinbeck's *East of Eden*. It builds a cause-and-effect graph of the plot,
then builds a character-consistent alternate plot, to study a research question about free will.

## Ground rules for Claude

- **Keep `CHANGELOG.md` current.** Every change that lands in the repo gets an entry under the current date:
  what changed and which milestone it serves.
- **Record cumulative build cost.** Append a row to the cost ledger in `CHANGELOG.md`:
  - at least once per working session,
  - whenever a milestone completes,
  - before any commit that closes out a chunk of work.

  The row gives the date, the session id, the session's cumulative `cost_usd` and the running total across
  all sessions.
  - **Where the number comes from:** in a Claude Code cloud session, call the `get_session` tool
    (claude-code-remote) with no `session_id` and read `external_metadata.usage.cost_usd`. That figure is
    cumulative for the session only, so the running total adds the last recorded value of each earlier session.
  - **Local CLI sessions:** use `/cost` instead.
  - **When cost can't be read:** write "unavailable" and never estimate silently.
  - **Agent API spend is separate.** Once the agent itself calls the Claude API, log its API spend in a
    separate "Agent runtime" column. That keeps the cost of building the agent apart from the cost of
    running it.
- **Log learnings.** This project is also practice for the user in building agents. Each `CHANGELOG.md` entry
  has a "Learnings" subsection that records:
  - **Went wrong:** mistakes, dead ends, bugs, wrong assumptions.
  - **Learned:** what worked, what generalizes to building other agents.
  - **User feedback:** the user's corrections and preferences, close to their own words.
  - **Friction:** where Claude got stuck, was blocked, or had to work around a limitation. Say it plainly
    and in the moment, too, not only in the log.
- **Every conclusion ships with a plot graph.** Any output that makes a claim (a significance pick, a
  divergence point, a free-will conclusion) must include the plot line or tree that backs it up. The
  graph is the evidence, and the prose explains it.
- **Copyright.** *East of Eden* (1952) is still under US copyright. Never commit the book's text, or long
  excerpts from it, to this repo. Source text lives outside git (for example `data/source/`, which is
  gitignored) and comes from the user's own copy. Committed citations are a chapter number plus a short
  quote (one sentence or less).
- **Grounding.** Every extracted event must cite a chapter and a short quote, so a reader can catch invented
  scenes.
  - **Book mode:** used when a DRM-free text is in `data/source/`. Code checks that each quote appears
    word for word in the chapter it cites.
  - **Memory mode (current default, user decision):** `extract --from-memory`. Store-bought copies are
    DRM-locked, so the model works from its own knowledge of the novel. Each citation is a short search
    phrase. The user checks every event in their own copy and records the result as `user_verified` in
    `events.json`. Code still checks the count, the focal event, the chapter range (1–55) and the phrase
    length.
  - **Never remove DRM** or suggest doing so.
  - Revisit sourcing before M5: the critic is better grounded in the real text.
- **No model identifiers** in commits, code comments or docs.
- **Branching (user decision):** each milestone gets its own branch and a pull request into `main`, which
  the user reviews and merges. Small housekeeping (changelog and cost rows, doc fixes) may go straight to
  `main`.

## Shared data schema

Each milestone reads and writes the same event format, so a single visualizer works across all of them.
Fields are added as milestones progress.

```
Event {
  id, title, chapter, characters[], summary, citation   # MVP
  rationale, is_focal_event                             # MVP: why it's on the path; marks the reveal
  user_verified: true | false | null                    # MVP: set by the user, never by the model
  causes: [event ids]                                   # M0: directed acyclic graph (DAG)
  thread: "Trask" | "Cathy/Kate" | "Hamilton" | "Lee"   # M0: swimlanes
  edge_types: physical | enabling | motivational | informational   # M2
  character_state: { who: { knows, believes, wants, wounds } }     # M2
  necessity: necessary | contributing | overdetermined             # M3
}
```

## Framing notes

1. **The focal event is Cal telling Aron about Cathy.** It is the moment of choice, the Cain moment, where
   the question "is Cal predestined to 'kill' Aron?" gets decided. Timshel is *not* the target event. From
   M2 on, the graph extends past the reveal to the **outcome events** (Aron enlists and dies, Kate's
   suicide and will, Adam's stroke, the Timshel blessing). These are not new targets. They are how the agent
   checks whether an alternate plot reaches the goal: Aron survives and Cal is free of guilt.
   - **Example.** Kate's will leaves her fortune to Aron. Remove the reveal and the secret may still come
     out through the will, so the alternate plot doesn't save Aron after all. Without the outcome events,
     the agent can't see this.
   - **Timshel's role.** It is the last node of the real book's graph. Whether alternate plots must keep
     it depends on the experiment (see "Two experiments: pinned endings" below):
     - In Experiment A it is free to disappear.
     - In Experiment B it is pinned, and it constrains everything before it.

     Either way, M7 compares the agent's findings with Steinbeck's answer. "Thou mayest" is said *after*
     the harm, so it is a claim about Cal's future. The research question is about the past: could Cal
     have avoided the harm?
2. Who knows that Kate is Cathy, and when they learn it, is the spine of the ending. Model it explicitly.

## Milestone plan

| Stage | Goal | New capability | Output | Done when |
|---|---|---|---|---|
| **MVP** | 10 linear events → Cal tells Aron about Cathy | Extract events, grounded in citations | Linear timeline | All 10 are cited and in order, and the user agrees with the picks |
| **M0** | 20 non-linear events → the reveal | `causes[]` edges plus parallel threads | Swimlane graph (DAG) where threads converge | Every node leads to the reveal, and parallel lanes merge visibly |
| **M1** | The agent chooses how many events (X) | Significance rule: remove an event, and if the path to the ending breaks or a key motive changes, it was significant | Graph plus the agent's reasons for keeping or cutting each event | The picks stay stable across runs and the user agrees with the cuts |
| **M2** | Character state model | Per event: each character's knowledge, beliefs, desires and wounds. Typed edges | Graph the user can step through, showing character state at each event | Correctly tracks who knows Kate = Cathy, and when |
| **M3** | Counterfactual dependency | For each node: "if this didn't happen, does the ending still occur?" | Nodes colored necessary, contributing or overdetermined | Overdetermined nodes are identified (Cal's anger has many sources) |
| **M4** | Alternate plot generation | Target: no reveal, Aron survives, Cal free of guilt. Find the smallest set of changes that reaches it | Before and after graphs side by side, differences highlighted | The after-graph satisfies all three goals |
| **M5** | Consistency critic and plot-hole detector | A second agent checks each changed event against the character's established traits and feelings, with citations. It also flags plot holes (see below) in any plot line, real or alternate | Each change marked consistent or inconsistent, plus a list of plot holes, each pinned to a node on the graph | Every change passes the critic with no plot holes left, or is revised until it does |
| **M6** | Latest divergence point | Walk backward from the reveal. At each node, search for a character-consistent alternative that reaches the goal while all pinned events still happen. Run Experiment A, then B | The latest viable divergence point, the required changes and the agent's hypothesized alternate ending, drawn through the downstream events | The answer is cited and the critic accepts it |
| **M7** | Free-will analysis | Classify each viable divergence: a character's choice, chance or outside events, or upbringing and temperament | Report, plus a per-character map of where alternatives remain open | See below |

### Plot holes the critic must catch

- **Knowledge violation:** a character acts on something they can't know yet (tracked by M2 knowledge state).
- **Uncaused event:** a node with no plausible cause in the graph.
- **Unmotivated choice:** a decision with no setup in the character's established wants and wounds.
- **Timeline contradiction:** events out of order, or overlapping in impossible ways.
- **Dangling thread:** a cause that should still fire but is ignored, such as Kate's will naming Aron.
- **Erased consequence:** a change that removes an event other nodes still depend on.

The real book's graph is a baseline. The critic should find few or no plot holes in it. If it flags many,
the critic is miscalibrated.

### Two experiments: pinned endings

The agent runs alternate plots under a **pinned-events** setting: a list of events that must still
happen. Everything not pinned can change. Pinning an outcome works backward: whatever the agent changes
upstream must still produce the pinned events, so the pin narrows which earlier histories are possible.
The user raised this.

- **Experiment A: open ending (the original question).**
  - **Pinned:** nothing after the reveal.
  - **Goal:** Aron survives and Cal is free of guilt.
  - **Asks:** what is the latest point where the story can change, and still be true to the characters,
    so that Cal doesn't "kill" Aron?
  - **Tests:** free will to *avoid* the harm.
- **Experiment B: fixed ending (fatalism test).**
  - **Pinned:** Adam dies and blesses Cal with "Timshel."
  - **Asks:** which earlier events are *forced* by that ending, and which can vary?
  - **If every surviving history still needs Cal's reveal and Aron's death:** the ending is fated, the way
    Oedipus's is. However the path wiggles, it arrives at the same place.
  - **If substitutes work** (Adam dies of something else, and Cal is forgiven for a different wrong): only
    the *shape* of the ending is fixed, not the route to it.
  - Watch for chains that pinning breaks:
    - Adam's stroke is caused by Aron's death.
    - Timshel only means something if Cal has something to be forgiven for.
- **A vs. B conflict, to test.** Pinning Timshel probably conflicts with A's goal that Cal has no guilt,
  because the blessing answers guilt. If the agent finds the two can't both hold, that is a result in its
  own right. In Steinbeck's structure, Cal's freedom ("thou mayest") might *require* the sin it forgives.
- **Output for each experiment:** before and after plot graphs, with pinned nodes marked, and events
  forced by a pin highlighted.
- **Order (decided): A first, then B.**
  - **A answers the original question.** It also produces what the user most wants to see: the agent's
    hypothesized open ending. That means the full downstream story, where Aron lives, what Cal becomes,
    whether Adam still has his stroke, and what happens to Kate's will.
  - **B is A plus a pin.** It reuses A's search, critic and before/after view, adding one backward
    constraint. Building A first means B costs little extra.
  - **A's alternate plots give B a baseline.** Once they exist, B checks whether any of them can still
    reach Timshel. That makes the A vs. B conflict test concrete instead of abstract.
  - **A is easier to grade.** "Does Aron survive, and is it in character?" is easier to judge than "is
    this event truly forced?", so the critic gets calibrated on A before facing B.

### Why M6/M7 is a free-will experiment

The constraint that changes must stay consistent with each character's story and feelings makes the
philosophical question testable.

- **If the latest viable divergence is Cal's own choice on the walk to Kate's,** then the same Cal, with
  the same history, could have done otherwise. That is the libertarian reading, roughly the claim *timshel*
  ("thou mayest") makes.
- **If every late alternative needs a different Cal** (the critic rejects "Cal just doesn't tell" as out of
  character), the divergence moves upstream. Candidates are:
  - Adam rejecting the $15,000 at Thanksgiving,
  - Adam's lie that the twins' mother is dead,
  - the gift-rejection pattern repeating from Charles and Adam.

  That points to a determinist or compatibilist reading.
- **Distance from the reveal back to the latest viable divergence is measurable,** and can be computed for
  each character (is Cal freer than Aron, and is Adam the least free?). Compare it against Steinbeck's
  own claim.

Hypotheses for M6 to test (not conclusions):
- Cal on the walk. He has shown restraint and remorse before.
- Adam at Thanksgiving. Refusing war-profit money fits Adam, but refusing it *gently* might also fit.
- Aron's fragility. Can Lee or Abra cushion the reveal?
- Adam's original lie about the twins' mother. Verify in the text who urged him to tell the truth.

## Code layout (MVP)

- `eden/source.py`: loads `data/source/*.epub|.txt` and splits it on "Chapter N" headings. Also holds the
  quote normalizer.
- `eden/extract.py`: the only model call. It uses structured outputs, append-only repair turns and refusal
  fallbacks. In book mode it also caches the book prefix.
- `eden/validate.py`: deterministic checks. Errors trigger a repair turn. Warnings, such as story order
  differing from page order, are only reported.
- `eden/render.py`: a pure function from `events.json` to `timeline.md` (Mermaid) and `timeline.html`
  (inline SVG).
- `python -m eden {chapters,extract,render}`. `extract` skips the model call when the pinned picks match the
  source (the book hash, or "memory") and the prompt hash.
- Tests use `tests/fixtures/mini_book.txt`, an invented text, so CI never needs the novel.

## Stack (proposed)

- Python plus the Claude API for the agents (the extractor, then the critic).
- Visualizer: Mermaid for the MVP, then D3 or Cytoscape for swimlanes and side-by-side diffs.
- Hosting (user decision): everything stays in this GitHub repo for now. The user will add it to the
  portfolio site (yunweiliang.github.io) themselves later. Don't touch the portfolio repo for this project.
- Evaluation: a reference event set the user curates by hand before M1.
