"""#1515: a state-text role used by a graphical legend swatch has mark contrast."""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import (
    evaluate_scene_contrast,
    policy_member_of,
)
from chrona.presentation.scene.model import ScenePrimitive


WHITE = "#FFFFFF"
MID_GRAY = "#808080"  # 3.95:1 on white: above MARK, below required state text.
LOW_GRAY = "#AAAAAA"  # below the 3:1 MARK floor on white.
BOX = {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10}


def _scene(*primitives, policy=None):
    document = {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": WHITE, "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": [],
    }]}
    return evaluate_scene_contrast(document, policy=policy)


def _primitive(identifier, role, kind, fill, *, purpose="legend-swatch", treatment=None):
    result = {"id": identifier, "kind": kind, "sourceRef": role, "sourceKind": "legend",
              "purpose": purpose, "visualRole": role, "paintOrder": 100,
              "bounds": dict(BOX), "paint": {"fill": fill, "opacity": 1}}
    if treatment is not None:
        result["contrastTreatment"] = treatment
    return result


@pytest.mark.parametrize("role", ["variance-ahead", "variance-on-track", "variance-behind"])
@pytest.mark.parametrize("kind", ["Rect", "Symbol", "Path"])
def test_variance_graphical_legend_uses_mark_floor_and_needs_no_text_treatment(role, kind):
    finding, = _scene(_primitive("swatch", role, kind, MID_GRAY))

    assert finding.visual_role == role
    assert (finding.code, finding.floor, finding.severity) == (
        "E_SCENE_MARK_CONTRAST", 3.0, "info")
    assert finding.contrast_ratio > 3.0
    assert finding.contrast_ratio < 4.5


@pytest.mark.parametrize("kind", ["Rect", "Symbol", "Path"])
def test_nonlegend_graphical_state_role_is_not_promoted(kind):
    finding, = _scene(_primitive("state", "variance-behind", kind, MID_GRAY,
                                 purpose="planned", treatment="required"))

    assert (finding.code, finding.floor, finding.severity) == (
        "E_SCENE_STATE_TEXT_CONTRAST", 4.5, "error")


def test_state_text_missing_treatment_still_fails_and_uses_4_5_floor():
    finding, = _scene(_primitive("state-text", "variance-behind", "Text", MID_GRAY,
                                 purpose="table-cell"))

    assert finding.code == "E_SCENE_STATE_TEXT_CONTRAST_TREATMENT"
    assert finding.severity == "error"


def test_state_text_between_mark_and_text_floors_fails_at_4_5():
    finding, = _scene(_primitive("state-text", "variance-behind", "Text", MID_GRAY,
                                 purpose="table-cell", treatment="required"))

    assert (finding.code, finding.floor, finding.severity) == (
        "E_SCENE_STATE_TEXT_CONTRAST", 4.5, "error")
    assert 3.0 < finding.contrast_ratio < 4.5


def test_legend_swatch_at_same_ink_passes_at_mark_floor():
    finding, = _scene(_primitive("swatch", "variance-behind", "Rect", MID_GRAY))

    assert (finding.code, finding.floor, finding.severity) == (
        "E_SCENE_MARK_CONTRAST", 3.0, "info")


@pytest.mark.parametrize("setting,expected_severity,expected_code", [
    ("warning", "warning", "W_SCENE_MARK_CONTRAST"),
    ("error", "error", "E_SCENE_MARK_CONTRAST"),
    ("none", "info", "E_SCENE_MARK_CONTRAST"),
])
def test_legend_mark_policy_severity_and_attribution(setting, expected_severity, expected_code):
    finding, = _scene(_primitive("swatch", "variance-behind", "Rect", LOW_GRAY),
                      policy={"mark": setting})

    assert (finding.severity, finding.code) == (expected_severity, expected_code)
    assert policy_member_of(finding) == "mark"


@pytest.mark.parametrize("role", ["variance-behind", "annotation-note-text", "period-label"])
def test_typed_scene_primitive_accepts_graphical_state_role_as_legend_without_treatment(role):
    primitive = ScenePrimitive("swatch", "Rect", role, "legend", "legend-swatch",
                               role, (10, 10, 20, 10))

    assert primitive.contrast_treatment is None


def test_typed_scene_text_still_rejects_missing_treatment():
    with pytest.raises(ValueError, match="visual_role/contrast_treatment"):
        ScenePrimitive("text", "Text", "variance-behind", "legend", "legend-swatch",
                       "variance-behind", (10, 10, 20, 10), text="Overrun")
