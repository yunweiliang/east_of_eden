"""Command line: python -m eden {extract,render}."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .schema import Event

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "mvp"
RUNTIME_LEDGER = ROOT / "output" / "agent_runtime_costs.jsonl"


def cmd_extract(args) -> None:
    from .extract import MODEL, extract_events, prompt_hash

    events_path = OUT / "events.json"
    phash = prompt_hash(args.count)
    if events_path.exists() and not args.force:
        meta = json.loads(events_path.read_text())["meta"]
        if meta["prompt_hash"] == phash:
            print("Pinned picks already match this prompt; skipping the model call. Use --force to re-pick.")
            return

    result = extract_events(args.count)
    meta = {
        "stage": "mvp",
        "model": MODEL,
        "served_by": result.served_by,
        "prompt_hash": phash,
        "grounding": "memory",
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


def cmd_portfolio(args) -> None:
    from .render import splice_timeline, to_portfolio_timeline

    data = json.loads((OUT / "events.json").read_text())
    events = [Event.model_validate(e) for e in data["events"]]
    page = ROOT / "portfolio" / "home.html"
    page.write_text(splice_timeline(page.read_text(), to_portfolio_timeline(events)))
    print(f"Updated the timeline in {page}; your writing around it is unchanged.")


def cmd_publish(args) -> None:
    import getpass
    import subprocess

    from .publish import PLACEHOLDER, git, lock, lock_json, normalize, unlock

    site = Path(args.site).expanduser()
    page = (ROOT / "portfolio" / "home.html").read_text()
    if not (site / "_data" / "lock.json").exists():
        raise SystemExit(f"{site} doesn't look like the portfolio repo (no _data/lock.json). Use --site PATH.")
    if PLACEHOLDER in page:
        print(f"Note: the page still contains the placeholder {PLACEHOLDER!r}.")

    passcode = getpass.getpass("Passcode: ")
    if not normalize(passcode):
        raise SystemExit("No passcode typed; nothing changed.")
    if normalize(getpass.getpass("Passcode again: ")) != normalize(passcode):
        raise SystemExit("The two passcodes don't match; nothing changed.")

    data = lock(page, passcode)
    if unlock(data, passcode) != page:  # never publish a lock that can't be opened
        raise SystemExit("Round-trip check failed; nothing changed.")

    try:
        git(site, "pull", "--no-rebase", "--no-edit")
        (site / "_data" / "lock.json").write_text(lock_json(data))
        print(f"Locked portfolio/home.html into {site / '_data' / 'lock.json'}")
        if args.no_push:
            print("--no-push: not committing. Review with `git diff` in the portfolio folder.")
            return
        git(site, "add", "_data/lock.json")
        git(site, "commit", "-m", args.message)
        git(site, "push")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"git stopped with an error (see above): {' '.join(e.cmd)}")
    print("Published. The site updates in a minute or two.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eden")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("extract", help="Pick events with the model, validate them, pin them, then render")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--force", action="store_true", help="Re-pick even if pinned picks match")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("render", help="Redraw the timeline from the pinned events.json (no model call)")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("portfolio", help="Refresh the timeline inside portfolio/home.html (no model call)")
    p.set_defaults(func=cmd_portfolio)

    p = sub.add_parser("publish", help="Lock portfolio/home.html with your passcode, then commit and push it")
    p.add_argument("--site", default="~/yunweiliang.github.io", help="Path to your portfolio repo")
    p.add_argument("--message", default="Update locked home page", help="Commit message")
    p.add_argument("--no-push", action="store_true", help="Only write lock.json; don't commit or push")
    p.set_defaults(func=cmd_publish)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
