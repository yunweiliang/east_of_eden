# east_of_eden

An agent that dissects John Steinbeck's *East of Eden* into a cause-and-effect plot graph, then builds
character-consistent alternate plots to study free will. The plan and ground rules are in `CLAUDE.md`, and
the history, costs and learnings are in `CHANGELOG.md`.

## MVP: 10 linear events leading to Cal's reveal

```
book (your copy) → split into chapters → model picks 10 events → code checks them → pinned events.json → timeline
     deterministic        deterministic        the only non-deterministic step       deterministic      deterministic
```

The model only chooses the events. Code checks every pick:
- there are exactly 10,
- the last one is the focal event,
- every chapter exists,
- every citation appears word for word in the chapter it cites.

If a check fails, the model gets the errors and corrects its list (up to 2 times). Accepted picks are
pinned in `output/mvp/events.json`, so re-drawing the timeline never calls the model again.

### Run it

```bash
pip install -e '.[dev]'
cp /path/to/east-of-eden.epub data/source/   # gitignored: the book never enters git
python -m eden chapters                       # check the book splits into chapters 1 to 55
export ANTHROPIC_API_KEY=...                  # or `ant auth login`
python -m eden extract                        # picks, checks, pins, renders
python -m eden render                         # redraw from the pinned picks only, with no model call
pytest                                        # tests use an invented mini-book, not the novel
```

Outputs:
- `output/mvp/timeline.html`: the drawn plot line.
- `output/mvp/timeline.md`: the Mermaid version, which GitHub renders.
- `output/agent_runtime_costs.jsonl`: the agent's own API spend.
