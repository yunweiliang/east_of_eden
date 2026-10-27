"""Runs the visualization eval: k tries per case, graded by eval/grader.py, scored as pass@1, pass@k and pass^k.

    python eval/runner.py                          # dev set, fixed inputs only (free)
    python eval/runner.py --with-agent -k 5        # also run the agent 5 times per agent case (API spend)
    python eval/runner.py heldout --model MODEL_ID --with-agent -k 3

A case either renders a fixed set of events (input.file, input.events, input.synthetic) or has the agent
pick fresh events in every try (input.agent), with --model. Fixed inputs render the same way every time, so
their k tries agree; agent tries vary, which is what pass@k and pass^k measure.

Tune on the dev set. The held-out set reports totals only (add --details to see its cases), so it stays a
check on whether a change generalizes rather than a second set to tune against.

Each run is archived to output/eval/<set>/run.<timestamp>.json; agent spend is also appended to
output/agent_runtime_costs.jsonl. Exits non-zero when a regression case fails any try.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import random
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eden.core.llm import MODEL, PRICES, extract_events  # noqa: E402
from eden.core.pins import log_runtime_cost  # noqa: E402
from eden.stages import STAGES  # noqa: E402

from grader import CheckResult, Rendered, grade  # noqa: E402

EVAL = Path(__file__).resolve().parent
CASES = EVAL / "cases"
SETS = {"dev": CASES / "devset.jsonl", "heldout": CASES / "heldout-set.jsonl"}
OUTPUT = ROOT / "output" / "eval"
RUNTIME_LEDGER = ROOT / "output" / "agent_runtime_costs.jsonl"
WORDS = ("ledger salinas valley lettuce brothel shotgun willow thanksgiving ranch laudanum gift "
         "fortune telegram twins mother blessing father brother train orchard").split()


# --- Building a case's events --------------------------------------------------------------------

def complete(raw: dict, i: int, n: int, stage) -> object:
    """An event from a case, with every field the case leaves out filled with a harmless default."""
    base = {"id": f"e{i}", "title": f"Event {i}", "chapter": 1 + i * 54 // max(n - 1, 1), "characters": [],
            "summary": f"What happens in event {i}.", "citation": "a short phrase", "rationale": "Leads on.",
            "is_focal_event": i == n - 1}
    if stage.NAME != "mvp":
        base |= {"causes": [], "thread": "Trask"}
    if stage.NAME == "m1":
        base["for_cal"] = "Cal feels it."
    return stage.Event.model_validate(base | raw)


def synthetic(spec: dict, stage) -> list:
    """A generated graph: n events spread over threads, linked by a named pattern. Seeded, so repeatable.

    links: "chain" (each event causes the next), "per_thread" (each thread is a chain, and every thread's
    last event feeds the reveal), "dense" (per_thread plus up to `extra` random earlier causes) or "none".
    """
    rng = random.Random(spec.get("seed", 0))
    n, threads = spec["n"], spec.get("threads", ["Trask"])
    raws = []
    for i in range(n):
        thread = threads[i % len(threads)]
        words = spec.get("title_words")
        title = " ".join(rng.choice(WORDS) for _ in range(words)).capitalize() if words else f"{thread} event {i}"
        raws.append({"title": spec.get("title", title).format(i=i, thread=thread), "thread": thread})
    raws[-1]["thread"] = spec.get("focal_thread", "Trask")

    links = spec.get("links", "per_thread")
    for i, raw in enumerate(raws):
        if links == "chain" and i:
            raw["causes"] = [f"e{i - 1}"]
        elif links in ("per_thread", "dense") and i:
            earlier = [j for j in range(i) if raws[j]["thread"] == raw["thread"]]
            raw["causes"] = [f"e{earlier[-1]}"] if earlier else []
            if links == "dense":
                pick = rng.sample(range(i), min(spec.get("extra", 2), i))
                raw["causes"] = list(dict.fromkeys(raw["causes"] + [f"e{j}" for j in pick]))
    if links in ("per_thread", "dense") and n > 1:  # every thread's last event feeds the reveal
        last = {raws[j]["thread"]: j for j in range(n - 1)}
        raws[-1]["causes"] = list(dict.fromkeys(raws[-1].get("causes", []) + [f"e{j}" for j in last.values()]))
    if stage.NAME == "mvp":
        for raw in raws:
            raw.pop("causes", None), raw.pop("thread", None)
    return [complete(raw, i, n, stage) for i, raw in enumerate(raws)]


def mutate(events: list, edits: list[dict]) -> list:
    """Edits a case applies to its events: {"event": index or "all", "field": ..., "set" or "append": ...}."""
    events = [e.model_copy(deep=True) for e in events]
    for edit in edits:
        targets = events if edit.get("event", "all") == "all" else [events[edit["event"]]]
        for e in targets:
            old = getattr(e, edit["field"])
            setattr(e, edit["field"], edit["set"] if "set" in edit else old + edit["append"])
    return events


def fixed_events(case: dict, stage) -> tuple[list, dict, Path | None]:
    """The events, meta and output folder a fixed-input case renders from."""
    src = case["input"]
    if "file" in src:
        path = ROOT / src["file"]
        data = json.loads(path.read_text())
        events = [stage.Event.model_validate(e) for e in data["events"]]
        meta, out_dir = data.get("meta", {}), path.parent
    elif "events" in src:
        events = [complete(raw, i, len(src["events"]), stage) for i, raw in enumerate(src["events"])]
        meta, out_dir = {"prompt_hash": "eval"}, None
    else:
        events, meta, out_dir = synthetic(src["synthetic"], stage), {"prompt_hash": "eval"}, None
    return mutate(events, src.get("mutate", [])), meta, out_dir


# --- Rendering -----------------------------------------------------------------------------------

def blanked(events: list) -> list:
    """The events with every model-written text field replaced, so a render shows only the template's markup."""
    fields = [f for f in ("title", "summary", "citation", "rationale", "for_cal") if f in type(events[0]).model_fields] if events else []
    return [e.model_copy(update={**{f: "x" for f in fields}, "characters": ["x"]}) for e in events]


def render(stage, events: list, meta: dict, out_dir: Path | None) -> Rendered:
    """Everything the stage's renderers produce, built in memory (stage.render() would write files).

    Renders twice, to check that the same input gives the same output.
    """
    def once(events: list) -> Rendered:
        if stage.NAME == "mvp":
            m = importlib.import_module("eden.stages.mvp.render")
            return Rendered("mvp", events, events, m.to_svg(events), m.to_html(events, meta), m.to_mermaid(events),
                            {"markdown": m.to_markdown(events, meta), "portfolio": m.to_portfolio_timeline(events)},
                            mermaid_nodes=len(events), mermaid_edges=max(len(events) - 1, 0))
        if stage.NAME == "m0":
            m = importlib.import_module("eden.stages.m0.render")
            ids = {e.id for e in events}
            return Rendered("m0", events, events, m.to_svg(events), m.to_html(events, meta), m.to_mermaid(events),
                            {"markdown": m.to_markdown(events, meta)}, mermaid_nodes=len(events),
                            mermaid_edges=sum(c in ids for e in events for c in e.causes))
        from eden.stages.m0.render import to_svg
        m = importlib.import_module("eden.stages.m1.render")  # the package's render() shadows the module
        with tempfile.TemporaryDirectory() as tmp:  # no judge runs: every candidate is drawn
            s = m.Summary(events, out_dir or Path(tmp))
            ids = {e.id for e in s.judged}
            return Rendered("m1", s.kept_graph, s.pool, to_svg(s.kept_graph), m.to_html(s, meta), m.to_mermaid(s),
                            {"markdown": m.to_markdown(s, meta)}, mermaid_nodes=len(s.judged),
                            mermaid_edges=sum(c in ids for e in s.judged for c in e.causes))

    first, second = once(events), once(events)
    first.stable = first.outputs() == second.outputs()
    first.blank = once(blanked(events)).outputs()
    return first


# --- Running cases -------------------------------------------------------------------------------

@dataclass
class Try:
    passed: bool
    checks: list[CheckResult]
    cost_usd: float | None = 0.0
    served_by: str | None = None
    error: str | None = None


@dataclass
class CaseResult:
    id: str
    kind: str
    stage: str
    source: str  # "fixed" or "agent"
    tries: list[Try] = field(default_factory=list)

    @property
    def passes(self) -> int:
        return sum(t.passed for t in self.tries)

    @property
    def pass_at_1(self) -> float:
        return self.passes / len(self.tries)

    @property
    def pass_at_k(self) -> bool:
        return self.passes > 0

    @property
    def pass_hat_k(self) -> bool:
        return self.passes == len(self.tries)

    @property
    def cost(self) -> tuple[float, bool]:
        """Total spend over the tries, and whether every try's cost was known."""
        known = [t.cost_usd for t in self.tries if t.cost_usd is not None]
        return round(sum(known), 4), len(known) == len(self.tries)


def check_names(case: dict, specs: dict) -> list[str]:
    names = case.get("checks") or specs["defaults"][case["stage"]]
    return [n for n in names if n not in case.get("skip", [])]


def run_try(case: dict, specs: dict, model: str) -> Try:
    stage = STAGES[case["stage"]]
    names = check_names(case, specs)
    cost, served_by, stage_errors = 0.0, None, None
    try:
        if "agent" in case["input"]:
            count = case["input"]["agent"].get("count", stage.DEFAULT_COUNT)
            result = extract_events(stage, count, model=model)
            events, cost, served_by = result.items, result.cost_usd, result.served_by
            stage_errors = result.report.errors
            meta = {"created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "stage": f"eval-{stage.NAME}", "served_by": served_by, "attempts": result.attempts,
                    "usage": result.usage, "cost_usd": cost, "prompt_hash": "eval"}
            log_runtime_cost(RUNTIME_LEDGER, meta)
            out_dir = None
        else:
            events, meta, out_dir = fixed_events(case, stage)
        rendered = render(stage, events, meta, out_dir)
    except Exception as err:  # an API error or a crash in a renderer fails the try, not the run
        return Try(False, [], None if "agent" in case["input"] else 0.0, served_by, f"{type(err).__name__}: {err}")
    rendered.expect = case.get("expect", {})
    rendered.stage_errors = stage_errors
    checks = grade(rendered, names, specs["checks"], case.get("params"))
    return Try(all(c.status in ("pass", "skip") for c in checks), checks, cost, served_by)


def run_case(case: dict, specs: dict, k: int, model: str, pool: ThreadPoolExecutor) -> CaseResult:
    source = "agent" if "agent" in case["input"] else "fixed"
    tries = list(pool.map(lambda _: run_try(case, specs, model), range(k)))
    return CaseResult(case["id"], case["kind"], case["stage"], source, tries)


def load_cases(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip() and not line.startswith("//")]
    ids = [c["id"] for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"Duplicate case ids in {path.name}: {', '.join(sorted(dupes))}")
    return cases


# --- Reporting -----------------------------------------------------------------------------------

def money(cost: float, complete: bool) -> str:
    return f"${cost:.4f}" + ("" if complete else " + unavailable")


def summary_rows(results: list[CaseResult]) -> list[tuple[str, int, float, float, float, float, bool]]:
    rows = []
    for kind in ("regression", "capability", "all"):
        group = [r for r in results if kind == "all" or r.kind == kind]
        if not group:
            continue
        n = len(group)
        costs = [r.cost for r in group]
        rows.append((kind, n, sum(r.pass_at_1 for r in group) / n, sum(r.pass_at_k for r in group) / n,
                     sum(r.pass_hat_k for r in group) / n, round(sum(c for c, _ in costs), 4),
                     all(ok for _, ok in costs)))
    return rows


def print_report(results: list[CaseResult], k: int, details: bool) -> None:
    if details:
        print(f"{'case':38} {'kind':10} {'src':5} {'pass':>6} {'p@1':>5} {'p@k':>4} {'p^k':>4}  cost")
        for r in results:
            cost, ok = r.cost
            print(f"{r.id:38} {r.kind:10} {r.source:5} {r.passes:>3}/{len(r.tries):<2} {r.pass_at_1:5.2f} "
                  f"{'yes' if r.pass_at_k else 'no':>4} {'yes' if r.pass_hat_k else 'no':>4}  {money(cost, ok)}")
            for i, t in enumerate(r.tries, 1):
                if t.error:
                    print(f"    try {i}: ERROR {t.error}")
                for c in t.checks:
                    if c.status in ("fail", "error"):
                        print(f"    try {i}: {c.status.upper()} {c.name}: " + "; ".join(c.problems))
                if len(r.tries) > 1 and r.source == "fixed":
                    break  # fixed inputs fail the same way every try
        print()
    print(f"k = {k} tries per case")
    print(f"{'set':12} {'cases':>5} {'pass@1':>7} {'pass@k':>7} {'pass^k':>7}  cost")
    for kind, n, p1, pk, phk, cost, ok in summary_rows(results):
        print(f"{kind:12} {n:>5} {p1:7.2f} {pk:7.2f} {phk:7.2f}  {money(cost, ok)}")


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def save(results: list[CaseResult], args, created: str) -> Path:
    folder = OUTPUT / args.set
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"run.{created.replace(':', '')}.json"
    meta = {"created": created, "set": args.set, "model": args.model, "k": args.k, "with_agent": args.with_agent,
            "commit": git_commit(),
            "summary": [dict(zip(("kind", "cases", "pass@1", "pass@k", "pass^k", "cost_usd", "cost_complete"), row))
                        for row in summary_rows(results)]}
    cases = [{**asdict(r), "pass@1": r.pass_at_1, "pass@k": r.pass_at_k, "pass^k": r.pass_hat_k,
              "cost_usd": r.cost[0], "cost_complete": r.cost[1]} for r in results]
    path.write_text(json.dumps({"meta": meta, "cases": cases}, indent=2) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("set", nargs="?", default="dev", choices=[*SETS, "all"])
    ap.add_argument("--model", default=MODEL, help=f"model for agent cases (default {MODEL})")
    ap.add_argument("-k", type=int, default=1, help="tries per case (default 1)")
    ap.add_argument("--with-agent", action="store_true", help="run agent cases too; each try calls the API")
    ap.add_argument("--kind", choices=["regression", "capability"], help="only this kind of case")
    ap.add_argument("--case", action="append", help="only this case id (repeatable)")
    ap.add_argument("--details", action="store_true", help="per-case results, also for the held-out set")
    ap.add_argument("--workers", type=int, default=4, help="tries run in parallel (default 4)")
    ap.add_argument("--no-save", action="store_true", help="don't archive the run")
    args = ap.parse_args(argv)
    if args.k < 1:
        ap.error("-k must be at least 1")

    specs = yaml.safe_load((EVAL / "checks.yaml").read_text())
    sets = list(SETS) if args.set == "all" else [args.set]
    cases = [c for s in sets for c in load_cases(SETS[s])]
    cases = [c for c in cases if (not args.kind or c["kind"] == args.kind) and (not args.case or c["id"] in args.case)]
    agent = [c for c in cases if "agent" in c["input"]]
    if agent and not args.with_agent:
        print(f"Skipping {len(agent)} agent case(s); add --with-agent to run them (API spend).")
        cases = [c for c in cases if c not in agent]
    if not cases:
        raise SystemExit("No cases to run.")
    if agent and args.with_agent:
        priced = "" if args.model in PRICES else " (no price on file for this model: cost will read unavailable)"
        print(f"Running {len(agent)} agent case(s) x {args.k} tries on {args.model}{priced}.")

    created = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = [run_case(c, specs, args.k, args.model, pool) for c in cases]

    print_report(results, args.k, details=args.details or args.set == "dev")
    if not args.no_save:
        print(f"\nSaved {save(results, args, created).relative_to(ROOT)}")
    broken = [r.id for r in results if r.kind == "regression" and not r.pass_hat_k]
    if broken:
        print(f"\nRegression failed: {', '.join(broken)}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
