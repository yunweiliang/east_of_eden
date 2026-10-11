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
- **Copyright.** *East of Eden* (1952) is still under US copyright. Never commit the book's text, or long
  excerpts from it, to this repo. Source text lives outside git (for example `data/source/`, which is
  gitignored) and comes from the user's own copy. Committed citations are a chapter number plus a short
  quote (one sentence or less).
- **Grounding.** Every extracted event must cite a chapter and a short quote, so a reader can catch invented
  scenes.
- **No model identifiers** in commits, code comments or docs.

## Shared data schema

Each milestone reads and writes the same event format, so a single visualizer works across all of them.
Fields are added as milestones progress.

```
Event {
  id, title, chapter, characters[], summary, citation   # MVP
  causes: [event ids]                                   # M0: directed acyclic graph (DAG)
  thread: "Trask" | "Cathy/Kate" | "Hamilton" | "Lee"   # M0: swimlanes
  edge_types: physical | enabling | motivational | informational   # M2
  character_state: { who: { knows, believes, wants, wounds } }     # M2
  necessity: necessary | contributing | overdetermined             # M3
}
```

## Framing notes

1. The book doesn't end on Cal telling Aron about Cathy. After the reveal, Aron enlists and dies in France,
   Kate commits suicide, Adam has a stroke and blesses Cal with *"Timshel."* Ending the graph at the reveal
   is fine for MVP–M1. From M2 on, the graph extends through the Timshel ending, because the counterfactual
   goal (Aron survives and Cal lives without guilt) can only be checked downstream of the reveal.
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
| **M5** | Consistency critic | A second agent checks each changed event against the character's established traits and feelings, with citations | Each change marked consistent or inconsistent, with reasons | Every change passes the critic, or is revised until it does |
| **M6** | Latest divergence point | Walk backward from the reveal. At each node, search for a character-consistent alternative that reaches the goal | The latest viable divergence point and the required changes | The answer is cited and the critic accepts it |
| **M7** | Free-will analysis | Classify each viable divergence: a character's choice, chance or outside events, or upbringing and temperament | Report, plus a per-character map of where alternatives remain open | See below |

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

## Stack (proposed)

- Python plus the Claude API for the agents (the extractor, then the critic).
- Visualizer: Mermaid for the MVP, then D3 or Cytoscape for swimlanes and side-by-side diffs.
- Hosting option: a page on yunweiliang.github.io (a Jekyll site with a passcode gate), for example
  `/east-of-eden/`.
- Evaluation: a reference event set the user curates by hand before M1.
