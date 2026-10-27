"""The one non-deterministic step, shared by every stage: the model picks the events.

Each stage supplies its own prompt, schema and checks (see eden/stages/). This module only calls the model,
feeds check failures back as repair turns, and adds up the cost. The model works from its own knowledge of
the novel; no book text is sent.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass

import anthropic

from .checks import Report

MODEL = "claude-opus-5-5"
MAX_REPAIRS = 2

# USD per million tokens, Claude API first-party rates. Used to log the agent's own runtime spend.
# A rate left out is unknown: a run that used those tokens reports its cost as unavailable.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
    "claude-sonnet-5-5": {"input": 2.00, "cache_read": 0.20, "output": 10.00},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},  # prompts up to 100K tokens
    "claude-fable-5-1": {"input": 10.00, "cache_read": 0.25, "output": 50.00},
}
# Models that take the server-side refusal fallback ("default" routing). Haiku has none.
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


@dataclass
class RunResult:
    items: list  # the stage's events, or the judge's verdicts
    report: Report
    attempts: int
    usage: dict
    cost_usd: float | None
    served_by: str


def strict_schema(model_cls) -> dict:
    """Pydantic JSON schema with $defs inlined and additionalProperties=false, for structured outputs."""
    schema = model_cls.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            # Drop pydantic's "title" annotations, but not a property that happens to be named "title".
            out = {
                k: ({name: resolve(sub) for name, sub in v.items()} if k == "properties" else resolve(v))
                for k, v in node.items()
                if not (k == "title" and isinstance(v, str))
            }
            if out.get("type") == "object":
                out["additionalProperties"] = False
                out["required"] = list(out.get("properties", {}))
            return out
        if isinstance(node, list):
            return [resolve(n) for n in node]
        return node

    return resolve(schema)


def prompt_hash(stage, count: int) -> str:
    """Changes whenever the stage's prompt, its version or the model changes, so pinned picks go stale."""
    text = f"{stage.PROMPT_VERSION}|{MODEL}|{stage.SYSTEM}|{stage.TASK.format(count=count)}"
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def cost_of(usage: dict, model: str) -> float | None:
    p = PRICES.get(model)
    if p is None:
        return None
    rates = {"input_tokens": "input", "cache_creation_input_tokens": "cache_write",
             "cache_read_input_tokens": "cache_read", "output_tokens": "output"}
    if any(usage[k] and rate not in p for k, rate in rates.items()):
        return None  # tokens of a kind we have no price for
    return round(sum(usage[k] * p.get(rate, 0) for k, rate in rates.items()) / 1_000_000, 4)


def _add_usage(total: dict, usage) -> None:
    for key in total:
        total[key] += getattr(usage, key, 0) or 0


def ask_with_repairs(system: str, task: str, list_cls, parse, check, redo: str,
                     client: anthropic.Anthropic | None = None, model: str = MODEL) -> RunResult:
    """Ask for a structured list, then repair it until `check` passes or the repairs run out.

    parse turns the validated `list_cls` answer into the items to keep; check(items) returns a Report;
    redo is what to ask for in a repair turn ("the full corrected list of 20 events").
    """
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": task}]
    usage = {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0}
    served_by = model
    fallback = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"} if model in FALLBACK_MODELS else {}

    for attempt in range(1, MAX_REPAIRS + 2):
        with client.beta.messages.stream(
            model=model,
            max_tokens=64000,
            system=system,
            messages=messages,
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": strict_schema(list_cls)},
            },
            **fallback,
        ) as stream:
            response = stream.get_final_message()
        _add_usage(usage, response.usage)
        served_by = response.model

        if response.stop_reason == "refusal":
            raise RuntimeError(f"Model declined the request: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Response hit max_tokens before finishing the list.")

        text = next(b.text for b in response.content if b.type == "text")
        items = parse(list_cls.model_validate(json.loads(text)))
        report = check(items)
        if report.ok or attempt > MAX_REPAIRS:
            return RunResult(items, report, attempt, usage, cost_of(usage, served_by), served_by)

        # Append-only repair turn: keep the model's answer and tell it exactly what failed.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": f"Your list failed these checks. Return {redo}.\n- " + "\n- ".join(report.errors),
        })
    raise AssertionError("unreachable")


def extract_events(stage, count: int, client: anthropic.Anthropic | None = None, model: str = MODEL) -> RunResult:
    """Ask the model for `count` events in the stage's schema, repairing until the stage's checks pass."""
    return ask_with_repairs(
        stage.SYSTEM, stage.TASK.format(count=count), stage.EventList,
        parse=lambda answer: [stage.Event(**e.model_dump()) for e in answer.events],
        check=lambda events: stage.validate(events, count),
        redo=f"the full corrected list of {count} events",
        client=client,
        model=model,
    )
