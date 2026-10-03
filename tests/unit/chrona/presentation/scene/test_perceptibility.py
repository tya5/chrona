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


def _scene(*primitives, overflow="fit", canvas_paint="#FFFFFF", version="chrona/scene/v0.6"):
    return {"version": version, "kind": "scene", "surfaces": [{"id": "review", "slots": [
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


def test_an_image_backed_rects_paint_image_does_not_change_occlusion_465():
    """#465: paint.image is invisible to perceptibility -- only kind/fill/opacity matter."""
    image = {"assetIdentity": "sha256:" + "0" * 64, "viewport": {"inlineSize": 40, "blockSize": 40},
            "tiles": [{"source": _bounds(inline_size=40, block_size=40), "destination": _bounds(inline_size=10, block_size=10)}]}
    findings = evaluate_scene_perceptibility(_scene(
        _primitive("text"), _primitive("cover", "Rect", order=1, paint={"fill": "#000000", "opacity": 1, "image": image}),
    ))
    finding = next(item for item in findings if item.code == "E_SCENE_TEXT_OCCLUDED")
    assert finding.primitive_ids == ("text", "cover")


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


def test_suppressed_layout_identity_must_not_be_emitted():
    document = _scene(_primitive("as-of-label"))
    document["diagnostics"] = ["W_LAYOUT_LABEL_SUPPRESSED:as-of-label"]
    finding = next(item for item in evaluate_scene_perceptibility(document)
                   if item.code == "E_SCENE_SUPPRESSED_PRIMITIVE_EMITTED")
    assert finding.primitive_ids == ("as-of-label",)
    document["surfaces"][0]["primitives"] = []
    assert "E_SCENE_SUPPRESSED_PRIMITIVE_EMITTED" not in _codes(document)


@pytest.mark.parametrize(("diagnostic", "primitive_id"), [
    ("W_LAYOUT_RELATION_SUPPRESSED:relation:one:a:b", "relation:one:a:b"),
    ("W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:one:a:b", "relation-label:one:a:b"),
])
def test_suppressed_relation_and_relation_label_identity(diagnostic, primitive_id):
    document = _scene(_primitive(primitive_id, kind="Path" if primitive_id.startswith("relation:") else "Text"))
    document["diagnostics"] = [diagnostic]
    assert "E_SCENE_SUPPRESSED_PRIMITIVE_EMITTED" in _codes(document)
    document["surfaces"][0]["primitives"][0]["id"] = "unrelated"
    assert "E_SCENE_SUPPRESSED_PRIMITIVE_EMITTED" not in _codes(document)


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


def test_catalog_pattern_observation_exposes_effective_channels_geometry_and_intrinsic_density():
    pattern = {"tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45,
               "densityBasisPoints": 1250, "primitives": [{"kind": "rect", "x": 0, "y": 0,
               "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
               "regionBounds": {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
               "clipBounds": {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
               "cornerRadius": 2}
    primitive = _primitive("pattern", "Rect", paint={"fill": "#EEEEEE", "stroke": "#222222", "opacity": 1})
    primitive["pattern"] = pattern
    document = _scene(primitive, version="chrona/scene/v0.7")
    finding = next(item for item in evaluate_scene_perceptibility(document)
                   if item.code == "I_SCENE_PATTERN_PERCEPTIBILITY")
    facts = dict(finding.measured_facts)
    assert finding.severity == "info" and finding.disposition == "observed"
    assert facts["substrate"] == "#EEEEEE" and facts["ink"] == "#222222"
    assert facts == {
        "substrate": "#EEEEEE", "ink": "#222222", "densityBasisPoints": 1250.0,
        "tileInlineSize": 8.0, "tileBlockSize": 4.0, "angleDegrees": 45.0,
        "originInline": 10.0, "originBlock": 10.0,
        "regionInline": 10.0, "regionBlock": 10.0,
        "regionInlineSize": 20.0, "regionBlockSize": 10.0,
        "clipInline": 10.0, "clipBlock": 10.0,
        "clipInlineSize": 20.0, "clipBlockSize": 10.0,
        "cornerRadius": 2.0,
    }
    mapping = finding.as_mapping()
    assert mapping["version"] == "v1" and mapping["code"] == "I_SCENE_PATTERN_PERCEPTIBILITY"
    assert mapping["primitiveIds"] == ["pattern"] and mapping["slotId"] == "slot"
    assert mapping["disposition"] == "observed"


def test_v06_pattern_does_not_change_legacy_perceptibility_findings():
    primitive = _primitive("pattern", "Rect", paint={"fill": "#EEEEEE", "opacity": 1})
    primitive["pattern"] = {"kind": "diagonal-hatch"}
    assert "I_SCENE_PATTERN_PERCEPTIBILITY" not in _codes(_scene(primitive))


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


def _relation_path(identifier, relation):
    return {**_primitive(identifier, "Path"), "sourceKind": "relation", "sourceRef": relation}


def test_two_paths_for_one_relation_are_an_error_and_one_path_each_is_not_1031():
    one_each = _scene(_relation_path("relation:a:x:y", "a"), _relation_path("relation:b:x:y", "b"))
    assert "E_SCENE_RELATION_PATH_DUPLICATE" not in _codes(one_each)
    findings = evaluate_scene_perceptibility(_scene(
        _relation_path("relation:a:x:y", "a"), _relation_path("relation:a:x:snapshot:y", "a"),
        _relation_path("relation:b:x:y", "b")))
    finding = next(item for item in findings if item.code == "E_SCENE_RELATION_PATH_DUPLICATE")
    assert (finding.severity, finding.primitive_ids) == ("error", ("relation:a:x:y", "relation:a:x:snapshot:y"))
    assert dict(finding.measured_facts) == {"relation": "a", "paths": 2}


def test_the_legend_dependency_swatch_is_not_a_relation_path_1031():
    swatch = _relation_path("legend-swatch:dependency", "dependency")
    assert "E_SCENE_RELATION_PATH_DUPLICATE" not in _codes(_scene(swatch, _relation_path("relation:dependency", "dependency")))
