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
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
}


@dataclass
class RunResult:
    events: list
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
    return round(
        (usage["input_tokens"] * p["input"]
         + usage["cache_creation_input_tokens"] * p["cache_write"]
         + usage["cache_read_input_tokens"] * p["cache_read"]
         + usage["output_tokens"] * p["output"]) / 1_000_000,
        4,
    )


def _add_usage(total: dict, usage) -> None:
    for key in total:
        total[key] += getattr(usage, key, 0) or 0


def extract_events(stage, count: int, client: anthropic.Anthropic | None = None) -> RunResult:
    """Ask the model for `count` events in the stage's schema, repairing until the stage's checks pass."""
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": stage.TASK.format(count=count)}]
    usage = {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0}
    served_by = MODEL

    for attempt in range(1, MAX_REPAIRS + 2):
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            system=stage.SYSTEM,
            messages=messages,
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": strict_schema(stage.EventList)},
            },
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        _add_usage(usage, response.usage)
        served_by = response.model

        if response.stop_reason == "refusal":
            raise RuntimeError(f"Model declined the request: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Response hit max_tokens before finishing the event list.")

        text = next(b.text for b in response.content if b.type == "text")
        events = [stage.Event(**e.model_dump()) for e in stage.EventList.model_validate(json.loads(text)).events]
        report = stage.validate(events, count)
        if report.ok or attempt > MAX_REPAIRS:
            return RunResult(events, report, attempt, usage, cost_of(usage, served_by), served_by)

        # Append-only repair turn: keep the model's answer and tell it exactly what failed.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": "Your list failed these checks. Return the full corrected list of "
                       f"{count} events.\n- " + "\n- ".join(report.errors),
        })
    raise AssertionError("unreachable")
