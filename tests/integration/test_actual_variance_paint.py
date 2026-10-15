"""Variance classes may select a Theme fill for Actual marks (#1516)."""
from __future__ import annotations

from datetime import date
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"


ACTUAL = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "variance-paint-test",
    "body": {
        "asOf": "2026-02-20",
        "observations": [
            {"id": "ahead-observed", "sequence": 1, "projectObjectId": "ahead",
             "actual": {"start": "2026-02-02", "finish": "2026-02-07", "progress": 1.0}},
            {"id": "track-observed", "sequence": 1, "projectObjectId": "track",
             "actual": {"start": "2026-02-02", "finish": "2026-02-11", "progress": 1.0}},
            {"id": "behind-observed", "sequence": 1, "projectObjectId": "behind",
             "actual": {"start": "2026-02-02", "finish": "2026-02-14", "progress": 1.0}},
            {"id": "gate-observed", "sequence": 1, "projectObjectId": "gate",
             "actual": {"at": "2026-02-13"}},
        ],
    },
}

COLORS = {
    "actual-ahead": "textMuted",
    "actual-on-track": "positive",
    "actual-behind": "negative",
}


def _source():
    return sr.project({
        "ahead": sr.span("ahead", date(2026, 2, 2), 10),
        "track": sr.span("track", date(2026, 2, 2), 9),
        "behind": sr.span("behind", date(2026, 2, 2), 7),
        "gate": sr.point("gate", date(2026, 2, 13)),
        "missing": sr.span("missing", date(2026, 2, 2), 5),
    })


def _parts(*, bind_variance: bool, declare_variance: bool = False):
    parts = sr.bundle("executive-light")
    # Host-fill evidence is independent of the View's optional progress overlay.
    parts["view"]["body"].pop("progressFill", None)
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-02-01", "end": "2026-02-21",
    }
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Finish delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedNumber",
         "missing": "blank", "align": "end", "width": "content", "headerOrientation": "horizontal"},
    ]
    parts["view"]["body"]["comparison"]["facets"].append("missingActual")
    if bind_variance or declare_variance:
        roles = parts["theme"]["body"]["roles"]
        for role in COLORS:
            roles[role] = {}
        if bind_variance:
            bindings = parts["theme"]["body"]["colorBindings"]
            for role, color in COLORS.items():
                bindings[f"{role}.fill"] = color
    return parts


def _render(tmp_path, *, bind_variance: bool, declare_variance: bool = False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return sr.render(tmp_path, _source(),
                     presentation=_parts(bind_variance=bind_variance, declare_variance=declare_variance), actual=ACTUAL,
                     viewport=(1800, 1000))


def _render_explicit_actual(tmp_path):
    parts = _parts(bind_variance=True)
    for field in ("selection", "grouping", "ordering"):
        parts["view"]["body"].pop(field, None)
    parts["view"]["body"]["rows"] = {
        "mode": "explicit",
        "items": [
            {"id": f"row-{object_id}", "depth": 0, "items": [
                {"id": f"actual-{object_id}", "source": {"kind": "actual", "object": object_id}}
            ]}
            for object_id in ("ahead", "track", "behind")
        ],
    }
    return sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL, viewport=(1800, 1000))


def _actuals(rendered):
    return {item.source_ref: item for item in rendered.surface.primitives
            if item.purpose == "actual" and item.source_kind == "object"}


def test_complete_actual_variance_selects_class_fill_in_scene_and_svg(tmp_path):
    rendered = _render(tmp_path, bind_variance=True)
    marks = _actuals(rendered)
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_by_id = {node.attrib.get("data-scene-id"): node.attrib.get("fill") for node in svg.iter()
                 if node.attrib.get("data-scene-id")}

    assert marks["ahead"].paint.fill == "#4B5563"
    assert marks["track"].paint.fill == "#269D79"
    assert marks["behind"].paint.fill == "#B91C1C"
    for item_id in ("ahead", "track", "behind"):
        assert marks[item_id].visual_role == "actual"
        assert svg_by_id[marks[item_id].scene_id] == marks[item_id].paint.fill

    # State text remains its independent variance role and completed contrast policy.
    delta_roles = {item.source_ref: (item.visual_role, item.contrast_treatment)
                   for item in rendered.surface.primitives
                   if item.purpose == "table-cell" and item.visual_role.startswith("variance-")}
    assert {role for role, _ in delta_roles.values()} >= {"variance-ahead", "variance-on-track", "variance-behind"}
    assert all(treatment in {"required", "deemphasized"} for _, treatment in delta_roles.values())
    assert not rendered.contrast_warnings

    # An Actual point has no finish variance and keeps the base Actual paint.
    assert marks["gate"].visual_role == "actual"
    assert marks["gate"].paint.fill == "#269D79"

    # The due but unobserved item keeps the separate Missing Actual semantic and paint.
    missing = next(item for item in rendered.surface.primitives if item.purpose == "missingActual")
    assert missing.source_ref == "missing"
    assert missing.visual_role == "missing-actual"
    assert missing.paint.fill == "#4B5563"


def test_absent_variance_binding_preserves_existing_actual_svg_and_geometry(tmp_path):
    fallback = _render(tmp_path / "fallback", bind_variance=False)
    declared_but_unbound = _render(tmp_path / "unbound", bind_variance=False, declare_variance=True)
    bound = _render(tmp_path / "bound", bind_variance=True)

    assert declared_but_unbound.artifact.content == fallback.artifact.content
    fallback_marks, unbound_marks = _actuals(fallback), _actuals(declared_but_unbound)
    bound_marks = _actuals(bound)
    assert set(fallback_marks) == set(unbound_marks)
    for item_id, mark in fallback_marks.items():
        other = unbound_marks[item_id]
        assert other.bounds == mark.bounds
        assert other.paint == mark.paint
        painted = bound_marks[item_id]
        assert replace(painted, paint=mark.paint) == mark
        assert (painted.paint.stroke, painted.paint.stroke_width, painted.paint.dash) == (
            mark.paint.stroke, mark.paint.stroke_width, mark.paint.dash)


def test_technical_print_binds_only_the_behind_actual_to_its_red_scheme_ink(tmp_path):
    parts = sr.bundle("technical-print")
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-02-01", "end": "2026-02-21",
    }
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL,
                         icon_catalogs=(STARTER_CATALOG,), viewport=(1800, 1000))
    marks = _actuals(rendered)
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_by_id = {node.attrib.get("data-scene-id"): node.attrib.get("fill") for node in svg.iter()
                 if node.attrib.get("data-scene-id")}

    # The technical-print Scheme explicitly defines `negative` as this ink.
    assert marks["behind"].paint.fill == "#B3241C"
    assert marks["ahead"].paint.fill == marks["track"].paint.fill == "#0D0D0D"
    for item_id in ("ahead", "track", "behind"):
        assert svg_by_id[marks[item_id].scene_id] == marks[item_id].paint.fill
    assert not rendered.contrast_warnings


def test_explicit_actual_rows_receive_variance_fill_in_svg(tmp_path):
    rendered = _render_explicit_actual(tmp_path)
    marks = _actuals(rendered)
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_by_id = {node.attrib.get("data-scene-id"): node.attrib.get("fill") for node in svg.iter()
                 if node.attrib.get("data-scene-id")}

    for item_id, color in {"ahead": "#4B5563", "track": "#269D79", "behind": "#B91C1C"}.items():
        assert marks[item_id].purpose == "actual"
        assert marks[item_id].visual_role == "actual"
        assert svg_by_id[marks[item_id].scene_id] == color
    assert not rendered.contrast_warnings


def test_progress_overlay_keeps_its_paint_and_reports_changed_host_contrast(tmp_path):
    def render_progress(directory, *, bind_variance):
        directory.mkdir()
        parts = _parts(bind_variance=bind_variance)
        parts["view"]["body"]["progressFill"] = {"source": "actual"}
        return sr.render(directory, _source(), presentation=parts, actual=ACTUAL,
                         viewport=(1800, 1000))

    baseline = render_progress(tmp_path / "baseline", bind_variance=False)
    selected = render_progress(tmp_path / "selected", bind_variance=True)
    baseline_progress = {item.scene_id: item for item in baseline.surface.primitives
                         if item.purpose == "progress-fill"}
    selected_progress = {item.scene_id: item for item in selected.surface.primitives
                         if item.purpose == "progress-fill"}
    assert baseline_progress and selected_progress == baseline_progress
    assert not baseline.contrast_warnings
    assert {identity for warning in selected.contrast_warnings for identity in warning.primitive_ids} == {
        "progress-fill:actual:ahead:ahead", "progress-fill:actual:behind:behind",
    }
    assert all(warning.code == "W_SCENE_MARK_CONTRAST" for warning in selected.contrast_warnings)
