"""Command line: python -m eden {extract,render,judge,portfolio,preview,publish}."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .stages import STAGES

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
# The readable home page lives in the private portfolio-drafts repo, so this repo can be public.
DRAFTS = "~/portfolio-drafts"


def drafts_page(args) -> Path:
    page = Path(args.drafts).expanduser() / "home.html"
    if not page.exists():
        raise SystemExit(f"Can't find {page}, the home page draft. Use --drafts PATH.")
    return page
RUNTIME_LEDGER = OUTPUT / "agent_runtime_costs.jsonl"


def cmd_extract(args) -> None:
    from .core.llm import MODEL, extract_events, prompt_hash
    from .core.pins import log_runtime_cost, pinned_hash, save_run

    stage = STAGES[args.stage]
    out_dir = OUTPUT / stage.NAME
    count = args.count or stage.DEFAULT_COUNT
    phash = prompt_hash(stage, count)
    if not args.force and pinned_hash(out_dir) == phash:
        print("Pinned picks already match this prompt; skipping the model call. Use --force to re-pick.")
        return

    result = extract_events(stage, count)
    meta = {
        "stage": stage.NAME,
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
    backup = save_run(out_dir, meta, result.items)
    if backup:
        print(f"Previous picks kept as {backup}")
    log_runtime_cost(RUNTIME_LEDGER, meta)

    print(f"{len(result.items)} events after {result.attempts} attempt(s); agent runtime cost ${result.cost_usd}")
    for line in result.report.errors:
        print(f"ERROR   {line}")
    for line in result.report.warnings:
        print(f"WARNING {line}")
    cmd_render(args)


def cmd_render(args) -> None:
    from .core.pins import load_run

    stage = STAGES[args.stage]
    out_dir = OUTPUT / stage.NAME
    events, meta = load_run(out_dir, stage.Event)
    written = stage.render(events, meta, out_dir)
    print("Wrote " + " and ".join(str(p) for p in written))


def cmd_judge(args) -> None:
    from .core.llm import MODEL
    from .core.pins import load_run, log_runtime_cost
    from .stages import m1
    from .stages.m1.judge import judge, judge_hash, judged_pool
    from .stages.m1.runs import save_judge_run

    out_dir = OUTPUT / m1.NAME
    if not (out_dir / "events.json").exists():
        raise SystemExit("No pool yet. Run `python -m eden extract --stage m1` first.")
    pool, pool_meta = load_run(out_dir, m1.Event)
    unchecked = sum(e.user_verified is None for e in pool)
    if unchecked:
        print(f"Note: {unchecked} pool event(s) are unchecked. Events you mark false later are dropped, "
              "which changes the judge's input, so runs made before that won't be compared with later ones.")
    events = judged_pool(pool)
    jhash = judge_hash(events)

    for n in range(1, args.runs + 1):
        result = judge(events)
        meta = {
            "stage": "m1-judge",
            "model": MODEL,
            "served_by": result.served_by,
            "judge_hash": jhash,
            "pool_prompt_hash": pool_meta.get("prompt_hash"),
            "attempts": result.attempts,
            "usage": result.usage,
            "cost_usd": result.cost_usd,
            "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "errors": result.report.errors,
        }
        path = save_judge_run(out_dir, meta, result.items)
        log_runtime_cost(RUNTIME_LEDGER, meta)
        kept = sum(v.keep for v in result.items)
        print(f"Run {n}/{args.runs}: kept {kept} of {len(events)} after {result.attempts} attempt(s); "
              f"agent runtime cost ${result.cost_usd}; saved {path.name}")
        for line in result.report.errors:
            print(f"ERROR   {line}")
    args.stage = m1.NAME
    cmd_render(args)


def cmd_portfolio(args) -> None:
    from .core.pins import load_run
    from .publish import splice_timeline

    mvp = STAGES["mvp"]  # the portfolio shows the MVP timeline for now
    events, _ = load_run(OUTPUT / mvp.NAME, mvp.Event)
    page = drafts_page(args)
    page.write_text(splice_timeline(page.read_text(), mvp.to_portfolio_timeline(events)))
    print(f"Updated the timeline in {page}; your writing around it is unchanged.")


def cmd_preview(args) -> None:
    import webbrowser

    from .publish import preview_page

    css = Path(args.site).expanduser() / "assets" / "css" / "site.css"
    if not css.exists():
        raise SystemExit(f"Can't find {css}, the site's stylesheet. Use --site PATH.")
    page = drafts_page(args)
    out = page.with_name("preview.html")
    out.write_text(preview_page(page.read_text(), css.read_text()))
    print(f"Wrote {out}")
    if not args.no_open:
        webbrowser.open(out.as_uri())


def cmd_publish(args) -> None:
    import getpass
    import subprocess

    from .publish import PLACEHOLDER, git, lock, lock_json, normalize, unlock

    site = Path(args.site).expanduser()
    page = drafts_page(args).read_text()
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
        print(f"Locked home.html into {site / '_data' / 'lock.json'}")
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

    stage_help = f"Which milestone to run: {', '.join(STAGES)} (default: mvp)"

    p = sub.add_parser("extract", help="Pick events with the model, validate them, pin them, then render")
    p.add_argument("--stage", choices=STAGES, default="mvp", help=stage_help)
    p.add_argument("--count", type=int, help="Number of events (default: the stage's own)")
    p.add_argument("--force", action="store_true", help="Re-pick even if pinned picks match")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("render", help="Redraw from the pinned events.json (no model call)")
    p.add_argument("--stage", choices=STAGES, default="mvp", help=stage_help)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("judge", help="M1: run the significance test over the pinned pool, several times")
    p.add_argument("--runs", type=int, default=5, help="How many independent judge runs (default: 5)")
    p.set_defaults(func=cmd_judge)

    drafts_help = f"Path to your portfolio-drafts repo (default: {DRAFTS})"

    p = sub.add_parser("portfolio", help="Refresh the timeline inside the home page draft (no model call)")
    p.add_argument("--drafts", default=DRAFTS, help=drafts_help)
    p.set_defaults(func=cmd_portfolio)

    p = sub.add_parser("preview", help="Open the home page draft styled like the site, before locking it")
    p.add_argument("--drafts", default=DRAFTS, help=drafts_help)
    p.add_argument("--site", default="~/yunweiliang.github.io", help="Path to your portfolio repo")
    p.add_argument("--no-open", action="store_true", help="Only write the file; don't open a browser")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("publish", help="Lock the home page draft with your passcode, then commit and push it")
    p.add_argument("--drafts", default=DRAFTS, help=drafts_help)
    p.add_argument("--site", default="~/yunweiliang.github.io", help="Path to your portfolio repo")
    p.add_argument("--message", default="Update locked home page", help="Commit message")
    p.add_argument("--no-push", action="store_true", help="Only write lock.json; don't commit or push")
    p.set_defaults(func=cmd_publish)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
