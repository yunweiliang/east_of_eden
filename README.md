# east_of_eden

An agent that dissects John Steinbeck's *East of Eden* into a cause-and-effect plot graph, then builds
character-consistent alternate plots to study free will. The plan and ground rules are in `CLAUDE.md`, and
the history, costs and learnings are in `CHANGELOG.md`.

## MVP: 10 linear events leading to Cal's reveal

```
model picks 10 events → code checks them → pinned events.json → timeline → you check each event in your copy
  the only uncertain step     deterministic       deterministic      deterministic
```

Store-bought ebooks (Kindle included) are copy-protected, so by default the model works from its own knowledge
of the novel (`--from-memory`). Each event gives a chapter and a short search phrase. You look it up in your
copy and record the result in `output/mvp/events.json` by setting `"user_verified": true` or `false`. Then
re-render to update the "Checked" column. If you ever have a DRM-free text, drop it in `data/source/` and
run without the flag. Code then checks every quote word for word.

Code checks that:
- there are exactly 10 events,
- the last one is the focal event,
- every chapter is in the range 1–55,
- every phrase is short.

If a check fails, the model gets the errors and corrects its list (up to 2 times).

### Run it

```bash
pip install -e '.[dev]'
export ANTHROPIC_API_KEY=...          # or `ant auth login`
python -m eden extract --from-memory  # picks, checks, pins, renders
# check each event in your copy, then set "user_verified" in output/mvp/events.json
python -m eden render                 # redraw from the pinned picks only, with no model call
pytest                                # tests use an invented mini-book, not the novel
```

Outputs:
- `output/mvp/timeline.html`: the drawn plot line.
- `output/mvp/timeline.md`: the Mermaid version, which GitHub renders.
- `output/agent_runtime_costs.jsonl`: the agent's own API spend.
