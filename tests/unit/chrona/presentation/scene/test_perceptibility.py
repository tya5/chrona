from __future__ import annotations

import pytest

from chrona.presentation.scene.perceptibility import ScenePerceptibilityError, evaluate_scene_perceptibility
from chrona.presentation.scene.paint_analysis import composited_contrast


def _bounds(inline=0, block=0, inline_size=10, block_size=10):
    return {"inline": inline, "block": block, "inlineSize": inline_size, "blockSize": block_size}


def _primitive(identifier, kind="Text", *, bounds=None, slot="slot", order=0, host=None, paint=None):
    value = {"id": identifier, "kind": kind, "slotId": slot, "bounds": bounds or _bounds(), "paintOrder": order}
    if host is not None:
        value["hostPlacementId"] = host
    if paint is not None:
        value["paint"] = paint
    return value


def _scene(*primitives, overflow="fit", canvas_paint="#FFFFFF"):
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{"id": "review", "slots": [
        {"id": "slot", "bounds": _bounds(), "overflow": overflow},
    ], "canvasPaint": {"fill": canvas_paint, "opacity": 1}, "primitives": list(primitives)}]}


def _codes(document):
    return [item.code for item in evaluate_scene_perceptibility(document)]


def test_reports_later_opaque_rect_occlusion_and_preserves_measured_identity():
    findings = evaluate_scene_perceptibility(_scene(
        _primitive("text"), _primitive("cover", "Rect", order=1, paint={"fill": "#000000", "opacity": 1}),
    ))
    finding = next(item for item in findings if item.code == "E_SCENE_TEXT_OCCLUDED")
    assert finding.primitive_ids == ("text", "cover")
    assert dict(finding.measured_facts)["coverageRatio"] == 1


def test_hosted_opaque_overlap_is_individually_classified_not_silently_ignored():
    assert "I_SCENE_HOSTED_TEXT_OVERLAP" in _codes(_scene(
        _primitive("text", host="host"), _primitive("host", "Rect", order=1, paint={"fill": "#000000", "opacity": 1}),
    ))


def test_nonopaque_and_half_coverage_rects_do_not_report_occlusion():
    assert "E_SCENE_TEXT_OCCLUDED" not in _codes(_scene(
        _primitive("text"), _primitive("half", "Rect", order=1, bounds=_bounds(inline_size=4.99), paint={"fill": "#000000", "opacity": 1}),
        _primitive("transparent", "Rect", order=2, paint={"fill": "#000000", "opacity": 0.9}),
    ))


@pytest.mark.parametrize(("overflow", "code"), [("fit", "E_SCENE_TEXT_SLOT_ESCAPE"), ("ellipsized", "E_SCENE_TEXT_SLOT_ESCAPE"),
                                                     ("clip-optional", "E_SCENE_TEXT_SLOT_ESCAPE"),
                                                     ("visible-overflow", "I_SCENE_DECLARED_VISIBLE_OVERFLOW")])
def test_slot_disposition_is_observed_per_text(overflow, code):
    findings = evaluate_scene_perceptibility(_scene(_primitive("text", bounds=_bounds(inline_size=11)), overflow=overflow))
    finding = next(item for item in findings if item.code == code)
    assert finding.slot_id == "slot"
    assert finding.disposition == overflow


def test_slot_tolerance_and_suppressed_disposition_do_not_emit_escape():
    assert "E_SCENE_TEXT_SLOT_ESCAPE" not in _codes(_scene(_primitive("text", bounds=_bounds(inline_size=10.0005))))
    assert "I_SCENE_DECLARED_VISIBLE_OVERFLOW" not in _codes(_scene(_primitive("text", bounds=_bounds(inline_size=11)), overflow="suppressed"))


def test_text_intersection_has_strict_area_threshold_and_canonical_ids():
    document = _scene(_primitive("z", bounds=_bounds()), _primitive("a", bounds=_bounds(inline=5)))
    finding = next(item for item in evaluate_scene_perceptibility(document) if item.code == "E_SCENE_TEXT_INTERSECTION")
    assert finding.primitive_ids == ("a", "z")
    assert dict(finding.measured_facts)["area"] == 50
    assert "E_SCENE_TEXT_INTERSECTION" not in _codes(_scene(_primitive("one", bounds=_bounds()), _primitive("two", bounds=_bounds(inline=9.6))))


def test_paint_observation_composites_opacity_without_selecting_a_policy_floor():
    finding = next(item for item in evaluate_scene_perceptibility(_scene(
        _primitive("tint", "Rect", paint={"fill": "#000000", "opacity": 0.1}),
    )) if item.code == "I_SCENE_PAINT_CONTRAST")
    assert finding.severity == "info"
    assert 1 < dict(finding.measured_facts)["contrastRatio"] < 1.3


def test_shared_flat_paint_analysis_composites_translucent_and_opaque_values():
    assert composited_contrast(fill="#000000", opacity=1, ground="#FFFFFF") == 21
    assert 1 < composited_contrast(fill="#000000", opacity=0.1, ground="#FFFFFF") < 1.3


def test_findings_are_ordered_independently_of_primitive_input_order():
    findings = evaluate_scene_perceptibility(_scene(
        _primitive("z", bounds=_bounds(inline_size=11)), _primitive("a", bounds=_bounds(inline_size=11)),
    ))
    assert list(findings) == sorted(findings, key=lambda item: (item.scene_path, item.code, item.primitive_ids))


@pytest.mark.parametrize("document", [{}, {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": []},
                                        _scene(_primitive("text", slot="absent"))])
def test_rejects_malformed_or_incomplete_scene_facts(document):
    with pytest.raises(ScenePerceptibilityError, match="E_SCENE_PERCEPTIBILITY_DOCUMENT"):
        evaluate_scene_perceptibility(document)
