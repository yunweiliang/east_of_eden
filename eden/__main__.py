"""Command line: python -m eden {chapters,extract,render}."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .schema import Event
from .source import load_book

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "mvp"
RUNTIME_LEDGER = ROOT / "output" / "agent_runtime_costs.jsonl"


def find_source(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    candidates = sorted(p for p in (ROOT / "data" / "source").glob("*") if p.suffix.lower() in {".epub", ".txt"})
    if not candidates:
        sys.exit("No book found. Put your .epub or .txt in data/source/ (gitignored), pass --source, "
                 "or use `extract --from-memory`.")
    return candidates[0]


def cmd_chapters(args) -> None:
    book = load_book(find_source(args.source))
    print(f"{len(book.chapters)} chapters, sha256 {book.sha256[:12]}")
    for c in book.chapters:
        print(f"  ch {c.number:>2}: {len(c.text.split()):>6} words")


def cmd_extract(args) -> None:
    from .extract import MODEL, extract_events, prompt_hash

    if args.from_memory:
        book, source_id = None, "memory"
        print("Memory mode: the model works from its own knowledge of the novel. Verify each event yourself.")
    else:
        book = load_book(find_source(args.source))
        source_id = book.sha256
    events_path = OUT / "events.json"
    phash = prompt_hash(args.count, memory=book is None)
    if events_path.exists() and not args.force:
        meta = json.loads(events_path.read_text())["meta"]
        if meta["source_sha256"] == source_id and meta["prompt_hash"] == phash:
            print("Pinned picks already match this source and prompt; skipping the model call. Use --force to re-pick.")
            return

    result = extract_events(book, args.count)
    meta = {
        "stage": "mvp",
        "model": MODEL,
        "served_by": result.served_by,
        "prompt_hash": phash,
        "grounding": "memory" if book is None else "book",
        "source_sha256": source_id,
        "attempts": result.attempts,
        "usage": result.usage,
        "cost_usd": result.cost_usd,
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "errors": result.report.errors,
        "warnings": result.report.warnings,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    if events_path.exists():
        # Keep the previous picks (and any user_verified marks on them) instead of silently overwriting.
        stamp = json.loads(events_path.read_text())["meta"].get("created", "previous").replace(":", "")
        backup = events_path.with_name(f"events.{stamp}.json")
        events_path.rename(backup)
        print(f"Previous picks kept as {backup.name}")
    events_path.write_text(json.dumps({"meta": meta, "events": [e.model_dump() for e in result.events]}, indent=2) + "\n")
    with RUNTIME_LEDGER.open("a") as f:
        f.write(json.dumps({k: meta[k] for k in ("created", "stage", "served_by", "attempts", "usage", "cost_usd")}) + "\n")

    print(f"{len(result.events)} events after {result.attempts} attempt(s); agent runtime cost ${result.cost_usd}")
    for line in result.report.errors:
        print(f"ERROR   {line}")
    for line in result.report.warnings:
        print(f"WARNING {line}")
    cmd_render(args)


def cmd_render(args) -> None:
    from .render import to_html, to_markdown

    data = json.loads((OUT / "events.json").read_text())
    events = [Event.model_validate(e) for e in data["events"]]
    (OUT / "timeline.md").write_text(to_markdown(events, data["meta"]))
    (OUT / "timeline.html").write_text(to_html(events, data["meta"]))
    print(f"Wrote {OUT / 'timeline.md'} and {OUT / 'timeline.html'}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eden")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("chapters", help="Check that the book splits into chapters correctly")
    p.add_argument("--source")
    p.set_defaults(func=cmd_chapters)

    p = sub.add_parser("extract", help="Pick events with the model, validate them, pin them, then render")
    p.add_argument("--source")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--force", action="store_true", help="Re-pick even if pinned picks match")
    p.add_argument("--from-memory", action="store_true",
                   help="No book file: the model works from its own knowledge and you verify each event")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("render", help="Redraw the timeline from the pinned events.json (no model call)")
    p.set_defaults(func=cmd_render)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
