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


from eden.stages.m0.validate import causes_point_backward


def m0(id, causes):
    return Event(id=id, title="t", chapter=1, characters=[], summary="s", citation="c", rationale="r",
                 is_focal_event=False, causes=causes, thread="Trask")


def test_backward_arrows_pass():
    events = [m0("a", []), m0("b", ["a"]), m0("c", ["a", "b"])]
    assert causes_point_backward(events) == []


def test_catches_self_cause_unknown_id_and_forward_arrow():
    events = [m0("a", ["b"]), m0("b", ["b"]), m0("c", ["ghost"])]
    errors = "\n".join(causes_point_backward(events))
    assert "[a] cause 'b' comes later" in errors
    assert "[b] lists itself" in errors
    assert "[c] cause 'ghost' is not an event" in errors


from eden.stages.m0.validate import all_lead_to_reveal


def focal(id, causes):
    e = m0(id, causes)
    e.is_focal_event = True
    return e


def test_two_threads_merging_into_the_reveal_pass():
    # a -> b -> reveal  and  x -> reveal: two lanes converging
    events = [m0("a", []), m0("x", []), m0("b", ["a"]), focal("reveal", ["b", "x"])]
    assert all_lead_to_reveal(events) == []


def test_catches_a_dead_end():
    # d causes nothing that reaches the reveal
    events = [m0("a", []), m0("d", []), focal("reveal", ["a"])]
    errors = all_lead_to_reveal(events)
    assert len(errors) == 1 and errors[0].startswith("[d] doesn't lead to the reveal")


from test_pipeline import FakeClient

from eden.core.llm import extract_events, prompt_hash
from eden.stages import STAGES, m0 as m0_stage
from eden.stages.m0.render import to_markdown
from eden.stages.m0.validate import uses_several_threads, validate


def lane(id, causes, thread, chapter=1, focal=False):
    e = m0(id, causes)
    e.thread, e.chapter, e.is_focal_event = thread, chapter, focal
    return e


GRAPH = [lane("a", [], "Trask", 3), lane("x", [], "Cathy/Kate", 8),
         lane("b", ["a"], "Trask", 20), lane("reveal", ["b", "x"], "Trask", 49, focal=True)]


def test_m0_is_a_registered_stage_with_its_own_prompt():
    assert STAGES["m0"] is m0_stage and m0_stage.DEFAULT_COUNT == 20
    assert prompt_hash(m0_stage, 20) != prompt_hash(STAGES["mvp"], 10)
    assert "Never add a link just to connect the graph" in m0_stage.TASK


def test_single_thread_graph_is_an_error():
    one_lane = [lane("a", [], "Trask"), lane("reveal", ["a"], "Trask", focal=True)]
    assert uses_several_threads(one_lane) and not uses_several_threads(GRAPH)


def test_repair_turn_fixes_a_dead_end():
    dead_end = GRAPH[:3] + [lane("d", [], "Lee", 30), GRAPH[3]]  # "d" feeds into nothing
    client = FakeClient([dead_end, GRAPH])  # first answer has the dead end, the repaired one doesn't
    result = extract_events(m0_stage, 4, client=client)
    assert result.attempts == 2 and result.report.ok
    assert "[d] doesn't lead to the reveal" in client.calls[1]["messages"][-1]["content"]
    assert all(isinstance(e, m0_stage.Event) for e in result.items)


def test_graph_draws_lanes_and_arrows():
    md = to_markdown(GRAPH, {"prompt_hash": "p"})
    assert 'subgraph lane_n_Cathy_Kate["Cathy/Kate"]' in md
    assert "n_a --> n_b" in md and "n_x --> n_reveal" in md
    assert "(starts a thread)" in md
    assert to_markdown(GRAPH, {"prompt_hash": "p"}) == md  # deterministic


from eden.stages.m0.render import COL, edge_path, render, to_html


def test_swimlanes_draw_one_lane_per_used_thread_in_fixed_order():
    svg = to_html(GRAPH, {"prompt_hash": "p"})
    assert svg.index(">Trask</text>") < svg.index(">Cathy/Kate</text>")
    assert ">Hamilton</text>" not in svg and ">Lee</text>" not in svg  # no empty lanes


def test_swimlanes_draw_one_arrow_per_cause_and_mark_the_reveal():
    page = to_html(GRAPH, {"prompt_hash": "p"})
    assert page.count('class="edge') == sum(len(e.causes) for e in GRAPH)
    assert page.count('class="edge cross focal"') == 1  # x (Cathy/Kate) -> reveal (Trask)
    assert 'class="node focal"' in page


def test_arrow_shapes():
    assert edge_path(0, 46, COL, 46).startswith("M0,46 L")       # next-door, same lane: straight
    assert " C" in edge_path(0, 46, 3 * COL, 46)                  # longer jump, same lane: arcs over
    assert edge_path(0, 46, COL, 196) == f"M0,46 C{COL / 2:g},46 {COL / 2:g},196 {COL},196"  # across lanes


def test_model_text_is_escaped_in_the_drawing(tmp_path):
    evil = lane("a", [], "Lee", 2)
    evil.title = "<script>alert(1)</script>"
    paths = render([evil, lane("reveal", ["a"], "Trask", 49, focal=True)], {"prompt_hash": "p"}, tmp_path)
    assert [p.name for p in paths] == ["graph.md", "graph.html"]
    assert "<script>" not in (tmp_path / "graph.html").read_text()


from eden.core.html import check_summary


def test_check_summary_counts_checked_and_true_separately():
    a, b, c = lane("a", [], "Trask"), lane("b", [], "Trask"), lane("c", [], "Trask")
    assert check_summary([a, b, c]) == "0/3 checked by the reader"
    a.user_verified, b.user_verified = True, False
    assert check_summary([a, b, c]) == "2/3 checked by the reader, 1 true"
