"""The eval's own grader and scoring. No model calls: agent tries use a fake extract_events."""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
yaml = pytest.importorskip("yaml")

import runner  # noqa: E402
from eden.core.checks import Report  # noqa: E402
from eden.core.llm import RunResult  # noqa: E402

SPECS = yaml.safe_load((ROOT / "eval" / "checks.yaml").read_text())


def run(case, k=1, model="claude-opus-5-5"):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(1) as pool:
        return runner.run_case(case, SPECS, k, model, pool)


def test_every_check_in_yaml_has_a_grader_function_and_back():
    from grader import CHECKS
    assert set(SPECS["checks"]) == set(CHECKS)
    for names in SPECS["defaults"].values():
        assert set(names) <= set(CHECKS)


@pytest.mark.parametrize("name", ["devset.jsonl", "heldout-set.jsonl"])
def test_cases_are_well_formed(name):
    for case in runner.load_cases(ROOT / "eval" / "cases" / name):
        assert case["kind"] in ("regression", "capability")
        assert case["stage"] in ("mvp", "m0", "m1")
        assert set(case["input"]) & {"file", "events", "synthetic", "agent"}
        assert set(runner.check_names(case, SPECS)) <= set(SPECS["checks"])


@pytest.mark.parametrize("name", ["devset.jsonl", "heldout-set.jsonl"])
def test_regression_cases_pass_today(name):
    cases = [c for c in runner.load_cases(ROOT / "eval" / "cases" / name)
             if c["kind"] == "regression" and "agent" not in c["input"]]
    failing = {c["id"]: [ch for t in r.tries for ch in t.checks if ch.status != "pass" and ch.status != "skip"]
               for c in cases if not (r := run(c)).pass_hat_k}
    assert failing == {}


def test_escape_check_catches_unescaped_text(monkeypatch):
    m0 = importlib.import_module("eden.stages.m0.render")
    monkeypatch.setattr(m0.html, "escape", lambda s, quote=True: s)
    case = next(c for c in runner.load_cases(ROOT / "eval" / "cases" / "devset.jsonl") if c["id"] == "reg-m0-escapes-markup")
    checks = {c.name: c for c in run(case).tries[0].checks}
    assert checks["model_text_escaped"].status == "fail"
    assert checks["svg_well_formed"].status == "fail"
    assert checks["one_node_per_event"].problems == ["the SVG doesn't parse; see svg_well_formed"]


def test_pass_at_k_and_cost_over_agent_tries(monkeypatch):
    mvp = importlib.import_module("eden.stages.mvp")
    events, _ = importlib.import_module("eden.core.pins").load_run(ROOT / "output" / "mvp", mvp.Event)
    outcomes = iter([[], ["[x] broken"], []])  # try 2's picks fail the stage's own checks

    def fake_extract(stage, count, client=None, model=None):
        return RunResult(events, Report(errors=next(outcomes)), 1, {}, 0.25, model)

    monkeypatch.setattr(runner, "extract_events", fake_extract)
    monkeypatch.setattr(runner, "log_runtime_cost", lambda ledger, meta: None)
    r = run({"id": "a", "kind": "capability", "stage": "mvp", "input": {"agent": {}}}, k=3, model="claude-sonnet-5-5")
    assert (r.passes, r.pass_at_1, r.pass_at_k, r.pass_hat_k) == (2, 2 / 3, True, False)
    assert r.cost == (0.75, True)
    assert {t.served_by for t in r.tries} == {"claude-sonnet-5-5"}


def test_failed_agent_try_fails_and_leaves_cost_unknown(monkeypatch):
    def failing(stage, count, client=None, model=None):
        raise RuntimeError("API down")

    monkeypatch.setattr(runner, "extract_events", failing)
    r = run({"id": "a", "kind": "capability", "stage": "mvp", "input": {"agent": {}}}, k=2)
    assert r.passes == 0 and r.cost == (0, False)
    assert r.tries[0].error == "RuntimeError: API down"


def test_cost_is_unavailable_for_tokens_without_a_price():
    from eden.core.llm import cost_of
    usage = {"input_tokens": 1_000_000, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
             "output_tokens": 1_000_000}
    assert cost_of(usage, "claude-haiku-5-5") == 0.6
    assert cost_of({**usage, "cache_read_input_tokens": 10}, "claude-haiku-5-5") is None  # no cache-read price on file
    assert cost_of(usage, "some-unknown-model") is None
