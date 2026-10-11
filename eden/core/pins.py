"""Reading and writing a stage's pinned run, output/<stage>/events.json, plus the runtime cost ledger."""

from __future__ import annotations

import json
from pathlib import Path


def load_run(out_dir: Path, event_cls) -> tuple[list, dict]:
    """The pinned events, parsed with the stage's own Event class, and the run's metadata."""
    data = json.loads((out_dir / "events.json").read_text())
    return [event_cls.model_validate(e) for e in data["events"]], data["meta"]


def pinned_hash(out_dir: Path) -> str | None:
    path = out_dir / "events.json"
    return json.loads(path.read_text())["meta"]["prompt_hash"] if path.exists() else None


def save_run(out_dir: Path, meta: dict, events: list) -> str | None:
    """Write a new pinned run. An existing one is renamed, never overwritten, so user_verified marks survive.

    Returns the backup's file name, if there was a previous run.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "events.json"
    backup = None
    if path.exists():
        stamp = json.loads(path.read_text())["meta"].get("created", "previous").replace(":", "")
        backup = path.with_name(f"events.{stamp}.json")
        path.rename(backup)
    path.write_text(json.dumps({"meta": meta, "events": [e.model_dump() for e in events]}, indent=2) + "\n")
    return backup.name if backup else None


def log_runtime_cost(ledger: Path, meta: dict) -> None:
    """Append the agent's own API spend for this run; it feeds the "Agent runtime" column in CHANGELOG.md."""
    with ledger.open("a") as f:
        f.write(json.dumps({k: meta[k] for k in ("created", "stage", "served_by", "attempts", "usage", "cost_usd")}) + "\n")
