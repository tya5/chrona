"""Native and SVG acceptance for completed Actual/Progress/encoding legend keys (#1679)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.scene.contrast_policy import POLICY_MEMBERS, evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
EXECUTIVE = ROOT / "src/chrona/resources/presets/bundles/executive-light"
ACTUAL = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "realized-legend-actual",
    "body": {"asOf": "2026-02-20", "observations": [
        {"id": "ahead", "sequence": 1, "projectObjectId": "ahead",
         "actual": {"start": "2026-02-02", "finish": "2026-02-07", "progress": 1.0}},
        {"id": "track", "sequence": 1, "projectObjectId": "track",
         "actual": {"start": "2026-02-02", "finish": "2026-02-11", "progress": 1.0}},
        {"id": "behind", "sequence": 1, "projectObjectId": "behind",
         "actual": {"start": "2026-02-02", "finish": "2026-02-14", "progress": 1.0}},
        {"id": "gate", "sequence": 1, "projectObjectId": "gate", "actual": {"at": "2026-02-13"}},
    ]},
}
ACTUAL_COLORS = {"ahead": "#4B5563", "track": "#269D79", "behind": "#B91C1C", "gate": "#269D79"}
PROGRESS_COLOR = "#8D530F"


def _source():
    return sr.project({
        "ahead": sr.span("ahead", date(2026, 2, 2), 10),
        "track": sr.span("track", date(2026, 2, 2), 9),
        "behind": sr.span("behind", date(2026, 2, 2), 7),
        "gate": sr.point("gate", date(2026, 2, 13)),
    })


def _detail(*roles):
    value = yaml.safe_load((EXECUTIVE / "detail.yaml").read_bytes())
    value["body"]["legend"].extend({"role": role, "label": label} for role, label in roles)
    return value


def _parts(*, progress=False):
    parts = sr.bundle("executive-light")
    for role, color in (("actual-ahead", "textMuted"), ("actual-on-track", "positive"),
                        ("actual-behind", "negative")):
        parts["theme"]["body"]["roles"][role] = {}
        parts["theme"]["body"]["colorBindings"][f"{role}.fill"] = color
    body = parts["view"]["body"]
    body["window"] = {"mode": "explicit", "start": "2026-02-01", "end": "2026-02-21"}
    body["rows"] = {"mode": "automatic"}
    body["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Finish delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedNumber",
         "missing": "em-dash", "align": "end", "width": "content", "headerOrientation": "horizontal"},
    ]
    body["comparison"]["facets"] = ["planned", "actual", "finishDelta", "missingActual"]
    if progress:
        body["progressFill"] = {"source": "actual"}
    else:
        body.pop("progressFill", None)
    return parts


def _render(tmp_path: Path, source, *, actual=None, parts=None, detail=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return sr.render(tmp_path, source, presentation=parts or _parts(), actual=actual,
                     detail=detail or _detail(), viewport=(1800, 1000))


def _render_with_style(tmp_path: Path, source, *, parts, style, detail=None, actual=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    project_path = sr._write(tmp_path / "project.yaml", source)
    style_path = sr._write(tmp_path / "style.yaml", style)
    actual_path = sr._write(tmp_path / "actual.yaml", actual) if actual is not None else None
    draft = resolve_draft_render(
        project_path=project_path, view_path=paths["view"], style_path=style_path,
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        actual_path=actual_path,
        detail_path=sr._write(tmp_path / "detail.yaml", detail or _detail()), viewport=(1800, 1000))
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


def _paint_ink(paint):
    return paint.fill, paint.stroke, paint.stroke_width, paint.dash, paint.opacity, paint.gradient


def _swatches(rendered, role):
    return tuple(item for item in rendered.surface.primitives
                 if item.purpose == "legend-swatch" and item.visual_role == role)


def _svg_fills(rendered):
    content = rendered.artifact.content
    root = ElementTree.fromstring(content if isinstance(content, bytes) else content.encode())
    return {item.attrib["data-scene-id"]: item.attrib.get("fill") for item in root.iter()
            if item.attrib.get("data-scene-id")}


def test_executive_light_actual_and_progress_keys_match_distinct_completed_paints_and_svg(tmp_path):
    parts = _parts(progress=True)
    rendered = _render(tmp_path, _source(), actual=ACTUAL, parts=parts)
    actual_marks = tuple(item for item in rendered.surface.primitives if item.purpose == "actual")
    actual_keys = _swatches(rendered, "actual")
    progress_marks = tuple(item for item in rendered.surface.primitives if item.purpose == "progress-fill")
    progress_keys = _swatches(rendered, "progress-fill")

    # Span ink still coalesces; an equal-painted point has its own semantic key.
    marks_by_ink = {_paint_ink(item.paint): item.paint for item in actual_marks}
    keys_by_ink = {_paint_ink(item.paint): item.paint for item in actual_keys}
    assert len(actual_marks) == 4 and len(marks_by_ink) == 3
    assert set(keys_by_ink) == set(marks_by_ink)
    assert len(actual_keys) == 4
    assert {item.source_ref: item.paint.fill for item in actual_marks} == ACTUAL_COLORS
    assert all(_paint_ink(item.paint) in marks_by_ink for item in actual_keys)
    assert progress_marks and len(progress_keys) == 1
    assert {item.paint for item in progress_marks} == {progress_keys[0].paint}
    assert progress_keys[0].paint.fill == PROGRESS_COLOR

    labels = {item.source_ref: item.text for item in rendered.surface.primitives if item.purpose == "legend-label"}
    assert {labels[item.source_ref] for item in actual_keys} == {
        "Ahead", "On track", "Behind", "Actual · Milestone"}
    svg_fills = _svg_fills(rendered)
    for item in (*actual_marks, *actual_keys, *progress_marks, *progress_keys):
        assert svg_fills[item.scene_id] == item.paint.fill


def test_zero_actual_progress_emits_no_progress_key(tmp_path):
    actual = deepcopy(ACTUAL)
    for observation in actual["body"]["observations"]:
        observation["actual"]["progress"] = 0
    rendered = _render(tmp_path, _source(), actual=actual, parts=_parts(progress=True))

    assert not tuple(item for item in rendered.surface.primitives if item.purpose == "progress-fill")
    assert not _swatches(rendered, "progress-fill")
    assert "progressFill" not in " ".join(item.source_ref for item in rendered.surface.primitives
                                               if item.purpose == "legend-swatch")


def _encoded_parts():
    parts = _parts()
    parts["view"]["body"]["colorEncoding"] = {
        "scale": "owners", "target": "planned", "source": {"field": "owner"}, "domain": ["a", "b"],
    }
    parts["theme"]["body"]["colorScales"] = {"owners": {"slots": {"a": "owner-a", "b": "owner-b"}}}
    parts["scheme"]["body"]["categories"].update({"owner-a": "#3456A0", "owner-b": "#0A8060"})
    return parts


def test_all_planned_view_encoding_replaces_base_key_but_mixed_encoding_keeps_it(tmp_path):
    all_source = sr.project({
        "one": sr.span("one", date(2026, 2, 2), 5, owner="a"),
        "two": sr.span("two", date(2026, 2, 10), 5, owner="b"),
    })
    all_encoded = _render(tmp_path / "all", all_source, parts=_encoded_parts())

    def keys(rendered):
        return {item.source_ref for item in rendered.surface.primitives if item.purpose == "legend-swatch"}

    assert "planned" not in keys(all_encoded)
    assert {"scale:owners:a", "scale:owners:b"} <= keys(all_encoded)

    # A closed variance selector supplies the mixed encoded/unencoded case:
    # the ahead planned mark is encoded, while the behind mark retains base ink.
    style_parts = _parts()
    style_parts["theme"]["body"]["colorScales"] = {"style-owners": {"slots": {"a": "owner-a"}}}
    style_parts["scheme"]["body"]["categories"]["owner-a"] = "#3456A0"
    style = {"version": "chrona/style/v0.2", "kind": "style", "id": "partial-plan-fill", "body": {
        "rules": [{"id": "one-owner", "when": {"semantic": "planned", "comparisonCategory": "ahead"},
                   "then": {"encode": {
                "channel": "fill", "source": {"field": "owner"}, "scale": "style-owners",
                "domain": ["a"], "legend": {"title": "Owner"}}}}],
    }}
    mixed_actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "mixed-style-actual",
                    "body": {"asOf": "2026-02-20", "observations": [
                        {"id": "one", "sequence": 1, "projectObjectId": "one",
                         "actual": {"start": "2026-02-02", "finish": "2026-02-05"}},
                        {"id": "two", "sequence": 1, "projectObjectId": "two",
                         "actual": {"start": "2026-02-10", "finish": "2026-02-17"}},
                    ]}}
    mixed_style = _render_with_style(tmp_path / "mixed-style", all_source,
                                     parts=style_parts, style=style, actual=mixed_actual)
    style_keys = {item.source_ref for item in mixed_style.surface.primitives if item.purpose == "legend-swatch"}
    assert "planned" in style_keys and any(key.startswith("scale:style:") for key in style_keys)
    planned_fills = {item.paint.fill for item in mixed_style.surface.primitives if item.purpose == "planned"}
    assert {"#3456A0", "#3986E6"} <= planned_fills


def _render_with_snapshot(tmp_path: Path, source, snapshot, *, actual=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = _parts(progress=True)
    parts["view"]["body"]["comparison"]["baseline"] = "primary"
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    project_path = sr._write(tmp_path / "project.yaml", source)
    snapshot_path = sr._write(tmp_path / "snapshot-project.yaml", snapshot)
    actual_path = sr._write(tmp_path / "actual.yaml", actual) if actual is not None else None
    draft = resolve_draft_render(
        project_path=project_path, view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], actual_path=actual_path,
        detail_path=sr._write(tmp_path / "detail.yaml", _detail(("snapshot", "Snapshot"),
                                                                  ("progressFill", "Progress"))),
        snapshot_project_path=snapshot_path, viewport=(1800, 1000))
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


def test_absent_actual_with_snapshot_has_no_snapshot_actual_progress_or_delta_candidates(tmp_path):
    source = _source()
    snapshot = deepcopy(source)
    for item in snapshot["objects"].values():
        if "schedule" in item and item["schedule"].get("mode") == "fixed-span":
            item["schedule"]["start"] = "2026-01-01"
            item["schedule"]["end"] = "2026-01-10"
    rendered = _render_with_snapshot(tmp_path, source, snapshot)

    roles = {item.visual_role for item in rendered.surface.primitives if item.purpose == "legend-swatch"}
    assert not roles & {"actual", "snapshot", "progress-fill"}
    assert not tuple(item for item in rendered.surface.primitives if item.purpose == "progress-fill")
    assert not tuple(item for item in rendered.surface.primitives
                     if item.purpose == "table-column-label" and item.table_column_id == "Finish delta")


def test_supplied_empty_actual_keeps_delta_column_and_missing_policy(tmp_path):
    rendered = _render(tmp_path, _source(), actual={
        "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "empty-actual",
        "body": {"asOf": "2026-02-20", "observations": []},
    }, parts=_parts())

    delta_headers = tuple(item for item in rendered.surface.primitives
                          if item.purpose == "table-column-label" and item.table_column_id == "Finish delta")
    assert delta_headers
    delta_cells = tuple(item for item in rendered.surface.primitives
                        if item.purpose == "table-cell" and item.table_column_id == "Finish delta")
    assert delta_cells
    assert all(item.text == "—" for item in delta_cells)


def test_final_actual_qualifiers_follow_visible_paint_groups_after_clip(tmp_path):
    actual = deepcopy(ACTUAL)
    behind = next(item for item in actual["body"]["observations"] if item["projectObjectId"] == "behind")
    behind["actual"].update(start="2026-02-22", finish="2026-02-24")
    rendered = _render(tmp_path, _source(), actual=actual, parts=_parts())

    actual_keys = _swatches(rendered, "actual")
    labels = {item.source_ref: item.text for item in rendered.surface.primitives if item.purpose == "legend-label"}
    assert {item.paint.fill for item in actual_keys} == {"#4B5563", "#269D79"}
    assert {labels[item.source_ref] for item in actual_keys} == {"Ahead", "On track", "Actual · Milestone"}


def test_fully_clipped_actual_groups_leave_one_unqualified_key_and_no_progress_key(tmp_path):
    actual = deepcopy(ACTUAL)
    for observation in actual["body"]["observations"]:
        if observation["projectObjectId"] in {"track", "behind"}:
            observation["actual"].update(start="2026-02-22", finish="2026-02-24", progress=1.0)
        elif observation["projectObjectId"] == "ahead":
            observation["actual"]["progress"] = 0.0
        elif observation["projectObjectId"] == "gate":
            observation["actual"]["at"] = "2026-02-22"
    parts = _parts(progress=True)
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-02-01", "end": "2026-02-21",
    }
    rendered = _render(tmp_path, _source(), actual=actual, parts=parts)

    actual_marks = tuple(item for item in rendered.surface.primitives if item.purpose == "actual")
    actual_keys = _swatches(rendered, "actual")
    labels = {item.source_ref: item.text for item in rendered.surface.primitives if item.purpose == "legend-label"}
    assert {item.source_ref for item in actual_marks} == {"ahead"}
    assert len(actual_keys) == 1
    assert actual_keys[0].paint == actual_marks[0].paint
    assert labels[actual_keys[0].source_ref] == "Actual"
    assert not _swatches(rendered, "progress-fill")


def test_dark_canvas_composite_actual_glyph_has_one_complete_key_and_keeps_scalar_keys_separate(tmp_path):
    parts = sr.bundle("executive-light")
    dark = sr.bundle("control-room-dark")
    parts["scheme"] = dark["scheme"]
    parts["theme"]["body"]["contrastPolicy"] = {member: "error" for member in POLICY_MEMBERS}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["theme"]["body"]["values"]["milestone-symbol"]["value"] = {
        "shape": "glyph", "viewBox": [10, 10], "parts": [
            {"d": "M5 0L10 5L5 10L0 5Z", "paint": "fill"},
            {"d": "M5 3L7 5L5 7L3 5Z", "paint": "fill", "color": "#0B1220"},
        ],
    }
    source = sr.project({
        "work": sr.span("work", date(2026, 2, 2), 10),
        "gate": sr.point("gate", date(2026, 2, 4)),
    })
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "dark-glyph-actual",
              "body": {"asOf": "2026-02-20", "observations": [
                  {"id": "work-observed", "sequence": 1, "projectObjectId": "work",
                       "actual": {"start": "2026-02-13", "finish": "2026-02-18"}},
                  {"id": "gate-observed", "sequence": 1, "projectObjectId": "gate",
                   "actual": {"at": "2026-02-12"}},
              ]}}
    detail = _detail(("actual", "Actual"), ("progressFill", "Progress"))

    rendered = sr.render(tmp_path, source, presentation=parts, actual=actual, detail=detail,
                         viewport=(1800, 1000))
    actual_point = tuple(sorted((item for item in rendered.surface.primitives
                                 if item.purpose == "actual" and item.source_ref == "gate" and item.kind == "Symbol"),
                                key=lambda item: item.paint_order))
    actual_span = next(item for item in rendered.surface.primitives
                       if item.purpose == "actual" and item.source_ref == "work")
    actual_swatches = tuple(item for item in rendered.surface.primitives
                            if item.purpose == "legend-swatch" and item.visual_role == "actual")
    swatch_groups: dict[str, list] = {}
    for item in actual_swatches:
        swatch_groups.setdefault(item.source_ref, []).append(item)
    glyph_groups = [tuple(sorted(group, key=lambda item: item.paint_order))
                    for group in swatch_groups.values() if all(item.kind == "Symbol" for item in group)]
    labels = tuple(item for item in rendered.surface.primitives if item.purpose == "legend-label")

    assert len(actual_point) >= 3
    assert len(glyph_groups) == 1
    (glyph_key,) = glyph_groups
    assert tuple(item.paint for item in glyph_key) == tuple(item.paint for item in actual_point)
    assert len({item.source_ref for item in glyph_key}) == 1
    assert sum(item.source_ref == glyph_key[0].source_ref for item in labels) == 1
    assert len(swatch_groups) == 2  # composite point key plus scalar span key
    scalar_keys = [group for group in swatch_groups.values() if any(item.kind == "Rect" for item in group)]
    assert len(scalar_keys) == 1
    assert tuple(item.paint for item in scalar_keys[0]) == (actual_span.paint,)

    svg_ids = {node.attrib.get("data-scene-id") for node in ElementTree.fromstring(rendered.artifact.content)
               .iter() if node.attrib.get("data-scene-id")}
    assert {item.scene_id for item in (*actual_point, *glyph_key)} <= svg_ids
    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    assert not [item for item in findings if item.severity == "error"]


def _ink_colors(paint):
    return frozenset(color for color in (paint.fill, paint.stroke) if color is not None)


def test_equal_red_actual_span_and_point_keep_distinct_keys_and_same_ink_progress_is_omitted(tmp_path):
    parts = _parts(progress=True)
    bindings = parts["theme"]["body"]["colorBindings"]
    parts["scheme"]["body"]["categories"]["legend-red"] = "#FF0000"
    parts["scheme"]["body"]["categories"]["legend-cream"] = "#FFFDF0"
    for role in ("actual", "actual-ahead", "actual-on-track", "actual-behind", "progress-fill"):
        bindings[f"{role}.fill"] = "category:legend-red"
    bindings["progress-fill.stroke"] = "category:legend-cream"
    source = sr.project({
        "span": sr.span("span", date(2026, 2, 2), 10),
        "point": sr.point("point", date(2026, 2, 13)),
    })
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "same-red-actual",
              "body": {"asOf": "2026-02-20", "observations": [
                  {"id": "span-observed", "sequence": 1, "projectObjectId": "span",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-12", "progress": 0.4}},
                  {"id": "point-observed", "sequence": 1, "projectObjectId": "point",
                   "actual": {"at": "2026-02-13"}},
              ]}}

    rendered = _render(tmp_path, source, actual=actual, parts=parts,
                       detail=_detail(("actual", "Actual"), ("progressFill", "Progress")))
    marks = tuple(item for item in rendered.surface.primitives if item.purpose == "actual")
    keys = _swatches(rendered, "actual")
    progress_marks = tuple(item for item in rendered.surface.primitives if item.purpose == "progress-fill")

    assert {item.kind.value for item in marks} >= {"Rect", "Symbol"}
    assert all(item.paint.fill == "#FF0000" for item in marks)
    assert len(keys) == 2
    assert {key.paint.fill for key in keys} == {"#FF0000"}
    labels = {item.source_ref: item.text for item in rendered.surface.primitives if item.purpose == "legend-label"}
    assert {labels[key.source_ref] for key in keys} == {"Actual", "Actual · Milestone"}
    assert any(item.kind.value == "Symbol" and item.paint.stroke != item.paint.fill for item in marks)
    assert progress_marks and all(item.paint.fill == next(
        mark.paint.fill for mark in marks if mark.source_ref == item.source_ref) for item in progress_marks)
    assert all(item.paint.stroke == "#FFFDF0" for item in progress_marks)
    assert not _swatches(rendered, "progress-fill")


def test_progress_key_compares_its_host_not_an_unrelated_equal_paint_actual(tmp_path):
    parts = _parts(progress=True)
    bindings = parts["theme"]["body"]["colorBindings"]
    bindings["actual-behind.fill"] = "warning"
    source = sr.project({
        "host": sr.span("host", date(2026, 2, 2), 10),
        "other": sr.span("other", date(2026, 2, 2), 10),
    })
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "typed-progress-host",
              "body": {"asOf": "2026-02-20", "observations": [
                  {"id": "host-observed", "sequence": 1, "projectObjectId": "host",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-07", "progress": 0.4}},
                  {"id": "other-observed", "sequence": 1, "projectObjectId": "other",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-16"}},
              ]}}

    rendered = _render(tmp_path, source, actual=actual, parts=parts,
                       detail=_detail(("actual", "Actual"), ("progressFill", "Progress")))
    host = next(item for item in rendered.surface.primitives
                if item.purpose == "actual" and item.source_ref == "host")
    other = next(item for item in rendered.surface.primitives
                 if item.purpose == "actual" and item.source_ref == "other")
    progress = tuple(item for item in rendered.surface.primitives if item.purpose == "progress-fill")
    progress_keys = _swatches(rendered, "progress-fill")

    assert progress and len(progress_keys) == 1
    assert _ink_colors(progress[0].paint) == _ink_colors(other.paint)
    assert _ink_colors(progress[0].paint) != _ink_colors(host.paint)
