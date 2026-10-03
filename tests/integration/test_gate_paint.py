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


def _fills(rendered):
    rows = {}
    for item in rendered.surface.primitives:
        if item.scene_id.startswith(("planned:", "legend-swatch:")):
            rows[item.scene_id.split(":")[0] + ":" + item.scene_id.split(":")[-1]] = (item.visual_role, item.paint.fill)
    return rows


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_a_theme_without_the_role_paints_gates_as_planned(tmp_path):
    without = _render(_sub(tmp_path, "a"), gate=False)
    roles = {role for role, _ in _fills(without).values()}
    assert "gate" not in roles


def test_the_gate_role_paints_the_gate_and_its_legend_key_but_not_the_bars(tmp_path):
    plain = _fills(_render(_sub(tmp_path, "plain"), gate=False))
    painted = _fills(_render(_sub(tmp_path, "gate"), gate=True))

    gate_marks = {key: value for key, value in painted.items() if key.startswith("planned:") and key.endswith("gate")}
    assert gate_marks and all(role == "gate" for role, _ in gate_marks.values())
    bar = next(value for key, value in painted.items() if key.startswith("planned:") and key.endswith("work"))
    assert bar == next(value for key, value in plain.items() if key.startswith("planned:") and key.endswith("work"))
    assert bar[0] == "planned" and bar[1] != next(iter(gate_marks.values()))[1]
    key_swatch = painted["legend-swatch:milestone"]
    assert key_swatch[0] == "gate" and key_swatch[1] == next(iter(gate_marks.values()))[1]


def test_the_gate_role_is_gated_like_a_mark(tmp_path):
    # A gate fill equal to the canvas would be invisible: the contrast gate still judges the `gate` role.
    from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
    from chrona.presentation.scene.serialization import scene_document
    painted = _render(_sub(tmp_path, "g"), gate=True, fill="surface")
    findings = evaluate_scene_contrast(scene_document(painted.scene))
    assert [item for item in findings if item.primitive_id.startswith("planned:") and item.primitive_id.endswith("gate")]
