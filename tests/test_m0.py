from eden.core.llm import strict_schema
from eden.stages.m0.schema import Event, EventList, ModelEvent
from eden.stages.mvp.schema import ModelEvent as MvpModelEvent


def test_m0_event_has_every_mvp_field_plus_causes_and_thread():
    assert set(ModelEvent.model_fields) == set(MvpModelEvent.model_fields) | {"causes", "thread"}


def test_model_must_fill_causes_and_a_known_thread():
    item = strict_schema(EventList)["properties"]["events"]["items"]
    assert set(item["required"]) == set(ModelEvent.model_fields)
    assert item["properties"]["causes"]["type"] == "array"
    assert item["properties"]["thread"]["enum"] == ["Trask", "Cathy/Kate", "Hamilton", "Lee"]
    assert "user_verified" not in item["properties"]  # only the user sets this


def test_stored_event_adds_user_verified():
    e = Event(id="x", title="t", chapter=1, characters=[], summary="s", citation="c", rationale="r",
              is_focal_event=False, causes=[], thread="Trask")
    assert e.user_verified is None
