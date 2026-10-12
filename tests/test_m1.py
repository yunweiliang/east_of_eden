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
    assert set(item["required"]) == {"event_id", "effect", "reason"}
    assert item["properties"]["effect"]["enum"] == ["path breaks", "key motive changes", "no real change"]
    assert "keep" not in item["properties"]  # derived by the rule, never chosen by the model


def test_keep_follows_the_significance_rule():
    def verdict(effect):
        return Verdict(event_id="x", effect=effect, reason="r")

    assert verdict("path breaks").keep
    assert verdict("key motive changes").keep
    assert not verdict("no real change").keep


from eden.stages.m1.schema import Event
from eden.stages.m1.validate import validate_verdicts


def cand(id, causes=(), focal=False):
    return Event(id=id, title="t", chapter=1, characters=[], summary="s", citation="c", rationale="r",
                 is_focal_event=focal, causes=list(causes), thread="Trask")


def says(id, effect="path breaks"):
    return Verdict(event_id=id, effect=effect, reason="r")


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
