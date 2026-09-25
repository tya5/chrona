from __future__ import annotations

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast


def _scene(*primitives, dispositions=()):
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": "#FFFFFF", "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": list(dispositions),
    }]}


def _primitive(identifier, role, purpose, fill, *, opacity=1, treatment=None):
    value = {"id": identifier, "visualRole": role, "purpose": purpose,
             "paint": {"fill": fill, "opacity": opacity}}
    if treatment is not None:
        value["contrastTreatment"] = treatment
    return value


def test_policy_reports_every_classified_flat_paint_with_its_finite_floor():
    findings = evaluate_scene_contrast(_scene(
        _primitive("band", "row-band", "row-decoration", "#FFFFFF"),
        _primitive("variance", "variance-ahead", "table-cell", "#000000", treatment="required"),
    ))
    by_id = {item.primitive_id: item for item in findings}
    assert by_id["band"].code == "E_SCENE_DECORATION_CONTRAST"
    assert by_id["band"].floor == 1.10
    assert by_id["variance"].code == "E_SCENE_STATE_TEXT_CONTRAST"
    assert by_id["variance"].floor == 4.5


def test_policy_rejects_missing_state_treatment_instead_of_inferring_a_floor():
    finding = evaluate_scene_contrast(_scene(
        _primitive("variance", "variance-on-track", "table-cell", "#000000"),
    ))[0]
    assert finding.code == "E_SCENE_STATE_TEXT_CONTRAST_TREATMENT"
    assert finding.severity == "error"


def test_policy_reports_explicit_decoration_absence_separately_from_paint():
    finding = evaluate_scene_contrast(_scene(
        dispositions=({"visualRole": "calendar-closed", "disposition": "absent"},),
    ))[0]
    assert finding.code == "I_SCENE_DECORATION_ABSENT"
    assert finding.primitive_id is None
    assert finding.disposition == "absent"
