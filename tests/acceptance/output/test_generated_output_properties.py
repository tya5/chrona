"""Properties every generated review SVG must satisfy, whatever its content.

These assert the document, not its bytes. A defect that reproduces deterministically
still fails here, which a byte comparison against a regenerated baseline cannot do.

Failures that exist today are pinned in ``known_failures.yaml`` so the gate can be
enforced before every defect behind it is fixed; see ``check`` for the rules.
"""
from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

from chrona.presentation.model.font_metrics import resolve_font_metrics

ROOT = Path(__file__).resolve().parents[3]
RESOURCES = ROOT / "src/chrona/resources"
KNOWN = yaml.safe_load((Path(__file__).parent / "known_failures.yaml").read_text(encoding="utf-8")) or {}
SVG = "{http://www.w3.org/2000/svg}"

MARK_PURPOSES = frozenset({"planned", "actual", "missingActual", "baseline", "milestone"})
# Text that is allowed inside the plot area by design, and so must clear the marks.
PLOT_TEXT_PURPOSES = frozenset({"member-label", "finish-delta", "as-of-label", "group-header"})
SLOT_PURPOSES = {
    "title": {"title-text"},
    "table": {"table-column-label", "table-cell"},
    "timeline": MARK_PURPOSES | {"dependency", "calendar-closed", "as-of"},
    "timeline-axis": {"axis-label", "axis-band", "axis-grid"},
    "notes": {"project-note"},
    "legend": {"legend-label", "legend-swatch"},
    "summary": {"summary-header", "summary-metric", "summary-figure-value", "summary-figure-caption"},
    "annotations": {"annotation-box", "annotation-text", "annotation-leader"},
}


def _slides():
    for manifest_path in sorted(ROOT.glob("examples/*/manifest.yaml")):
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        example = manifest_path.parent
        for slide in manifest.get("slides", ()):
            svg = example / str(slide["expectedSvg"])
            if not svg.is_file():
                continue
            identity = f"{example.name}/{slide['id']}"
            yield pytest.param(identity, example / str(slide.get("context", manifest["context"])), svg, id=identity)


SLIDES = list(_slides())
CASES = pytest.mark.parametrize("slide,context_path,svg_path", SLIDES)


def check(slide: str, request, actual: list | set, message: str) -> None:
    """Assert one property, honouring its complete pinned failure fingerprint.

    A pinned pair that still fails is reported as xfail rather than breaking the build.
    A pinned pair that starts passing fails, so a fix removes its pin in the same change.
    Any pair that is not pinned fails normally.
    """
    expected = (KNOWN.get(request.node.originalname or request.node.name) or {}).get(slide)
    normalized = sorted(actual) if isinstance(actual, set) else actual
    if not normalized:
        assert expected is None, f"{slide} now satisfies this property: remove it from known_failures.yaml"
        return
    assert expected is not None, message
    assert normalized == expected, f"{slide} failure fingerprint changed: {normalized!r}"
    if expected:
        pytest.xfail(message)


def _load(svg_path: Path, context_path: Path):
    tree = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
    body = yaml.safe_load(context_path.read_text(encoding="utf-8"))["body"]
    viewport = (float(body["environment"]["viewport"]["inlineSize"]),
                float(body["environment"]["viewport"]["blockSize"]))
    theme = _bound(context_path, body, "theme")
    stack = next(v["value"] for v in theme["body"]["values"].values() if v.get("type") == "fontFamily")
    weights = {int(v["value"]) for v in theme["body"]["values"].values() if v.get("type") == "fontWeight"}
    metrics = {weight: resolve_font_metrics(stack, body["environment"]["fontMetrics"], weight=weight, asset_root=RESOURCES)
               for weight in weights}
    return tree, viewport, metrics


def _bound(context_path: Path, body: dict, name: str) -> dict:
    return yaml.safe_load((context_path.parents[1] / body[name]["address"]).read_text(encoding="utf-8"))


def _marks(tree):
    for node in tree.iter(SVG + "rect"):
        if node.get("data-purpose") in MARK_PURPOSES:
            x, y = float(node.get("x")), float(node.get("y"))
            yield node.get("data-scene-id"), node.get("fill"), (x, y, x + float(node.get("width")), y + float(node.get("height")))


def _declared_slots(layout: dict) -> set[str]:
    """Return only slots whose authoring contract requires visible content."""
    required: set[str] = set()
    def visit(value):
        if isinstance(value, dict):
            source = value.get("source")
            if isinstance(source, str) and value.get("priority", "required") == "required":
                required.add(source)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(layout)
    return required


def _texts(tree, metrics):
    for node in tree.iter(SVG + "text"):
        size = float(node.get("font-size"))
        font = metrics.get(int(node.get("font-weight", 400))) or next(iter(metrics.values()))
        x, baseline, content = float(node.get("x")), float(node.get("y")), node.text or ""
        yield node.get("data-purpose"), content, (x, baseline - size, x + font.width(content, size), baseline)


def _overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _contrast(first: str, second: str) -> float:
    def luminance(value: str) -> float:
        channels = tuple(int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))
        linear = tuple(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
                       for channel in channels)
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return (max(luminance(first), luminance(second)) + 0.05) / (min(luminance(first), luminance(second)) + 0.05)


@CASES
def test_no_text_is_drawn_over_a_mark(slide, context_path, svg_path, request):
    """Text clears every mark unless it is a contrast-safe inside label on its own host."""
    tree, _, metrics = _load(svg_path, context_path)
    marks = list(_marks(tree))
    collisions = []
    for node in tree.iter(SVG + "text"):
        purpose, scene_id = node.get("data-purpose"), node.get("data-scene-id") or ""
        if purpose not in PLOT_TEXT_PURPOSES:
            continue
        size = float(node.get("font-size"))
        font = metrics.get(int(node.get("font-weight", 400))) or next(iter(metrics.values()))
        content, x, baseline = node.text or "", float(node.get("x")), float(node.get("y"))
        box = (x, baseline - size, x + font.width(content, size), baseline)
        host_ids = {prefix + scene_id.removeprefix("member-label:") for prefix in ("planned:", "actual:")}
        for mark_id, mark_fill, mark_bounds in marks:
            if not _overlaps(box, mark_bounds):
                continue
            allowed = (purpose == "member-label" and mark_id in host_ids and isinstance(mark_fill, str)
                       and isinstance(node.get("fill"), str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", mark_fill)
                       and re.fullmatch(r"#[0-9A-Fa-f]{6}", node.get("fill") or "")
                       and _contrast(node.get("fill") or "", mark_fill) >= 4.5)
            if not allowed:
                collisions.append((purpose, content, mark_id))
    check(slide, request, [list(item) for item in collisions], f"{len(collisions)} unsafe text/mark overlaps: {collisions[:5]}")


@CASES
def test_no_text_leaves_the_viewport(slide, context_path, svg_path, request):
    tree, (width, height), metrics = _load(svg_path, context_path)
    escaped = [(content, round(box[2] - width, 1)) for _, content, box in _texts(tree, metrics)
               if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height]
    check(slide, request, [list(item) for item in escaped], f"text past the canvas edge: {escaped}")


@CASES
def test_row_index_cells_render_an_ordinal(slide, context_path, svg_path, request):
    """A row number is not a duration; the default formatter must not sign it."""
    tree, _, _ = _load(svg_path, context_path)
    body = yaml.safe_load(context_path.read_text(encoding="utf-8"))["body"]
    columns = {column["id"] for column in _bound(context_path, body, "view")["body"].get("tableColumns", ())
               if column.get("source") == "rowIndex"}
    if not columns:
        pytest.skip("no rowIndex column declared")
    wrong = [(node.get("data-scene-id"), node.text) for node in tree.iter(SVG + "text")
             if node.get("data-purpose") == "table-cell"
             and (node.get("data-scene-id") or "").rsplit(":", 1)[-1] in columns
             and not re.fullmatch(r"\d+", (node.text or "").strip())]
    check(slide, request, [list(item) for item in wrong], f"row-index cells that are not an ordinal: {wrong[:3]}")


@CASES
def test_point_rows_never_render_a_span_only_state(slide, context_path, svg_path, request):
    """A gate is reached or it is not; it is never "in progress"."""
    tree, _, _ = _load(svg_path, context_path)
    body = yaml.safe_load(context_path.read_text(encoding="utf-8"))["body"]
    points = {key for key, value in _bound(context_path, body, "project")["objects"].items()
              if value.get("schedule", {}).get("mode") == "fixed"}
    offenders = set()
    for node in tree.iter(SVG + "text"):
        parts = (node.get("data-scene-id") or "").split(":")
        if node.get("data-purpose") == "table-cell" and len(parts) >= 3 and parts[1] in points:
            if (node.text or "").strip() == "in progress":
                offenders.add(parts[1])
    check(slide, request, offenders, f"point-kind rows labelled 'in progress': {sorted(offenders)}")


@CASES
def test_every_declared_slot_produces_a_primitive(slide, context_path, svg_path, request):
    """A slot that draws nothing is an authored intent the render silently dropped."""
    tree, _, _ = _load(svg_path, context_path)
    body = yaml.safe_load(context_path.read_text(encoding="utf-8"))["body"]
    declared = _declared_slots(_bound(context_path, body, "layout"))
    produced = {node.get("data-purpose") for node in tree.iter()}
    empty = sorted(slot for slot in declared & set(SLOT_PURPOSES) if not SLOT_PURPOSES[slot] & produced)
    check(slide, request, empty, f"slots declared in the Layout Profile that drew nothing: {empty}")
