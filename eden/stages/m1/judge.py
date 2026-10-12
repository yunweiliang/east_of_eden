"""The judge: the second M1 pass. It applies the significance test to every event in the pinned pool."""

from __future__ import annotations

import hashlib
import json

from ...core.llm import MODEL, RunResult, ask_with_repairs
from .graph import without
from .prompt import JUDGE_SYSTEM, JUDGE_TASK, JUDGE_VERSION
from .schema import Event, VerdictList
from .validate import validate_verdicts

# What the judge sees of each event. The rationale is left out on purpose: it is the proposer's own
# argument for keeping the event, and showing it would nudge the judge to agree.
SHOWN = ["id", "title", "chapter", "characters", "summary", "for_cal", "causes", "thread", "is_focal_event"]


def judged_pool(pool: list[Event]) -> list[Event]:
    """The events the judge rules on: the pool minus any the reader marked false, with paths bridged."""
    return without(pool, {e.id for e in pool if e.user_verified is False})


def judge_task(events: list[Event]) -> str:
    pool = json.dumps([e.model_dump(include=set(SHOWN)) for e in events], indent=1, ensure_ascii=False)
    return JUDGE_TASK.format(count=len(events), pool=pool)


def judge_hash(events: list[Event]) -> str:
    """Changes when anything the judge sees changes: its prompt, the model, or the events themselves.

    Runs with the same hash judged exactly the same input, so they can be compared for stability.
    """
    text = f"{JUDGE_VERSION}|{MODEL}|{JUDGE_SYSTEM}|{judge_task(events)}"
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def judge(events: list[Event], client=None) -> RunResult:
    """One judge run over `events` (already passed through judged_pool)."""
    return ask_with_repairs(
        JUDGE_SYSTEM, judge_task(events), VerdictList,
        parse=lambda answer: answer.verdicts,
        check=lambda verdicts: validate_verdicts(events, verdicts),
        redo=f"one verdict for each of the {len(events)} events",
        client=client,
    )
