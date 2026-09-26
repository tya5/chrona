from __future__ import annotations

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast


def _scene(*primitives, dispositions=()):
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": "#FFFFFF", "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": list(dispositions),
    }]}


def _primitive(identifier, role, purpose, fill, *, opacity=1, treatment=None,
               kind="Rect", order=100, bounds=None, stroke=None):
    value = {"id": identifier, "visualRole": role, "purpose": purpose,
             "kind": kind, "paintOrder": order,
             "bounds": bounds or {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
             "paint": {"fill": fill, "opacity": opacity,
                       **({"stroke": stroke, "strokeWidth": 1} if stroke else {})}}
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


def test_mark_ground_uses_highest_earlier_opaque_panel_and_reports_its_identity():
    findings = evaluate_scene_contrast(_scene(
        _primitive("panel", "unclassified", "panel", "#EEEEEE", order=10),
        _primitive("bar", "planned", "planned", "#F4F4F4", order=100),
    ))
    finding = next(item for item in findings if item.primitive_id == "bar")
    assert finding.code == "E_SCENE_MARK_CONTRAST"
    assert finding.severity == "error"
    assert finding.floor == 3.0
    assert (finding.ground_id, finding.ground_color, finding.paint_channel) == ("panel", "#EEEEEE", "fill")
    assert (finding.sample_inline, finding.sample_block) == (20, 15)


def test_a_multi_part_glyph_part_grounds_against_the_earlier_part_beneath_it():
    """#464: a later Symbol part's ground is the earlier same-bounds Symbol part, not the canvas."""
    findings = evaluate_scene_contrast(_scene(
        _primitive("body", "planned", "planned", "#5FA8FF", kind="Symbol", order=100),
        _primitive("band", "planned", "planned", "#1B1B1B", kind="Symbol", order=101),
    ))
    finding = next(item for item in findings if item.primitive_id == "band")
    assert (finding.ground_id, finding.ground_color, finding.paint_channel) == ("body", "#5FA8FF", "fill")


def test_stroke_only_rect_samples_painted_edge_not_unpainted_centre():
    findings = evaluate_scene_contrast(_scene(
        _primitive("left", "unclassified", "panel", "#222222", order=10,
                   bounds={"inline": 0, "block": 0, "inlineSize": 20, "blockSize": 30}),
        _primitive("right", "unclassified", "panel", "#EEEEEE", order=11,
                   bounds={"inline": 20, "block": 0, "inlineSize": 20, "blockSize": 30}),
        _primitive("stripe", "calendar-closed", "calendar-closed", None, stroke="#FFFFFF",
                   order=100, bounds={"inline": 19, "block": 0, "inlineSize": 4, "blockSize": 30}),
    ))
    stripe = next(item for item in findings if item.primitive_id == "stripe")
    assert stripe.ground_id == "left"
    assert stripe.paint_channel == "stroke"
    assert (stripe.sample_inline, stripe.sample_block) == (19, 15)


def test_hosted_progress_fill_is_not_exempt_from_mark_floor():
    findings = evaluate_scene_contrast(_scene(
        _primitive("actual", "actual", "actual", "#00AA00", order=100),
        _primitive("progress", "progress-fill", "progress-fill", "#00AA00", order=101),
    ))
    progress = next(item for item in findings if item.primitive_id == "progress")
    assert progress.ground_id == "actual"
    assert progress.severity == "error"


def test_opaque_linear_gradient_is_sampled_as_mark_ground():
    panel = _primitive("gradient", "unclassified", "panel", "#FFFFFF", order=10)
    panel["paint"]["gradient"] = {
        "start": [10, 15], "end": [30, 15],
        "stops": [{"offset": 0, "color": "#000000"},
                  {"offset": 1, "color": "#FFFFFF"}],
    }
    finding = evaluate_scene_contrast(_scene(
        panel, _primitive("bar", "planned", "planned", "#000000", order=100),
    ))[0]
    assert finding.ground_id == "gradient"
    assert finding.ground_kind == "gradient-sample"
    assert finding.ground_color == "#808080"


def test_category_fill_can_be_carried_by_a_contrasting_explicit_outline():
    finding = evaluate_scene_contrast(_scene(
        _primitive("panel", "unclassified", "panel", "#E8EFFA", order=10),
        _primitive("planned", "planned", "planned", "#E8EFFA", stroke="#172033", order=100),
    ))[0]
    assert finding.severity == "info"
    assert finding.paint_channel == "stroke"
    assert finding.ground_id == "panel"
    assert (finding.sample_inline, finding.sample_block) == (10, 15)
