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
