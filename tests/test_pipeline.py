import json
from types import SimpleNamespace

from conftest import FIXTURES
from eden.extract import extract_events, strict_schema
from eden.render import to_html, to_markdown
from eden.schema import Event, EventList, ModelEvent
from eden.source import load_book
from eden.validate import validate


def ev(i, chapter, citation, focal=False):
    return Event(id=f"e{i}", title=f"Event {i}", chapter=chapter, characters=["A"], summary="s",
                 citation=citation, rationale="r", is_focal_event=focal)


GOOD = [
    ev(1, 1, "Two brothers planted it in a dry spring."),
    ev(2, 2, "A stranger arrived with a letter."),
    ev(3, 3, "He told his brother what it said.", focal=True),
]


def test_valid_list_passes():
    assert validate(GOOD, load_book(FIXTURES / "mini_book.txt"), 3).ok


def test_catches_invented_quote_wrong_count_and_missing_focal():
    bad = [ev(1, 1, "The brothers argued about the orchard."), ev(2, 9, "Anything.")]
    report = validate(bad, load_book(FIXTURES / "mini_book.txt"), 3)
    text = "\n".join(report.errors)
    assert "Expected exactly 3" in text
    assert "not found verbatim" in text
    assert "Chapter 9 does not exist" in text
    assert "is_focal_event" in text


def test_backward_chapter_is_warning_not_error():
    events = [GOOD[1], GOOD[0], GOOD[2]]
    report = validate(events, load_book(FIXTURES / "mini_book.txt"), 3)
    assert report.ok and report.warnings


def test_strict_schema_inlines_defs_and_forbids_extra_keys():
    schema = strict_schema(EventList)
    assert "$defs" not in json.dumps(schema)
    item = schema["properties"]["events"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(ModelEvent.model_fields)
    assert "user_verified" not in item["properties"]


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    """Returns one bad answer, then a good one, to exercise the repair turn."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self.stream))

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        events = self.answers.pop(0)
        text = json.dumps({"events": [e.model_dump(exclude={"user_verified"}) for e in events]})
        usage = SimpleNamespace(input_tokens=100, cache_creation_input_tokens=1000,
                                cache_read_input_tokens=0, output_tokens=50)
        return FakeStream(SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)], usage=usage,
            stop_reason="end_turn", stop_details=None, model="claude-opus-5-5"))


def test_repair_turn_fixes_a_bad_quote():
    book = load_book(FIXTURES / "mini_book.txt")
    bad = [GOOD[0], ev(2, 2, "A stranger arrived with a parcel."), GOOD[2]]
    client = FakeClient([bad, GOOD])
    result = extract_events(book, 3, client=client)
    assert result.report.ok and result.attempts == 2
    assert result.usage["output_tokens"] == 100
    repair_msg = client.calls[1]["messages"][-1]["content"]
    assert "not found verbatim" in repair_msg
    assert result.cost_usd == round((200 * 4 + 2000 * 5 + 100 * 20) / 1e6, 4)


def test_render_is_deterministic():
    meta = {"source_sha256": "abc", "prompt_hash": "p"}
    assert to_html(GOOD, meta) == to_html(GOOD, meta)
    md = to_markdown(GOOD, meta)
    assert "flowchart LR" in md and "n_e2 --> n_e3" in md


def test_memory_mode_validates_without_book():
    events = [ev(1, 3, "any phrase"), ev(2, 30, "another"), ev(3, 55, "last", focal=True)]
    assert validate(events, None, 3).ok
    report = validate([ev(1, 3, "x"), ev(2, 56, "y"), ev(3, 0, "z", focal=True)], None, 3)
    assert sum("outside 1-55" in e for e in report.errors) == 2


def test_memory_mode_sends_no_book_and_uses_memory_prompt():
    client = FakeClient([[ev(1, 3, "a"), ev(2, 30, "b"), ev(3, 55, "c", focal=True)]])
    result = extract_events(None, 3, client=client)
    call = client.calls[0]
    assert result.report.ok and result.attempts == 1
    assert len(call["messages"][0]["content"]) == 1
    assert "no text is provided" in call["system"]
    assert all(e.user_verified is None for e in result.events)


def test_render_shows_reader_checks():
    events = [ev(1, 1, "a"), ev(2, 2, "b"), ev(3, 3, "c", focal=True)]
    events[0].user_verified = True
    events[1].user_verified = False
    md = to_markdown(events, {"grounding": "memory", "prompt_hash": "p"})
    assert "1/3 events checked" in md and "✓ checked" in md and "✗ wrong" in md and "unchecked" in md
    assert "not the text" in md


def test_mermaid_and_table_survive_awkward_model_output():
    events = [ev(1, 1, "a"), ev(2, 2, "b"), ev(3, 3, "c", focal=True)]
    events[0].id = "end"
    events[1].id = "cal's.gift"
    events[1].title = 'Adam says "No" & <leaves>'
    events[2].rationale = "line one\nline | two"
    md = to_markdown(events, {"prompt_hash": "p"})
    assert "n_end --> n_cal_s_gift" in md
    assert "#quot;No#quot; &amp; &lt;leaves&gt;" in md
    assert "line one line \\| two" in md


def test_force_extract_keeps_previous_picks(tmp_path, monkeypatch):
    import eden.__main__ as cli
    import eden.extract as extract

    monkeypatch.setattr(cli, "OUT", tmp_path / "mvp")
    monkeypatch.setattr(cli, "RUNTIME_LEDGER", tmp_path / "costs.jsonl")
    picks = [ev(1, 3, "a"), ev(2, 30, "b"), ev(3, 55, "c", focal=True)]
    monkeypatch.setattr(extract, "extract_events",
                        lambda book, count: extract.RunResult(picks, validate(picks, None, 3), 1,
                                                              {"output_tokens": 1}, 0.01, "m"))
    args = ["extract", "--from-memory", "--count", "3", "--force"]
    cli.main(args)
    data = json.loads((tmp_path / "mvp" / "events.json").read_text())
    data["events"][0]["user_verified"] = True
    (tmp_path / "mvp" / "events.json").write_text(json.dumps(data))
    cli.main(args)
    backups = list((tmp_path / "mvp").glob("events.*.json"))
    assert len(backups) == 1 and json.loads(backups[0].read_text())["events"][0]["user_verified"] is True
