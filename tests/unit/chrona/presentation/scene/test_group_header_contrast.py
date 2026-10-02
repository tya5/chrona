"""#884: group header text is judged on the band under it (tint, gradient, pattern substrate and ink).

Header text keeps the shared `text` role; the contrast class is resolved from its purpose `group-header`.
Synthetic Scene documents; no `examples/` input.
"""
from __future__ import annotations

from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding, contrast_binding_for
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast

INK = "#172033"
BOX = {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10}
PATTERN = {"tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45, "densityBasisPoints": 1250,
           "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
           "regionBounds": dict(BOX), "clipBounds": dict(BOX), "cornerRadius": 0}


def _scene(*primitives, version="chrona/scene/v0.7", canvas="#FFFFFF"):
    return {"version": version, "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": canvas, "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": []}]}


def _band(fill, *, stroke=None, pattern=None, gradient=None, role="group-header-band",
          purpose="group-header-band", identifier="band", order=10):
    paint = {"fill": fill, "opacity": 1, **({"stroke": stroke, "strokeWidth": 1} if stroke else {})}
    if gradient is not None:
        paint["gradient"] = gradient
    value = {"id": identifier, "visualRole": role, "purpose": purpose, "kind": "Rect", "paintOrder": order,
             "bounds": dict(BOX), "paint": paint}
    if pattern is not None:
        value["pattern"] = dict(pattern)
    return value


def _text(fill=INK, *, purpose="group-header", role="text", kind="Text", identifier="header", order=100):
    return {"id": identifier, "visualRole": role, "purpose": purpose, "kind": kind, "paintOrder": order,
            "bounds": dict(BOX), "paint": {"fill": fill, "opacity": 1}}


def _header(findings):
    return [item for item in findings if item.primitive_id == "header"]


def test_a_tint_equal_to_the_header_ink_is_a_gate_error_on_the_header_text():
    findings = _header(evaluate_scene_contrast(_scene(_band(INK), _text())))
    assert len(findings) == 1
    finding = findings[0]
    assert (finding.code, finding.severity, finding.disposition, finding.floor) == (
        "E_SCENE_STATE_TEXT_CONTRAST", "error", "required", 4.5)
    assert (finding.purpose, finding.visual_role) == ("group-header", "text")
    assert (finding.ground_id, finding.ground_color, finding.paint_channel) == ("band", INK, "fill")
    assert finding.contrast_ratio == 1.0


def test_a_legible_tint_is_reported_as_info_at_the_required_floor():
    finding = _header(evaluate_scene_contrast(_scene(_band("#E8EFFA"), _text())))[0]
    assert finding.severity == "info"
    assert finding.ground_id == "band" and finding.contrast_ratio > 10 and finding.floor == 4.5


def test_the_header_floor_is_required_not_deemphasized():
    # A mid tint under mid ink: above 3.0, below 4.5.
    finding = _header(evaluate_scene_contrast(_scene(_band("#737D91"), _text("#172033"))))[0]
    assert 3.0 < finding.contrast_ratio < 4.5
    assert finding.severity == "error"


def test_the_group_band_under_the_header_is_its_ground_when_there_is_no_header_band():
    finding = _header(evaluate_scene_contrast(_scene(
        _band(INK, role="group-band", purpose="group-decoration", identifier="group"), _text())))[0]
    assert finding.ground_id == "group" and finding.severity == "error"


def test_without_a_band_the_canvas_is_the_ground():
    finding = _header(evaluate_scene_contrast(_scene(_text(), canvas=INK)))[0]
    assert finding.ground_id == "canvas" and finding.severity == "error"


def test_a_gradient_band_is_sampled_under_the_header():
    gradient = {"start": [10, 15], "end": [30, 15],
                "stops": [{"offset": 0, "color": INK}, {"offset": 1, "color": INK}]}
    finding = _header(evaluate_scene_contrast(_scene(_band("#FFFFFF", gradient=gradient), _text())))[0]
    assert finding.ground_kind == "gradient-sample" and finding.severity == "error"


def test_other_text_in_the_shared_role_is_not_classified_by_the_header_rule():
    scene = _scene(_band(INK), _text(purpose="table-cell"), _text(purpose="group-detail", identifier="detail"))
    assert evaluate_scene_contrast(scene) and not [
        item for item in evaluate_scene_contrast(scene) if item.visual_role == "text"]


def test_only_a_text_primitive_can_be_ground_text():
    scene = _scene(_band(INK), _text(kind="Rect"))
    assert not [item for item in evaluate_scene_contrast(scene) if item.primitive_id == "header"]


def test_a_patterned_band_is_judged_on_its_ink_as_well_as_its_substrate():
    ink_is_text = _header(evaluate_scene_contrast(_scene(_band("#FFFFFF", stroke=INK, pattern=PATTERN), _text())))
    assert len(ink_is_text) == 1
    assert (ink_is_text[0].severity, ink_is_text[0].ground_kind, ink_is_text[0].ground_color) == (
        "error", "pattern-host-ink", INK)
    substrate_is_text = _header(evaluate_scene_contrast(_scene(_band(INK, stroke="#FFFFFF", pattern=PATTERN), _text())))
    assert (substrate_is_text[0].severity, substrate_is_text[0].ground_kind) == ("error", "pattern-host-substrate")
    legible = _header(evaluate_scene_contrast(_scene(_band("#FFFFFF", stroke="#E8EFFA", pattern=PATTERN), _text())))
    assert legible[0].severity == "info"
    # The worse of the two grounds decides: the ink is the nearer colour, so it is the recorded ground.
    assert (legible[0].ground_kind, legible[0].ground_color) == ("pattern-host-ink", "#E8EFFA")


def test_a_pattern_is_two_grounds_for_a_mark_as_well():
    band = _band("#FFFFFF", stroke="#3A7BD5", pattern=PATTERN, role="group-band", purpose="group-decoration")
    mark = {"id": "bar", "visualRole": "planned", "purpose": "planned", "kind": "Rect", "paintOrder": 100,
            "bounds": dict(BOX), "paint": {"fill": "#3A7BD5", "opacity": 1}}
    finding = evaluate_scene_contrast(_scene(band, mark))
    bar = next(item for item in finding if item.primitive_id == "bar")
    assert bar.severity == "error" and bar.ground_kind == "pattern-host-ink"


def test_a_decoration_over_a_patterned_host_is_not_judged_on_the_ink():
    host = _band("#FFFFFF", stroke="#E4ECF8", pattern=PATTERN, role="group-band", purpose="group-decoration")
    stripe = {"id": "stripe", "visualRole": "row-band", "purpose": "row-decoration", "kind": "Rect",
              "paintOrder": 100, "bounds": dict(BOX), "paint": {"fill": "#E8EFFA", "opacity": 1}}
    finding = next(item for item in evaluate_scene_contrast(_scene(host, stripe)) if item.primitive_id == "stripe")
    assert finding.ground_kind == "flat" and finding.severity == "info"


def test_a_v06_scene_ignores_a_pattern_as_before():
    finding = _header(evaluate_scene_contrast(_scene(
        _band("#FFFFFF", stroke=INK, pattern=PATTERN), _text(), version="chrona/scene/v0.6")))[0]
    assert finding.ground_kind == "flat" and finding.severity == "info"


def test_header_ink_has_no_stroke_ground_of_its_own():
    text = _text()
    text["paint"].update(stroke="#FFFFFF", strokeWidth=1)
    finding = _header(evaluate_scene_contrast(_scene(_band(INK), text)))
    assert [item.paint_channel for item in finding] == ["fill"] and finding[0].severity == "error"


def test_a_patterned_mark_on_a_patterned_host_is_judged_on_the_host_ink_too():
    host = _band("#FFFFFF", stroke="#3A7BD5", pattern=PATTERN, role="group-band", purpose="group-decoration")
    mark = {"id": "bar", "visualRole": "progress-fill", "purpose": "progress-fill", "kind": "Rect", "paintOrder": 100,
            "bounds": dict(BOX), "paint": {"fill": "#3A7BD5", "stroke": "#102A5C", "opacity": 1}, "pattern": dict(PATTERN)}
    findings = [item for item in evaluate_scene_contrast(_scene(host, mark)) if item.primitive_id == "bar"]
    kinds = {(item.paint_channel, item.ground_kind) for item in findings}
    assert {("fill", "pattern-host-substrate"), ("stroke", "pattern-host-substrate"),
            ("fill", "pattern-host-ink"), ("stroke", "pattern-host-ink")} <= kinds
    assert any(item.severity == "error" and item.ground_kind == "pattern-host-ink" and item.paint_channel == "fill"
               for item in findings)


def test_the_registry_resolves_ground_text_by_purpose_and_never_by_role():
    assert contrast_binding("text") is None and contrast_binding("group-header") is None
    header = contrast_binding_for("text", "group-header")
    assert header is not None and header.contrast_class == ContrastClass.GROUND_TEXT
    assert contrast_binding_for("text", "table-cell") is None and contrast_binding_for("text", None) is None
    assert contrast_binding_for("variance-ahead", "group-header").scene_role == "variance-ahead"
    assert contrast_binding_for("planned", "group-header").contrast_class == ContrastClass.MARK
    assert contrast_binding_for("annotation-callout-text", "group-header") is None
