"""Grades rendered plot lines against the checks in eval/checks.yaml. Deterministic: no model is called.

Each check is a function with the same name as its entry in checks.yaml. It takes the rendered output and
the check's params and returns a list of problems; an empty list is a pass. A check that doesn't apply to
a case (an M0 lane check on an MVP timeline) raises NotApplicable and is reported as skipped.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field

from eden.stages.m0.render import LANE, THREADS

SVG = "{http://www.w3.org/2000/svg}"
MAX_PROBLEMS = 5  # problems listed per failed check; the rest are counted

# Font sizes from each renderer's CSS (eden/stages/*/render.py), used to estimate label sizes.
FONT_PX = {
    "mvp": {"title": 14, "chap": 12},
    "m0": {"title": 13, "chap": 11, "lane-name": 13},
    "m1": {"title": 13, "chap": 11, "lane-name": 13},
}
MODEL_FIELDS = ("title", "summary", "citation", "rationale", "for_cal")
NARROW, WIDE = set("iljtf.,;:'!|() "), set("mwMW@")


def text_width(text: str, size: float, w: dict) -> float:
    """Estimated rendered width of a label: a width per character class, as a fraction of the font size."""
    return size * sum(w["narrow"] if c in NARROW else w["wide"] if c in WIDE else w["capital"] if c.isupper()
                      else w["other"] for c in text)


class NotApplicable(Exception):
    pass


@dataclass
class Rendered:
    """Everything one case's render produced, plus what the runner expects to see in it."""

    stage: str
    drawn: list           # events drawn in the SVG, in story order
    table: list           # events listed in the HTML table (for M1, the whole pool)
    svg: str
    html: str
    mermaid: str
    extra: dict[str, str] = field(default_factory=dict)  # other outputs: markdown, portfolio snippet
    mermaid_nodes: int = 0
    mermaid_edges: int = 0
    stable: bool = True   # rendering twice gave identical output
    expect: dict = field(default_factory=dict)
    stage_errors: list[str] | None = None  # the stage's own validate() errors, for picks the agent made
    blank: dict[str, str] = field(default_factory=dict)  # the same render with every model text field blanked

    def outputs(self) -> dict[str, str]:
        return {"svg": self.svg, "html": self.html, "mermaid": self.mermaid, **self.extra}


@dataclass
class CheckResult:
    name: str
    status: str  # "pass", "fail", "skip" or "error"
    problems: list[str] = field(default_factory=list)


# --- Reading the SVG -------------------------------------------------------------------------------

@dataclass
class Text:
    x: float
    y: float
    cls: str
    text: str
    anchor: str = "middle"


@dataclass
class Node:
    cx: float
    cy: float
    r: float
    cls: str
    hover: str
    texts: list[Text]


@dataclass
class Edge:
    points: list[tuple[float, float]]  # M point, then the control points and end of one segment
    cls: str
    hover: str

    @property
    def start(self) -> tuple[float, float]:
        return self.points[0]

    @property
    def end(self) -> tuple[float, float]:
        return self.points[-1]

    def sample(self, n: int) -> list[tuple[float, float]]:
        """n + 1 points along the line or cubic curve, ends included."""
        pts = self.points
        out = []
        for i in range(n + 1):
            t = i / n
            if len(pts) == 2:
                (x0, y0), (x1, y1) = pts
                out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            else:
                (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
                a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t ** 2 * (1 - t), t ** 3
                out.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))
        return out


@dataclass
class Lane:
    name: str
    y: float
    height: float


@dataclass
class ParsedSvg:
    width: float
    height: float
    nodes: list[Node]
    edges: list[Edge]
    lanes: list[Lane]
    lane_names: list[Text]


def _texts(el) -> list[Text]:
    return [Text(float(t.get("x")), float(t.get("y")), t.get("class", ""), t.text or "",
                 "start" if "lane-name" in t.get("class", "") else "middle")
            for t in el.iter(SVG + "text")]


def parse_svg(svg: str) -> ParsedSvg:
    root = ET.fromstring(svg)
    if root.tag != SVG + "svg":
        raise ValueError(f"root element is <{root.tag}>, not <svg>")
    _, _, width, height = (float(v) for v in root.get("viewBox").split())

    nodes = []
    for g in root.iter(SVG + "g"):
        circle = g.find(SVG + "circle")
        if circle is None:
            continue
        title = g.find(SVG + "title")
        nodes.append(Node(float(circle.get("cx")), float(circle.get("cy")), float(circle.get("r")),
                          circle.get("class", ""), title.text if title is not None else "", _texts(g)))

    edges = []
    for p in root.iter(SVG + "path"):
        if "edge" not in p.get("class", "").split():
            continue
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", p.get("d"))]
        title = p.find(SVG + "title")
        edges.append(Edge(list(zip(nums[::2], nums[1::2])), p.get("class", ""), title.text if title is not None else ""))

    rects = [r for r in root.iter(SVG + "rect") if r.get("class", "").startswith("lane")]
    names = [t for t in _texts(root) if "lane-name" in t.cls]
    lanes = [Lane(n.text, float(r.get("y")), float(r.get("height"))) for r, n in zip(rects, names)]
    return ParsedSvg(width, height, nodes, edges, lanes, names)


def classes(cls: str) -> set[str]:
    return set(cls.split())


# --- Checks --------------------------------------------------------------------------------------

def svg_well_formed(r: Rendered, p: dict) -> list[str]:
    try:
        parse_svg(r.svg)
    except (ET.ParseError, ValueError, TypeError, AttributeError) as err:
        return [f"SVG doesn't parse: {err}"]
    return []


def one_node_per_event(r: Rendered, p: dict) -> list[str]:
    nodes = parse_svg(r.svg).nodes
    if len(nodes) != len(r.drawn):
        return [f"{len(nodes)} nodes drawn for {len(r.drawn)} events"]
    return [f"node {i + 1} hovers as '{n.hover[:40]}', expected event '{e.title[:40]}'"
            for i, (n, e) in enumerate(zip(nodes, r.drawn)) if not n.hover.startswith(e.title)]


def _paired(r: Rendered) -> list[tuple[Node, object]]:
    nodes = parse_svg(r.svg).nodes
    if len(nodes) != len(r.drawn):
        raise NotApplicable("node count is wrong; see one_node_per_event")
    return list(zip(nodes, r.drawn))


def focal_marked_once(r: Rendered, p: dict) -> list[str]:
    nodes = parse_svg(r.svg).nodes
    focal = [n for n in nodes if "focal" in classes(n.cls)]
    if len(focal) != 1:
        return [f"{len(focal)} nodes styled as the reveal, expected 1"]
    if focal[0].cx != max(n.cx for n in nodes):
        return ["the reveal is not the rightmost node"]
    return []


def time_runs_left_to_right(r: Rendered, p: dict) -> list[str]:
    nodes = parse_svg(r.svg).nodes
    return [f"node {i + 2} (x={b.cx:g}) is not right of node {i + 1} (x={a.cx:g})"
            for i, (a, b) in enumerate(zip(nodes, nodes[1:])) if b.cx <= a.cx]


def chapters_labeled(r: Rendered, p: dict) -> list[str]:
    return [f"[{e.id}] has no 'Ch. {e.chapter}' label" for n, e in _paired(r)
            if f"Ch. {e.chapter}" not in [t.text for t in n.texts]]


def hover_has_full_text(r: Rendered, p: dict) -> list[str]:
    out = []
    for n, e in _paired(r):
        if e.title not in n.hover:
            out.append(f"[{e.id}] hover lacks the full title")
        if e.summary not in n.hover:
            out.append(f"[{e.id}] hover lacks the full summary")
    return out


def _graph_only(r: Rendered) -> None:
    if r.stage == "mvp":
        raise NotApplicable("the MVP timeline has no arrows or lanes")


def _positions(r: Rendered) -> dict[str, tuple[float, float]]:
    return {e.id: (n.cx, n.cy) for n, e in _paired(r)}


def _close(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) < 0.5 and abs(a[1] - b[1]) < 0.5


def edges_match_causes(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    pos = _positions(r)
    expected = Counter((pos[c], pos[e.id]) for e in r.drawn for c in e.causes if c in pos)
    drawn = Counter((round(ed.start[0], 1), round(ed.start[1], 1), round(ed.end[0], 1), round(ed.end[1], 1))
                    for ed in parse_svg(r.svg).edges)
    want = Counter((round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1)) for (a, b) in expected.elements())
    by_pos = {(round(x, 1), round(y, 1)): i for i, (x, y) in pos.items()}
    out = [f"missing arrow {by_pos.get(k[:2], '?')} -> {by_pos.get(k[2:], '?')}" for k in (want - drawn).elements()]
    out += [f"extra arrow {by_pos.get(k[:2], '?')} -> {by_pos.get(k[2:], '?')}" for k in (drawn - want).elements()]
    return out


def edges_point_forward(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    return [f"arrow '{e.hover}' runs right to left" for e in parse_svg(r.svg).edges if e.start[0] >= e.end[0]]


def focal_edges_highlighted(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    focal = [pos for (n, e), pos in zip(_paired(r), _positions(r).values()) if e.is_focal_event]
    out = []
    for ed in parse_svg(r.svg).edges:
        into_focal = any(_close(ed.end, f) for f in focal)
        if into_focal != ("focal" in classes(ed.cls)):
            out.append(f"arrow '{ed.hover}' " + ("feeds the reveal but isn't highlighted" if into_focal
                                                 else "is highlighted but doesn't feed the reveal"))
    return out


def cross_lane_edges_dashed(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    out = []
    for ed in parse_svg(r.svg).edges:
        crosses = ed.start[1] != ed.end[1]
        if crosses != ("cross" in classes(ed.cls)):
            out.append(f"arrow '{ed.hover}' " + ("changes lanes but isn't dashed" if crosses
                                                 else "is dashed but stays in its lane"))
    return out


def lanes_match_threads(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    want = [t for t in THREADS if any(e.thread == t for e in r.drawn)]
    got = [t.text for t in parse_svg(r.svg).lane_names]
    return [] if got == want else [f"lanes are {got}, expected {want}"]


def node_in_its_lane(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    lanes = {lane.name: lane for lane in parse_svg(r.svg).lanes}
    out = []
    for n, e in _paired(r):
        lane = lanes.get(e.thread)
        if lane is None:
            out.append(f"[{e.id}] has no '{e.thread}' lane")
        elif not lane.y <= n.cy - n.r and n.cy + n.r <= lane.y + lane.height:
            out.append(f"[{e.id}] sits outside the '{e.thread}' lane")
    return out


@dataclass
class Box:
    x0: float
    y0: float
    x1: float
    y1: float
    owner: int     # which node the label belongs to; -1 for lane names
    text: str

    def overlaps(self, other: "Box", slack: float) -> bool:
        return (self.x0 < other.x1 - slack and other.x0 < self.x1 - slack
                and self.y0 < other.y1 - slack and other.y0 < self.y1 - slack)


def _boxes(r: Rendered, p: dict) -> list[Box]:
    sizes = FONT_PX[r.stage]
    svg = parse_svg(r.svg)
    labelled = [(i, t) for i, n in enumerate(svg.nodes) for t in n.texts] + [(-1, t) for t in svg.lane_names]
    out = []
    for owner, t in labelled:
        size = next((px for cls, px in sizes.items() if cls in classes(t.cls)), 13)
        w = text_width(t.text, size, p["char_width"])
        x0 = t.x if t.anchor == "start" else t.x - w / 2
        out.append(Box(x0, t.y - 0.8 * size, x0 + w, t.y + 0.25 * size, owner, t.text))
    return out


def labels_inside_canvas(r: Rendered, p: dict) -> list[str]:
    svg, slack = parse_svg(r.svg), p.get("slack", 2)
    return [f"label '{b.text}' runs past the {side} edge" for b in _boxes(r, p)
            for side, out in (("left", b.x0 < -slack), ("right", b.x1 > svg.width + slack),
                              ("top", b.y0 < -slack), ("bottom", b.y1 > svg.height + slack)) if out]


def labels_dont_overlap(r: Rendered, p: dict) -> list[str]:
    boxes, slack = _boxes(r, p), p.get("slack", 1)
    return [f"label '{a.text}' overlaps '{b.text}'" for i, a in enumerate(boxes) for b in boxes[i + 1:]
            if a.owner != b.owner and a.overlaps(b, slack)]


def edges_avoid_nodes(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    svg = parse_svg(r.svg)
    out = []
    for ed in svg.edges:
        ends = [n for n in svg.nodes if _close((n.cx, n.cy), ed.start) or _close((n.cx, n.cy), ed.end)]
        for n in svg.nodes:
            if n in ends:
                continue
            reach = n.r + p.get("clearance", 0)
            if any((x - n.cx) ** 2 + (y - n.cy) ** 2 < reach ** 2 for x, y in ed.sample(p.get("samples", 200))):
                out.append(f"arrow '{ed.hover}' passes through '{n.hover.split(' (ch.')[0]}'")
    return out


def edges_inside_canvas(r: Rendered, p: dict) -> list[str]:
    _graph_only(r)
    svg = parse_svg(r.svg)
    return [f"arrow '{ed.hover}' leaves the drawing" for ed in svg.edges
            if any(not (0 <= x <= svg.width and 0 <= y <= svg.height) for x, y in ed.sample(p.get("samples", 40)))]


def model_text_escaped(r: Rendered, p: dict) -> list[str]:
    out = []
    risky = {s for e in r.table + r.drawn for s in [*(getattr(e, f, "") for f in MODEL_FIELDS), *e.characters]
             if any(ch in s for ch in "<>&")}
    for name in ("svg", "html", "mermaid"):
        text, template = r.outputs()[name], r.blank.get(name, "")
        # More raw copies than the template alone has (a table's own "</td><td>") means model text got through.
        out += [f"{name} contains model text unescaped: '{s[:40]}'" for s in sorted(risky)
                if text.count(s) > template.count(s)]
        if "<script" in text.lower():
            out.append(f"{name} contains a <script> tag")
    return out


def mermaid_consistent(r: Rendered, p: dict) -> list[str]:
    lines = r.mermaid.splitlines()
    if lines[:2] != ["```mermaid", "flowchart LR"] or lines[-1] != "```":
        return ["not a ```mermaid flowchart LR block"]
    declared = re.findall(r'^\s*(n_\w+)\["', r.mermaid, re.M)
    edges = re.findall(r"^\s*(\S+) --> (\S+)$", r.mermaid, re.M)
    out = []
    dupes = sorted(k for k, v in Counter(declared).items() if v > 1)
    if dupes:
        out.append(f"node ids declared twice: {', '.join(dupes)}")
    if len(declared) != r.mermaid_nodes:
        out.append(f"{len(declared)} nodes declared, expected {r.mermaid_nodes}")
    if len(edges) != r.mermaid_edges:
        out.append(f"{len(edges)} edges, expected {r.mermaid_edges}")
    known = set(declared)
    out += [f"edge {a} --> {b} names an undeclared node" for a, b in edges if a not in known or b not in known]
    return out


def html_page_basics(r: Rendered, p: dict) -> list[str]:
    needs = {
        "a doctype": r.html.lower().startswith("<!doctype html>"),
        "a viewport meta tag": 'name="viewport"' in r.html,
        "a <title>": "<title>" in r.html,
        "a dark-mode palette": "prefers-color-scheme: dark" in r.html,
        "a sideways scroll for the plot": "overflow-x:auto" in r.html.replace(" ", ""),
    }
    return [f"page has no {what}" for what, ok in needs.items() if not ok]


def table_row_per_event(r: Rendered, p: dict) -> list[str]:
    body = re.search(r"<tbody>(.*?)</tbody>", r.html, re.S)
    rows = len(re.findall(r"<tr[ >]", body.group(1))) if body else 0
    return [] if rows == len(r.table) else [f"{rows} table rows for {len(r.table)} events"]


def no_html_comments(r: Rendered, p: dict) -> list[str]:
    return [f"{name} contains an HTML comment" for name, text in r.outputs().items() if "<!--" in text]


def stage_checks_pass(r: Rendered, p: dict) -> list[str]:
    if r.stage_errors is None:
        raise NotApplicable("only for events the agent picked in this run")
    return r.stage_errors


def deterministic(r: Rendered, p: dict) -> list[str]:
    return [] if r.stable else ["two renders of the same input differ"]


def measured_counts(r: Rendered) -> dict[str, int]:
    svg = parse_svg(r.svg)
    body = re.search(r"<tbody>(.*?)</tbody>", r.html, re.S)
    return {"nodes": len(svg.nodes), "edges": len(svg.edges), "lanes": len(svg.lane_names),
            "rows": len(re.findall(r"<tr[ >]", body.group(1))) if body else 0}


def expected_counts(r: Rendered, p: dict) -> list[str]:
    if not r.expect:
        raise NotApplicable("the case pins no counts")
    got = measured_counts(r)
    return [f"{k}: {got.get(k)} drawn, expected {v}" for k, v in r.expect.items() if got.get(k) != v]


CHECKS = {f.__name__: f for f in (
    svg_well_formed, one_node_per_event, focal_marked_once, time_runs_left_to_right, chapters_labeled,
    hover_has_full_text, edges_match_causes, edges_point_forward, focal_edges_highlighted,
    cross_lane_edges_dashed, lanes_match_threads, node_in_its_lane, labels_inside_canvas, labels_dont_overlap,
    edges_avoid_nodes, edges_inside_canvas, model_text_escaped, mermaid_consistent, html_page_basics,
    table_row_per_event, no_html_comments, stage_checks_pass, deterministic, expected_counts,
)}


def grade(r: Rendered, names: list[str], specs: dict, overrides: dict | None = None) -> list[CheckResult]:
    """Run the named checks on one render. Params come from checks.yaml, then the case's overrides."""
    results = []
    for name in names:
        spec = specs.get(name)
        if spec is None or name not in CHECKS:
            results.append(CheckResult(name, "error", [f"no check named '{name}'"]))
            continue
        if r.stage not in spec.get("stages", []):
            results.append(CheckResult(name, "skip", [f"doesn't apply to {r.stage}"]))
            continue
        params = {**spec.get("params", {}), **(overrides or {}).get(name, {})}
        try:
            problems = CHECKS[name](r, params)
        except NotApplicable as why:
            results.append(CheckResult(name, "skip", [str(why)]))
            continue
        except ET.ParseError:
            results.append(CheckResult(name, "fail", ["the SVG doesn't parse; see svg_well_formed"]))
            continue
        except Exception as err:  # a check that crashes is a finding too, not a reason to stop the run
            results.append(CheckResult(name, "error", [f"{type(err).__name__}: {err}"]))
            continue
        extra = len(problems) - MAX_PROBLEMS
        shown = problems[:MAX_PROBLEMS] + ([f"... and {extra} more"] if extra > 0 else [])
        results.append(CheckResult(name, "fail" if problems else "pass", shown))
    return results
