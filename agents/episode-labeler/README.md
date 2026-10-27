# episode-labeler

**Status:** not started. Replaces the old character-state milestone (M2).

## What it is

The agent that turns a list of important events into a structured record of how the focal character
experienced each one. Every later agent depends on these records.

## What it does

For each kept event, in story order, it writes an episode with:

- `state_in`: the character's situation, beliefs and wants going in.
- `trigger`: what happens to them.
- `interpretation`: what they take it to mean, and why they think the other person acted as they did.
- `second_order_belief`: what they think the other person thinks of them.
- `action`: what they do next.
- `state_out`: where it leaves them.

Each field has at least one citation (chapter and short search phrase) and an evidence strength: `stated`,
`shown` or `inferred`. The labeler may use only what the character could know at that point in the book.

## Input

- Kept events from the significance-judge.
- Book config: focal character and the people around them.
- The previous episode's `state_out`, so state carries forward.

## Output

`episodes.json`: one record per kept event with the fields above, plus `user_verified` (set only by the user).

## Evals

### Regression cases

- Every field is filled and every claim has a citation.
- `state_in` of an episode matches `state_out` of the one before, or a stated reason explains the change.
- Knowledge check: no label uses a fact the character cannot know yet at that chapter.
- Every `inferred` label is tagged as such; none is passed off as `stated`.
- Same input and pinned output render identically.

### Capability cases

- **Agreement with the user's labels** on about 10 episodes: at least 80% on `state_in`, `action` and
  `state_out`.
- **Second-order beliefs.** On episodes where the user knows the character misjudges what another thinks of
  them, the label captures the misjudgment.
- **Evidence strength.** The strength tags agree with the user's own on at least 80% of labels.
- **Not generic.** Interpretations differ across episodes instead of repeating one line of boilerplate.
- **Transfer.** The same agreement rates are reported on the second dev book and once on the held-out book.

### Gate

M2: at least 80% field agreement with the user's labels.
