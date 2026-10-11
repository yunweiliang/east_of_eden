# east_of_eden

An agent that dissects John Steinbeck's *East of Eden* into a cause-and-effect plot graph, then builds
character-consistent alternate plots to study free will. The plan and ground rules are in `CLAUDE.md`, and
the history, costs and learnings are in `CHANGELOG.md`.

## MVP: 10 linear events leading to Cal's reveal

```
 ┌──────────────────────── the model ────────────────────────┐   ┌──────── plain Python ────────┐
 prompt ──► Claude picks 10 events, writes summaries ──► checks ──► events.json ──► timeline.html
            (can differ every time)                               (saved)        (same input → same picture)
```

### Is the output deterministic?

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

### Run it

```bash
pip install -e '.[dev]'
export ANTHROPIC_API_KEY=...          # or `ant auth login`
python -m eden extract                # picks, checks, pins, renders
# check each event in your copy, then set "user_verified" in output/mvp/events.json
python -m eden render                 # redraw from the pinned picks only, with no model call
pytest                                # uses a fake client, so it costs nothing
```

Outputs:
- `output/mvp/timeline.html`: the drawn plot line.
- `output/mvp/timeline.md`: the Mermaid version, which GitHub renders.
- `output/agent_runtime_costs.jsonl`: the agent's own API spend.
