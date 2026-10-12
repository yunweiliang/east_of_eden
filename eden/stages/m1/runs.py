"""Judge runs and the reader's reference set, stored next to the pinned pool in output/m1/.

Each judge run is its own file in output/m1/judge/, never overwritten, so runs pile up and can be
compared. The reference set is the reader's own list of significant events, written before the first run.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .schema import Verdict


class JudgeRun(BaseModel):
    meta: dict
    verdicts: list[Verdict]


class ReferenceEvent(BaseModel):
    title: str
    chapter: int | None = None  # the reader may add it later, after checking their copy
    pool_id: str | None = None  # filled in by the reader once the pool exists; null if the pool lacks it


def save_judge_run(out_dir: Path, meta: dict, verdicts: list[Verdict]) -> Path:
    folder = out_dir / "judge"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"run.{meta['created'].replace(':', '')}.json"
    n = 1
    while path.exists():  # two runs in the same second
        n += 1
        path = folder / f"run.{meta['created'].replace(':', '')}-{n}.json"
    path.write_text(json.dumps({"meta": meta, "verdicts": [v.model_dump() for v in verdicts]}, indent=2) + "\n")
    return path


def load_judge_runs(out_dir: Path, judge_hash: str) -> list[JudgeRun]:
    """The runs that judged exactly this input, oldest first. Runs on an older pool or prompt are skipped."""
    runs = [JudgeRun.model_validate_json(p.read_text()) for p in sorted((out_dir / "judge").glob("run.*.json"))]
    return [r for r in runs if r.meta.get("judge_hash") == judge_hash]


def load_reference(out_dir: Path) -> list[ReferenceEvent] | None:
    path = out_dir / "reference.json"
    if not path.exists():
        return None
    return [ReferenceEvent.model_validate(e) for e in json.loads(path.read_text())["events"]]
