"""A Theme `gate` role paints gates apart from the bars (#991).

A gate took the `planned` paint (the bars' blue). A Theme that declares `gate` colours the primary gates and the
legend's gate key with it; one that does not renders as before. Synthetic Project through the packaged
`executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "gate-legend", "body": {"legend": [
    {"role": "planned", "label": "Plan"}, {"role": "milestone", "label": "Gate"}]}}


def _render(tmp_path, *, gate: bool, fill: str = "text"):
    source = sr.project({"work": sr.span("work", date(2026, 2, 2), 30), "gate": sr.point("gate", date(2026, 3, 9))})
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    if gate:
        body["roles"]["gate"] = {"strokeWidth": "stroke-width"}
        body["colorBindings"].update({"gate.fill": fill, "gate.stroke": fill})
    body["colorBindings"].setdefault("milestone.fill", "accent")
    body["colorBindings"].setdefault("milestone.stroke", "text")
    body["roles"].setdefault("milestone", {"strokeWidth": "stroke-width"})
    return sr.render(tmp_path, source, presentation=parts, detail=DETAIL)


def _owner_marks(rendered, owner):
    return [item for item in rendered.surface.primitives
            if item.source_kind == "object" and item.source_ref == owner
            and item.purpose in {"planned", "actual"}]


def _owner_swatch(rendered, owner):
    prefix = f"legend-swatch:{owner}"
    return [item for item in rendered.surface.primitives
            if item.purpose == "legend-swatch" and item.kind == "Symbol"
            and (item.scene_id == prefix or item.scene_id.startswith(prefix + ":"))]


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_a_theme_without_the_role_paints_gates_as_planned(tmp_path):
    without = _render(_sub(tmp_path, "a"), gate=False)
    roles = {item.visual_role for item in _owner_marks(without, "gate")}
    assert "gate" not in roles


def test_the_gate_role_paints_the_gate_and_its_legend_key_but_not_the_bars(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), gate=False)
    painted = _render(_sub(tmp_path, "gate"), gate=True)

    gate_marks = _owner_marks(painted, "gate")
    assert gate_marks and all(item.visual_role == "gate" for item in gate_marks)
    gate_fill = next(item.paint.fill for item in gate_marks if item.paint.fill is not None)
    painted_bar = next(item for item in _owner_marks(painted, "work") if item.paint.fill is not None)
    plain_bar = next(item for item in _owner_marks(plain, "work") if item.paint.fill is not None)
    assert (painted_bar.visual_role, painted_bar.paint.fill) == (plain_bar.visual_role, plain_bar.paint.fill)
    assert painted_bar.visual_role == "planned" and painted_bar.paint.fill != gate_fill
    key_swatch = next(item for item in _owner_swatch(painted, "milestone") if item.paint.fill is not None)
    assert key_swatch.visual_role == "gate" and key_swatch.paint.fill == gate_fill


def test_the_gate_role_is_gated_like_a_mark(tmp_path):
    # A gate fill equal to the canvas would be invisible: the contrast gate still judges the `gate` role.
    from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
    from chrona.presentation.scene.serialization import scene_document
    painted = _render(_sub(tmp_path, "g"), gate=True, fill="surface")
    findings = evaluate_scene_contrast(scene_document(painted.scene))
    gate_ids = {item.scene_id for item in _owner_marks(painted, "gate")}
    assert [item for item in findings if item.primitive_id in gate_ids]
