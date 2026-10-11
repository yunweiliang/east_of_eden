import json
from types import SimpleNamespace

from conftest import FIXTURES
from eden.extract import extract_events, strict_schema
from eden.render import to_html, to_markdown
from eden.schema import Event, EventList
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
    assert set(item["required"]) == set(Event.model_fields)


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
        text = json.dumps({"events": [e.model_dump() for e in events]})
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
    assert "flowchart LR" in md and "e2 --> e3" in md
