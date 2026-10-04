from __future__ import annotations

import json

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


def _node_relation_path(identifier, points, *, start_node=None, end_node=None):
    path = _primitive(identifier, "Path", paint={"stroke": "#000000", "strokeWidth": 1, "opacity": 1})
    path.update(sourceKind="relation", sourceRef=identifier, points=points)
    if start_node is not None:
        path["fromInstanceId"] = start_node
    if end_node is not None:
        path["toInstanceId"] = end_node
    return path


def _node_overlap_cause(node, relation_ids, reason="distinct declared route approaches share a segment"):
    return "I_LAYOUT_RELATION_NODE_APPROACH_SHARED:" + json.dumps({
        "nodeInstanceId": node, "relationIds": sorted(relation_ids), "reason": reason,
    }, separators=(",", ":"))


def _codes(document):
    return [item.code for item in evaluate_scene_perceptibility(document)]


@pytest.mark.parametrize("points", [[[0, 0], [0.4, 0]], [[0, 0], [4, 0], [4, 0.4], [8, 0.4]]])
def test_substroke_relation_segments_are_observed_including_a_whole_short_path(points):
    path = _primitive("relation:dep", "Path", paint={"stroke": "#000000", "strokeWidth": 1, "opacity": 1})
    path.update(sourceKind="relation", sourceRef="dep", points=points)
    findings = evaluate_scene_perceptibility(_scene(path))
    short = [f for f in findings if f.code == "E_SCENE_RELATION_SEGMENT_TOO_SHORT"]
    assert len(short) == 1
    assert dict(short[0].measured_facts)["length"] == pytest.approx(0.4)


def test_stroke_width_relation_run_is_not_a_substroke_violation():
    path = _primitive("relation:dep", "Path", paint={"stroke": "#000000", "strokeWidth": 1, "opacity": 1})
    path.update(sourceKind="relation", sourceRef="dep", points=[[0, 0], [1, 0]])
    assert "E_SCENE_RELATION_SEGMENT_TOO_SHORT" not in _codes(_scene(path))


@pytest.mark.parametrize(("first", "second", "start_a", "end_a", "start_b", "end_b", "overlap"), [
    ([[0, 0], [10, 0], [10, 10]], [[4, 0], [10, 0], [10, -5]], "shared", "a", "shared", "b", 6.0),
    ([[-10, 0], [0, 0]], [[-5, 0], [0, 0]], "a", "shared", "b", "shared", 5.0),
    ([[0, 0], [10, 0]], [[5, 0], [0, 0]], "shared", "a", "b", "shared", 5.0),
])
def test_shared_node_approach_overlap_is_explained_for_each_endpoint_pair(
        first, second, start_a, end_a, start_b, end_b, overlap):
    pair = ("relation:a", "relation:b")
    document = _scene(
        _node_relation_path(pair[0], first, start_node=start_a, end_node=end_a),
        _node_relation_path(pair[1], second, start_node=start_b, end_node=end_b),
    )
    document["diagnostics"] = [_node_overlap_cause("shared", pair, "approaches meet on a shared node")]
    findings = evaluate_scene_perceptibility(document)
    shared = [item for item in findings if item.code == "I_SCENE_RELATION_NODE_APPROACH_SHARED"]
    assert len(shared) == 1
    assert shared[0].primitive_ids == pair
    assert dict(shared[0].measured_facts) == {
        "nodeInstanceId": "shared", "overlapLength": overlap,
        "reason": "approaches meet on a shared node",
    }
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" not in _codes(document)


def test_multiple_relation_pairs_are_reported_once_and_distinct_instance_ids_do_not_match():
    a = _node_relation_path("relation:a", [[0, 0], [10, 0], [10, 10]], start_node="node", end_node="a")
    b = _node_relation_path("relation:b", [[5, 0], [10, 0], [10, -5]], start_node="node", end_node="b")
    c = _node_relation_path("relation:c", [[8, 0], [12, 0], [12, 5]], start_node="node", end_node="c")
    document = _scene(a, b, c)
    document["diagnostics"] = [_node_overlap_cause("node", ("relation:a", "relation:b"))]
    findings = [item for item in evaluate_scene_perceptibility(document)
                if item.code.endswith("RELATION_NODE_APPROACH_SHARED")]
    assert [(item.code, item.primitive_ids) for item in findings] == [
        ("E_SCENE_RELATION_NODE_APPROACH_SHARED", ("relation:a", "relation:c")),
        ("E_SCENE_RELATION_NODE_APPROACH_SHARED", ("relation:b", "relation:c")),
        ("I_SCENE_RELATION_NODE_APPROACH_SHARED", ("relation:a", "relation:b")),
    ]


def test_repeated_endpoint_pair_at_one_node_emits_only_one_finding():
    document = _scene(
        _node_relation_path("relation:a", [[0, 0], [10, 0], [0, 0]], start_node="node", end_node="node"),
        _node_relation_path("relation:b", [[0, 0], [5, 0], [0, 0]], start_node="node", end_node="node"),
    )
    document["diagnostics"] = [_node_overlap_cause("node", ("relation:a", "relation:b"))]
    findings = [item for item in evaluate_scene_perceptibility(document)
                if item.code == "I_SCENE_RELATION_NODE_APPROACH_SHARED"]
    assert len(findings) == 1 and findings[0].primitive_ids == ("relation:a", "relation:b")


def test_unexplained_overlap_is_an_error_and_legacy_missing_identity_is_not_inferred():
    overlap = _scene(
        _node_relation_path("relation:a", [[0, 0], [10, 0]], start_node="node", end_node="a"),
        _node_relation_path("relation:b", [[5, 0], [15, 0]], start_node="node", end_node="b"),
    )
    findings = [item for item in evaluate_scene_perceptibility(overlap)
                if item.code == "E_SCENE_RELATION_NODE_APPROACH_SHARED"]
    assert len(findings) == 1 and findings[0].primitive_ids == ("relation:a", "relation:b")
    legacy = _scene(
        _node_relation_path("relation:a", [[0, 0], [10, 0]]),
        _node_relation_path("relation:b", [[5, 0], [15, 0]]),
    )
    assert not any(item.code.endswith("RELATION_NODE_APPROACH_SHARED")
                   for item in evaluate_scene_perceptibility(legacy))


@pytest.mark.parametrize("paths", [
    ([[0, 0], [5, 0]], [[5, 0], [10, 0]]),  # point contact only
    ([[0, 0], [10, 0]], [[5, -5], [5, 0]]),  # transverse approach
])
def test_point_contacts_and_transverse_segments_are_not_shared_approaches(paths):
    document = _scene(
        _node_relation_path("relation:a", paths[0], start_node="node", end_node="a"),
        _node_relation_path("relation:b", paths[1], start_node="node", end_node="b"),
    )
    assert not any(item.code.endswith("RELATION_NODE_APPROACH_SHARED")
                   for item in evaluate_scene_perceptibility(document))


@pytest.mark.parametrize("payload", [
    {"nodeInstanceId": "node", "relationIds": ["relation:a"], "reason": "why"},
    {"nodeInstanceId": "node", "relationIds": ["relation:b", "relation:a"], "reason": "why"},
    {"nodeInstanceId": "node", "relationIds": ["relation:a", "relation:b"], "reason": "  "},
])
def test_malformed_layout_node_overlap_explanation_is_an_error(payload):
    document = _scene(
        _node_relation_path("relation:a", [[0, 0], [10, 0]], start_node="node", end_node="a"),
        _node_relation_path("relation:b", [[5, 0], [15, 0]], start_node="node", end_node="b"),
    )
    document["diagnostics"] = ["I_LAYOUT_RELATION_NODE_APPROACH_SHARED:" + json.dumps(payload)]
    findings = [item for item in evaluate_scene_perceptibility(document)
                if item.code == "E_SCENE_RELATION_NODE_APPROACH_SHARED"]
    assert len(findings) == 1


def test_valid_explanation_for_wrong_relation_pair_is_unmatched():
    document = _scene(
        _node_relation_path("relation:a", [[0, 0], [10, 0]], start_node="node", end_node="a"),
        _node_relation_path("relation:b", [[5, 0], [15, 0]], start_node="node", end_node="b"),
    )
    document["diagnostics"] = [_node_overlap_cause("node", ("relation:a", "relation:wrong"))]
    findings = [item for item in evaluate_scene_perceptibility(document)
                if item.code == "E_SCENE_RELATION_NODE_APPROACH_SHARED"]
    assert len(findings) == 1  # the actual overlap is unexplained; extra layout claims are ignored


def test_stale_valid_explanation_without_an_observed_overlap_is_ignored():
    document = _scene(
        _node_relation_path("relation:a", [[0, 0], [10, 0]], start_node="a", end_node="a-end"),
        _node_relation_path("relation:b", [[0, 5], [10, 5]], start_node="b", end_node="b-end"),
    )
    document["diagnostics"] = [_node_overlap_cause("missing-node", ("relation:a", "relation:b"))]
    assert not any(item.code.endswith("RELATION_NODE_APPROACH_SHARED")
                   for item in evaluate_scene_perceptibility(document))


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


def _path_with(identifier, points):
    return {**_relation_path(identifier, "r"), "points": [list(point) for point in points]}


def test_a_relation_path_that_doubles_back_over_itself_is_an_error_1059():
    reversing = _path_with("relation:r:a:b", [(467.8, 167.0), (467.8, 189.3), (461.1, 189.3), (472.1, 189.3)])
    findings = evaluate_scene_perceptibility(_scene(reversing))
    finding = next(item for item in findings if item.code == "E_SCENE_RELATION_PATH_REVERSES")
    assert (finding.severity, finding.primitive_ids) == ("error", ("relation:r:a:b",))
    assert dict(finding.measured_facts) == {"relation": "r", "overlap": 6.7}
    # A later segment overlapping an earlier one (not only the adjacent reversal) is the same defect.
    loop = _path_with("relation:r:a:c", [(0, 0), (10, 0), (10, 5), (5, 5), (5, 0), (8, 0)])
    assert "E_SCENE_RELATION_PATH_REVERSES" in _codes(_scene(loop))


@pytest.mark.parametrize("points", [[[0, 5], [20, 5]], [[0, 0], [20, 20]]])
def test_relation_mark_crossings_include_own_foreign_and_diagonal_paths(points):
    path = _primitive("relation:dep", "Path", paint={"strokeWidth": 1})
    path.update(sourceKind="relation", sourceRef="dep", points=points)
    own = _primitive("planned:a", "Rect", bounds=_bounds(5, 2, 5, 8))
    foreign = _primitive("planned:c", "Rect", bounds=_bounds(12, 2, 5, 15))
    findings = [f for f in evaluate_scene_perceptibility(_scene(path, own, foreign))
                if f.code == "E_SCENE_RELATION_THROUGH_MARK"]
    assert {f.primitive_ids[1] for f in findings} == {"planned:a", "planned:c"}


def test_boundary_contact_ghost_and_legend_swatch_are_not_primary_crossings():
    path = _primitive("relation:dep", "Path", paint={"strokeWidth": 1})
    path.update(sourceKind="relation", sourceRef="dep", points=[[0, 2], [20, 2]])
    own = _primitive("planned:a", "Rect", bounds=_bounds(5, 2, 5, 8))
    ghost = _primitive("planned:snapshot:a", "Rect", bounds=_bounds(5, 0, 5, 8))
    swatch = dict(path, id="legend:dependency", points=[[0, 5], [20, 5]])
    assert "E_SCENE_RELATION_THROUGH_MARK" not in _codes(_scene(path, own, ghost, swatch))


def test_crossing_drawn_quadratic_is_checked_even_when_polyline_is_clear():
    path = _primitive("relation:dep", "Path", paint={"strokeWidth": 1})
    path.update(sourceKind="relation", sourceRef="dep", points=[[0, 0], [20, 0]], pathCommands=[
        {"kind": "move", "points": [[0, 0]]},
        {"kind": "quadratic", "points": [[10, 20], [20, 0]]}])
    mark = _primitive("planned:a", "Rect", bounds=_bounds(8, 8, 4, 4))
    assert "E_SCENE_RELATION_THROUGH_MARK" in _codes(_scene(path, mark))


@pytest.mark.parametrize("changes", [{"points": [[0, 0], ["x", 5]]}, {"paint": {"strokeWidth": "x"}},
                                     {"points": [[0, 0], [float("nan"), 5]]}])
def test_malformed_relation_geometry_has_a_typed_observation_error(changes):
    path = _primitive("relation:dep", "Path", paint={"strokeWidth": 1})
    path.update(sourceKind="relation", sourceRef="dep", points=[[0, 0], [20, 0]])
    path.update(changes)
    with pytest.raises(ScenePerceptibilityError):
        evaluate_scene_perceptibility(_scene(path))


def test_straight_and_stepped_relation_paths_and_the_legend_swatch_are_not_reversals_1059():
    stepped = _path_with("relation:r:a:b", [(0, 0), (0, 10), (6, 10), (6, 4), (12, 4)])
    swatch = {**_path_with("legend-swatch:dependency", [(0, 0), (9, 0), (3, 0)]), "sourceRef": "dependency"}
    assert "E_SCENE_RELATION_PATH_REVERSES" not in _codes(_scene(stepped, swatch))
