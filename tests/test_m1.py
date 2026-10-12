import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eden.core.llm import strict_schema
from eden.stages.m0 import schema as m0_schema
from eden.stages.m1.schema import EventList, Verdict, VerdictList


def test_pool_events_are_m0_events():
    assert EventList is m0_schema.EventList


def test_judge_must_fill_every_field_and_a_known_effect():
    item = strict_schema(VerdictList)["properties"]["verdicts"]["items"]
    assert set(item["required"]) == {"event_id", "effect", "affects", "reason"}
    assert item["properties"]["effect"]["enum"] == ["path breaks", "key motive changes", "no real change"]
    assert "keep" not in item["properties"]  # derived by the rule, never chosen by the model


def test_keep_follows_the_significance_rule():
    def verdict(effect):
        return Verdict(event_id="x", effect=effect, affects=[], reason="r")

    assert verdict("path breaks").keep
    assert verdict("key motive changes").keep
    assert not verdict("no real change").keep


from eden.stages.m1.schema import Event
from eden.stages.m1.validate import validate_verdicts


def cand(id, causes=(), focal=False):
    return Event(id=id, title="t", chapter=1, characters=[], summary="s", citation="c", rationale="r",
                 is_focal_event=focal, causes=list(causes), thread="Trask")


def says(id, effect="path breaks", affects=None):
    if affects is None:
        affects = [] if effect == "no real change" or id == "reveal" else ["reveal"]
    return Verdict(event_id=id, effect=effect, affects=affects, reason="r")


POOL = [cand("a"), cand("b", ["a"]), cand("reveal", ["b"], focal=True)]


def test_one_verdict_per_candidate_passes():
    assert validate_verdicts(POOL, [says("a", "no real change"), says("b"), says("reveal")]).ok


def test_catches_missing_duplicate_and_unknown_verdicts():
    errors = "\n".join(validate_verdicts(POOL, [says("a"), says("a"), says("ghost"), says("reveal")]).errors)
    assert "[a] has more than one verdict" in errors
    assert "[ghost] is not a candidate" in errors
    assert "[b] has no verdict" in errors


def test_reveal_cannot_be_cut():
    errors = validate_verdicts(POOL, [says("a"), says("b"), says("reveal", "no real change")]).errors
    assert errors == ["[reveal] is the reveal itself; it can't be cut."]


def test_claims_must_follow_the_arrows():
    # a -> b -> reveal, and x -> reveal: x can't affect b, and a keep must name something
    pool = [cand("a"), cand("x"), cand("b", ["a"]), cand("reveal", ["b", "x"], focal=True)]
    ok = [says("a", affects=["b", "reveal"]), says("x"), says("b"), says("reveal")]
    assert validate_verdicts(pool, ok).ok
    bad = [says("a", affects=[]), says("x", affects=["b"]), says("b", "no real change", ["reveal"]), says("reveal")]
    errors = "\n".join(validate_verdicts(pool, bad).errors)
    assert "[a] says \"path breaks\" but names no affected event" in errors
    assert "[x] names 'b' as affected, but no chain of causes leads from x to it" in errors
    assert "[b] says \"no real change\" but names affected events" in errors


import json
from types import SimpleNamespace

from test_pipeline import FakeStream

from eden.stages.m1.graph import without
from eden.stages.m1.judge import judge, judge_hash, judge_task, judged_pool


def test_removing_an_event_bridges_the_paths_through_it():
    # a -> b -> c -> reveal, and a -> reveal; remove b and c
    pool = [cand("a"), cand("b", ["a"]), cand("c", ["b"]), cand("reveal", ["c", "a"], focal=True)]
    kept = without(pool, {"b", "c"})
    assert [e.id for e in kept] == ["a", "reveal"]
    assert kept[1].causes == ["a"]  # bridged via c and b, and not listed twice
    assert pool[3].causes == ["c", "a"]  # the original is untouched


def test_judge_skips_events_the_reader_marked_false():
    pool = [cand("a"), cand("fake", ["a"]), cand("reveal", ["fake"], focal=True)]
    pool[1].user_verified = False
    assert [(e.id, e.causes) for e in judged_pool(pool)] == [("a", []), ("reveal", ["a"])]


def test_judge_sees_the_graph_but_not_the_proposers_rationale():
    pool = [cand("a"), cand("reveal", ["a"], focal=True)]
    pool[0].rationale = "SECRET ARGUMENT"
    task = judge_task(pool)
    assert '"causes": [\n   "a"\n  ]' in task and "SECRET ARGUMENT" not in task
    assert "Judge from the novel, not from the graph alone" in task
    changed = [cand("a"), cand("reveal", [], focal=True)]
    assert judge_hash(changed) != judge_hash(pool)  # a different graph is a different judge input


class FakeJudge:
    """Answers each call with the next list of verdicts."""

    def __init__(self, answers):
        self.answers, self.calls = list(answers), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self.stream))

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        text = json.dumps({"verdicts": [v.model_dump() for v in self.answers.pop(0)]})
        usage = SimpleNamespace(input_tokens=10, cache_creation_input_tokens=0, cache_read_input_tokens=0,
                                output_tokens=10)
        return FakeStream(SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=usage,
                                          stop_reason="end_turn", stop_details=None, model="claude-opus-5-5"))


def test_judge_repairs_a_missing_verdict():
    good = [says("a", "no real change"), says("b"), says("reveal")]
    client = FakeJudge([good[1:], good])
    result = judge(POOL, client=client)
    assert result.attempts == 2 and result.report.ok and [v.event_id for v in result.items] == ["a", "b", "reveal"]
    repair = client.calls[1]["messages"][-1]["content"]
    assert "[a] has no verdict" in repair and "one verdict for each of the 3 events" in repair
