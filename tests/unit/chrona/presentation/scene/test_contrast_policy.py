from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast


def _scene(*primitives, dispositions=(), version="chrona/scene/v0.6", provenance=None):
    scene = {"version": version, "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": "#FFFFFF", "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": list(dispositions),
    }]}
    if provenance is not None:
        scene["provenance"] = provenance
    return scene


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
    # A white band on the white canvas misses the decoration floor: a warning, never an error (#995).
    assert (by_id["band"].code, by_id["band"].severity) == ("W_SCENE_DECORATION_CONTRAST", "warning")
    assert by_id["band"].floor == 1.10
    assert by_id["variance"].code == "E_SCENE_STATE_TEXT_CONTRAST"
    assert by_id["variance"].floor == 4.5


def test_recovery_halo_is_decoration_not_a_mark_floor_exemption():
    halo = _primitive("halo", "dependency-halo", "dependency-halo", None,
                      kind="Path", stroke="#FFFFFF")
    halo["points"] = [[10, 15], [30, 15]]
    finding = next(item for item in evaluate_scene_contrast(_scene(halo)) if item.primitive_id == "halo")
    assert finding.code == "W_SCENE_DECORATION_CONTRAST"
    assert finding.severity == "warning"
    assert finding.floor == 1.10


def test_policy_rejects_missing_state_treatment_instead_of_inferring_a_floor():
    finding = evaluate_scene_contrast(_scene(
        _primitive("variance", "variance-on-track", "table-cell", "#000000"),
    ))[0]
    assert finding.code == "E_SCENE_STATE_TEXT_CONTRAST_TREATMENT"
    assert finding.severity == "error"


def test_note_text_requires_required_treatment_at_serialized_boundary():
    finding = evaluate_scene_contrast(_scene(
        _primitive("note-text", "annotation-note-text", "annotation-note-text", "#000000",
                   treatment="deemphasized"),
    ))[0]
    assert finding.code == "E_SCENE_STATE_TEXT_CONTRAST_TREATMENT"
    assert finding.scene_path == "/surfaces/0:review/primitives/0/contrastTreatment"


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


def test_an_image_backed_container_grounds_note_text_by_its_declared_fill_465():
    """#465: paint.image never changes ground resolution -- fill alone still does.

    An image-backed annotation container is still an ordinary Rect with a flat
    `fill` (the Theme author's declared representative colour for the
    artwork's content area); `_ground_under` must keep treating it exactly
    like a plain rectangle container, oblivious to `paint.image`.
    """
    ground = _primitive("annotation-box", "unclassified", "annotation", "#16213A", order=10,
                        bounds={"inline": 0, "block": 0, "inlineSize": 200, "blockSize": 60})
    ground["visualRole"] = "annotation-note-box"
    ground["sourceRef"] = "note:1"
    ground["paint"]["image"] = {
        "assetIdentity": "sha256:" + "0" * 64,
        "viewport": {"inlineSize": 40, "blockSize": 40},
        "tiles": [{"source": {"inline": 0, "block": 0, "inlineSize": 40, "blockSize": 40},
                  "destination": {"inline": 0, "block": 0, "inlineSize": 200, "blockSize": 60}}],
    }
    findings = evaluate_scene_contrast(_scene(
        ground,
        {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                      treatment="required", order=100,
                      bounds={"inline": 10, "block": 10, "inlineSize": 100, "blockSize": 20}),
         "sourceRef": "note:1"},
    ))
    finding = next(item for item in findings if item.primitive_id == "note-text")
    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == ("annotation-box", "#16213A", "flat")


def test_note_text_cannot_fall_back_to_unpaired_or_wrong_source_ground():
    text = {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                         treatment="required"), "sourceRef": "note:1"}
    unrelated = {**_primitive("other-box", "annotation-note-box", "annotation-note-box", "#000000",
                               order=10), "sourceRef": "note:2"}
    finding = next(item for item in evaluate_scene_contrast(_scene(unrelated, text))
                   if item.primitive_id == "note-text")
    assert finding.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert finding.ground_id is None


def test_note_text_rejects_missing_later_and_non_containing_paired_boxes():
    text = {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                         treatment="required", order=100), "sourceRef": "note:1"}
    valid_box = {**_primitive("box", "annotation-note-box", "annotation-note-box", "#000000",
                              order=10), "sourceRef": "note:1"}
    later_box = {**valid_box, "paintOrder": 101}
    outside_box = {**valid_box, "bounds": {"inline": 100, "block": 100,
                                            "inlineSize": 20, "blockSize": 10}}
    for primitives in ((text,), (later_box, text), (outside_box, text)):
        finding = next(item for item in evaluate_scene_contrast(_scene(*primitives))
                       if item.primitive_id == "note-text")
        assert finding.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"


def test_note_text_rejects_invalid_topmost_box_without_falling_back_to_lower_box():
    lower = {**_primitive("lower", "annotation-note-box", "annotation-note-box", "#000000",
                           order=10), "sourceRef": "note:1"}
    top = {**_primitive("top", "annotation-note-box", "annotation-note-box", None,
                        order=20), "sourceRef": "note:1"}
    text = {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                         treatment="required", order=100), "sourceRef": "note:1"}
    finding = next(item for item in evaluate_scene_contrast(_scene(lower, top, text))
                   if item.primitive_id == "note-text")
    assert finding.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert finding.ground_id == "top"


def test_note_text_rejects_absent_and_partial_opacity_box_fills():
    for fill, opacity in ((None, 1), ("#000000", 0.5)):
        box = {**_primitive("box", "annotation-note-box", "annotation-note-box", fill,
                            opacity=opacity, order=10), "sourceRef": "note:1"}
        text = {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                             treatment="required", order=100), "sourceRef": "note:1"}
        finding = next(item for item in evaluate_scene_contrast(_scene(box, text))
                       if item.primitive_id == "note-text")
        assert finding.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"


def test_note_text_rejects_gradient_or_pattern_note_box_ground():
    for feature in ("gradient", "pattern"):
        box = {**_primitive("box", "annotation-note-box", "annotation-note-box", "#000000",
                            order=10), "sourceRef": "note:1"}
        if feature == "gradient":
            box["paint"]["gradient"] = {"start": [10, 10], "end": [30, 10],
                                         "stops": [{"offset": 0, "color": "#000000"},
                                                   {"offset": 1, "color": "#FFFFFF"}]}
        else:
            box["pattern"] = {"kind": "diagonal"}
        text = {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                             treatment="required", order=100), "sourceRef": "note:1"}
        finding = next(item for item in evaluate_scene_contrast(_scene(box, text))
                       if item.primitive_id == "note-text")
        assert finding.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"


def test_note_text_can_use_paired_symbol_box_ground():
    box = {**_primitive("box", "annotation-note-box", "annotation-note-box", "#16213A",
                        kind="Symbol", order=10), "sourceRef": "note:1"}
    text = {**_primitive("note-text", "annotation-note-text", "annotation-note-text", "#FFFFFF",
                         treatment="required", order=100), "sourceRef": "note:1"}
    finding = next(item for item in evaluate_scene_contrast(_scene(box, text))
                   if item.primitive_id == "note-text")
    assert finding.ground_id == "box"
    assert finding.ground_color == "#16213A"


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


def _encoding_witness(value="gate"):
    return {"channel": "fill", "scaleId": "status-colors", "field": "status", "value": value,
            "sources": [{"kind": "view", "id": "view-a", "sourceRef": "/body/colorEncoding"}]}


def _encoded_mark(identifier="encoded", *, fill="#2C2138", stroke="#EAF0FA", order=100):
    mark = _primitive(identifier, "planned", "planned", fill, kind="Symbol", order=order, stroke=stroke,
                      bounds={"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10})
    mark.update(sourceRef="task-a", sourceKind="project", encoding=_encoding_witness())
    return mark


def _dark_host():
    return _primitive("host", "unclassified", "panel", "#16213A", order=10,
                      bounds={"inline": 0, "block": 0, "inlineSize": 60, "blockSize": 40})


def _cone(mark_ground=False, ink="#101010"):
    return {"id": "cone", "visualRole": "as-of-cone", "purpose": "as-of-cone", "kind": "Symbol",
            "paintOrder": 50, "markGround": mark_ground,
            "bounds": {"inline": 0, "block": 0, "inlineSize": 60, "blockSize": 40},
            "symbol": {"outline": [{"kind": "move", "points": [[0, 0]]},
                                   {"kind": "line", "points": [[60, 0]]},
                                   {"kind": "line", "points": [[60, 40]]},
                                   {"kind": "line", "points": [[0, 40]]},
                                   {"kind": "line", "points": [[0, 0]]}]},
            "paint": {"fill": ink, "opacity": 1, "gradient": {
                "start": [0, 0], "end": [0, 40],
                "stops": [{"offset": 0, "color": ink, "opacity": 1},
                          {"offset": 1, "color": ink, "opacity": 1}]}}}


def _encoded_scene(*primitives):
    return _scene(*primitives, version="chrona/scene/v0.7",
                  provenance={"resources": [{"kind": "view", "id": "view-a"}]})


def test_encoded_fill_is_checked_independently_of_readable_mark_outline():
    scene = _encoded_scene(_dark_host(), _encoded_mark())
    findings = evaluate_scene_contrast(scene, policy={"mark": "warning"})
    encoded = next(item for item in findings if item.code == "W_SCENE_ENCODING_CONTRAST")
    shape = next(item for item in findings if item.primitive_id == "encoded"
                 and item.code in {"E_SCENE_MARK_CONTRAST", "W_SCENE_MARK_CONTRAST"})

    assert encoded.severity == "warning"
    assert encoded.floor == 3.0
    assert encoded.paint_channel == "fill"
    assert encoded.ground_id == "host"
    assert encoded.contrast_ratio < 3.0
    assert encoded.encoding.as_mapping() == _encoding_witness()
    assert encoded.as_mapping()["encoding"] == _encoding_witness()
    # The existing mark observation still selects the readable outline.
    assert shape.paint_channel == "stroke"
    assert shape.contrast_ratio >= 3.0
    assert not any(item.severity == "error" for item in findings)


@pytest.mark.parametrize(("mark_ground", "expected_ground"), [(False, "host"), (True, "cone")])
def test_encoded_fill_uses_the_cones_completed_mark_ground_choice(mark_ground, expected_ground):
    findings = evaluate_scene_contrast(_encoded_scene(_dark_host(), _cone(mark_ground), _encoded_mark()),
                                       policy={"mark": "warning"})
    encoded = next(item for item in findings if item.code == "W_SCENE_ENCODING_CONTRAST")

    assert encoded.ground_id == expected_ground
    assert (encoded.ground_kind == "cone-blend") is mark_ground


@pytest.mark.parametrize(("mark_ground", "expected_ground"), [(False, "host"), (True, "cone")])
def test_multipart_mark_uses_the_cones_completed_mark_ground_choice(mark_ground, expected_ground):
    first = _primitive("glyph:part0", "planned", "planned", "#101010", kind="Symbol", order=100)
    second = _primitive("glyph:part1", "planned", "planned", "#101010", kind="Symbol", order=101,
                        bounds=first["bounds"])
    for part in (first, second):
        part.update(sourceRef="task-a", sourceKind="project")
    findings = evaluate_scene_contrast(_scene(_dark_host(), _cone(mark_ground), first, second,
                                              version="chrona/scene/v0.7"), policy={"mark": "warning"})
    shape = next(item for item in findings if item.code == "W_SCENE_MARK_CONTRAST")

    assert shape.ground_id == expected_ground
    assert (shape.ground_kind == "cone-blend") is mark_ground


@pytest.mark.parametrize(("mark_ground", "expected_ground"), [(False, "host"), (True, "cone")])
def test_catalog_pattern_mark_uses_the_cones_completed_mark_ground_choice(mark_ground, expected_ground):
    primitive = _primitive("pattern", "progress-fill", "progress-fill", "#101010", order=100)
    primitive["pattern"] = {
        "tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45,
        "densityBasisPoints": 1250, "primitives": [{"kind": "rect", "x": 0, "y": 0,
        "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
        "regionBounds": primitive["bounds"], "clipBounds": primitive["bounds"], "cornerRadius": 0,
    }
    primitive["paint"].update(stroke="#101010", strokeWidth=1)
    findings = evaluate_scene_contrast(_scene(_dark_host(), _cone(mark_ground), primitive,
                                              version="chrona/scene/v0.7"), policy={"mark": "warning"})
    mark_findings = [item for item in findings if item.primitive_id == "pattern"]

    assert mark_findings
    external_grounds = [item for item in mark_findings if item.ground_kind in {"flat", "cone-blend"}]
    assert external_grounds
    assert {item.ground_id for item in external_grounds} == {expected_ground}
    assert all((item.ground_kind == "cone-blend") is mark_ground for item in external_grounds)


def test_mark_ground_choice_does_not_change_severity_or_exception_ground_matching():
    scene = _scene(_cone(True, ink="#101010"),
                   _primitive("bar", "planned", "planned", "#101010", order=100))
    none = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "none"})
                if item.primitive_id == "bar")
    warning = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "warning"})
                    if item.primitive_id == "bar")
    error = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "error"})
                 if item.primitive_id == "bar")
    accepted = next(item for item in evaluate_scene_contrast(
        scene, policy={"mark": "error"}, exceptions=[{
            "purpose": "planned", "over": "as-of-cone", "minimum": 0.9,
            "reason": "explicit cone ground fixture",
        }]) if item.primitive_id == "bar")

    assert (none.code, none.severity, none.ground_id) == ("E_SCENE_MARK_CONTRAST", "info", "cone")
    assert (warning.code, warning.severity, warning.ground_id) == ("W_SCENE_MARK_CONTRAST", "warning", "cone")
    assert (error.code, error.severity, error.ground_id) == ("E_SCENE_MARK_CONTRAST", "error", "cone")
    assert (accepted.code, accepted.severity, accepted.ground_id) == ("W_SCENE_CONTRAST_ACCEPTED", "warning", "cone")


def test_unencoded_twin_and_stroke_only_mark_gain_no_encoding_finding():
    unencoded = _encoded_mark()
    unencoded.pop("encoding")
    stroke_only = _primitive("stroke-only", "planned", "planned", None,
                              kind="Symbol", order=101, stroke="#EAF0FA")
    scene = _encoded_scene(_dark_host(), unencoded, stroke_only)
    findings = evaluate_scene_contrast(scene, policy={"mark": "warning"})

    assert not any(item.code == "W_SCENE_ENCODING_CONTRAST" for item in findings)
    assert not any(item.code == "E_SCENE_ENCODING_CONTRAST" for item in findings)


def test_encoded_multipart_fill_is_checked_even_when_another_part_carries_visibility():
    first = _encoded_mark("glyph:part0", order=100)
    second = _primitive("glyph:part1", "planned", "planned", "#EAF0FA", kind="Symbol", order=101,
                        bounds=first["bounds"])
    for part in (first, second):
        part.update(sourceRef="task-a", sourceKind="project")
    scene = _encoded_scene(_dark_host(), first, second)
    findings = evaluate_scene_contrast(scene, policy={"mark": "warning"})

    encoded = [item for item in findings if item.code == "W_SCENE_ENCODING_CONTRAST"]
    assert len(encoded) == 1
    assert encoded[0].primitive_id == "glyph:part0"
    assert encoded[0].paint_channel == "fill"
    shape = next(item for item in findings if item.code in {"E_SCENE_MARK_CONTRAST", "W_SCENE_MARK_CONTRAST"}
                 and item.primitive_id in {"glyph:part0", "glyph:part1"})
    assert shape.contrast_ratio >= 3.0


def test_encoded_fill_obeys_mark_policy_none_error_and_accepted_exception():
    scene = _encoded_scene(_dark_host(), _encoded_mark())
    none = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "none"})
                if item.code == "E_SCENE_ENCODING_CONTRAST")
    assert none.severity == "info"

    error = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "error"})
                 if item.code == "E_SCENE_ENCODING_CONTRAST")
    assert error.severity == "error"

    accepted = next(item for item in evaluate_scene_contrast(
        scene, policy={"mark": "error"},
        exceptions=[{"purpose": "planned", "over": "unclassified", "minimum": 1.0,
                     "reason": "accepted fixture"}])
        if item.accepted_code == "E_SCENE_ENCODING_CONTRAST")
    assert accepted.code == "W_SCENE_CONTRAST_ACCEPTED"
    assert accepted.encoding.as_mapping() == _encoding_witness()


def test_encoded_fill_policy_override_is_scoped_to_encoded_findings():
    scene = _encoded_scene(_dark_host(), _encoded_mark())
    findings = evaluate_scene_contrast(
        scene, policy={"mark": "error"},
        encoded_fill_policy={"mark": "warning", "unsupportedGround": "warning"})

    encoded = next(item for item in findings if item.encoding is not None)
    ordinary = next(item for item in findings if item.code == "E_SCENE_MARK_CONTRAST")
    assert encoded.code == "W_SCENE_ENCODING_CONTRAST"
    assert encoded.severity == "warning"
    assert ordinary.severity == "info"
    assert ordinary.paint_channel == "stroke"


def test_encoded_fill_policy_override_applies_to_encoded_unsupported_ground_only():
    top = _primitive("unreadable", "unclassified", "panel", "#101010", order=90,
                     bounds={"inline": 0, "block": 0, "inlineSize": 60, "blockSize": 40})
    top["paint"]["gradient"] = {"invalid": True}
    scene = _encoded_scene(_dark_host(), top, _encoded_mark())
    findings = evaluate_scene_contrast(
        scene, policy={"mark": "error", "unsupportedGround": "error"},
        encoded_fill_policy={"mark": "warning", "unsupportedGround": "warning"})

    encoded = next(item for item in findings if item.encoding is not None)
    ordinary = next(item for item in findings
                    if item.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED" and item.encoding is None)
    assert encoded.code == "W_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert encoded.severity == "warning"
    assert ordinary.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert ordinary.severity == "error"

    inherited = evaluate_scene_contrast(scene, policy={"mark": "none", "unsupportedGround": "error"})
    inherited_encoded = next(item for item in inherited if item.encoding is not None)
    assert inherited_encoded.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert inherited_encoded.severity == "error"


def test_encoded_fill_uses_completed_opacity_and_reports_unsupported_ground():
    translucent = _encoded_mark()
    translucent["paint"]["opacity"] = 0.5
    scene = _encoded_scene(_dark_host(), translucent)
    finding = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "warning"})
                   if item.code == "W_SCENE_ENCODING_CONTRAST")
    assert finding.ground_id == "host"
    assert finding.contrast_ratio < 3.0

    # A malformed top host is not skipped in favour of the lower opaque panel.
    top = _primitive("unreadable", "unclassified", "panel", "#101010", order=90,
                     bounds={"inline": 0, "block": 0, "inlineSize": 60, "blockSize": 40})
    top["paint"]["gradient"] = {"invalid": True}
    unsupported = evaluate_scene_contrast(_encoded_scene(_dark_host(), top, _encoded_mark()),
                                          policy={"mark": "warning", "unsupportedGround": "warning"})
    ground = next(item for item in unsupported if item.code == "W_SCENE_CONTRAST_GROUND_UNSUPPORTED"
                  and item.primitive_id == "encoded")
    assert ground.encoding.as_mapping() == _encoding_witness()


def test_malformed_or_unjoined_encoding_witness_is_structural():
    malformed = _encoded_mark()
    malformed["encoding"] = {"channel": "stroke"}
    with pytest.raises(ValueError, match="E_SCENE_CONTRAST_DOCUMENT: malformed encoding witness"):
        evaluate_scene_contrast(_encoded_scene(malformed))

    missing_resource = _encoded_mark()
    missing_resource["encoding"]["sources"][0]["id"] = "unknown-view"
    with pytest.raises(ValueError, match="encoding source does not join"):
        evaluate_scene_contrast(_encoded_scene(missing_resource))

    wrong_version = _encoded_mark()
    with pytest.raises(ValueError, match="encoding metadata requires Scene v0.7"):
        evaluate_scene_contrast(_scene(wrong_version))


@pytest.mark.parametrize("kind,visual_role,purpose", [
    ("Rect", "unclassified", "panel"),
    ("Text", "planned", "planned"),
])
def test_encoding_witness_on_non_mark_or_non_shape_is_structural(kind, visual_role, purpose):
    primitive = _encoded_mark()
    primitive.update(kind=kind, visualRole=visual_role, purpose=purpose)

    with pytest.raises(
        ValueError,
        match="E_SCENE_CONTRAST_DOCUMENT: encoding metadata requires a completed filled MARK-classified",
    ):
        evaluate_scene_contrast(_encoded_scene(primitive))


def test_style_encoding_witness_is_self_contained_and_joins_resource_without_style_match():
    mark = _encoded_mark()
    mark["encoding"] = {"channel": "fill", "scaleId": "status-colors", "field": "status", "value": "gate",
                         "sources": [{"kind": "style", "id": "style-a", "sourceRef": "/body/rules/then",
                                      "ruleId": "encode-status"}]}
    scene = _encoded_scene(_dark_host(), mark)
    scene["provenance"]["resources"] = [{"kind": "style", "id": "style-a"}]

    finding = next(item for item in evaluate_scene_contrast(scene, policy={"mark": "warning"})
                   if item.code == "W_SCENE_ENCODING_CONTRAST")
    assert finding.encoding.sources[0].rule_id == "encode-status"

    mark["encoding"]["sources"][0].pop("ruleId")
    with pytest.raises(ValueError, match="malformed encoding witness"):
        evaluate_scene_contrast(scene, policy={"mark": "warning"})

    mark["encoding"]["sources"][0]["ruleId"] = "encode-status"
    mark["encoding"]["sources"][0]["id"] = "missing-style"
    with pytest.raises(ValueError, match="encoding source does not join exactly one Scene resource"):
        evaluate_scene_contrast(scene, policy={"mark": "warning"})


def test_category_fill_can_be_carried_by_a_contrasting_explicit_outline():
    finding = evaluate_scene_contrast(_scene(
        _primitive("panel", "unclassified", "panel", "#E8EFFA", order=10),
        _primitive("planned", "planned", "planned", "#E8EFFA", stroke="#172033", order=100),
    ))[0]
    assert finding.severity == "info"
    assert finding.paint_channel == "stroke"
    assert finding.ground_id == "panel"
    assert (finding.sample_inline, finding.sample_block) == (10, 15)


def test_catalog_pattern_checks_substrate_and_ink_pairs_independently_with_density():
    pattern = {"tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45,
               "densityBasisPoints": 1250, "primitives": [{"kind": "rect", "x": 0, "y": 0,
               "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
               "regionBounds": {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
               "clipBounds": {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
               "cornerRadius": 0}
    primitive = _primitive("pattern", "progress-fill", "progress-fill", "#FFFFFF", order=20,
                           bounds={"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10})
    primitive["paint"]["stroke"] = "#000000"
    primitive["pattern"] = pattern
    findings = evaluate_scene_contrast(_scene(primitive, version="chrona/scene/v0.7"))
    assert len(findings) == 3
    by_pair = {(item.paint_channel, item.ground_kind): item for item in findings}
    substrate = by_pair[("fill", "canvas")]
    # #1658: the substrate matches the canvas, but the black ink clears the floor on it, so the mark is judged
    # by its strongest ink and the substrate pair reports without failing.
    assert substrate.contrast_ratio == 1.0 and substrate.severity == "info"
    assert by_pair[("stroke", "pattern-substrate")].severity == "info"
    assert by_pair[("stroke", "canvas")].severity == "info"
    assert all(item.as_mapping()["densityBasisPoints"] == 1250 for item in findings)


def test_catalog_pattern_checks_host_substrate_and_host_ink_with_effective_paints():
    host = _primitive("host", "unclassified", "panel", "#333333", order=10,
                      bounds={"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10})
    primitive = _primitive("pattern", "progress-fill", "progress-fill", "#EEEEEE", order=20,
                           bounds={"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10})
    primitive["paint"]["stroke"] = "#111111"
    primitive["pattern"] = {
        "tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45,
        "densityBasisPoints": 1250, "primitives": [{"kind": "rect", "x": 0, "y": 0,
        "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
        "regionBounds": {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
        "clipBounds": {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10},
        "cornerRadius": 0,
    }

    findings = evaluate_scene_contrast(_scene(host, primitive, version="chrona/scene/v0.7"))
    by_pair = {(item.paint_channel, item.ground_id): item for item in findings}
    assert set(by_pair) == {("fill", "host"), ("stroke", "pattern"), ("stroke", "host")}
    assert (by_pair[("fill", "host")].ground_color,
            by_pair[("fill", "host")].ground_kind) == ("#333333", "flat")
    assert (by_pair[("stroke", "pattern")].ground_color,
            by_pair[("stroke", "pattern")].ground_kind) == ("#EEEEEE", "pattern-substrate")
    assert (by_pair[("stroke", "host")].ground_color,
            by_pair[("stroke", "host")].ground_kind) == ("#333333", "flat")
    assert all(item.density_basis_points == 1250 for item in findings)


def test_v06_pattern_policy_result_remains_the_legacy_single_best_candidate():
    primitive = _primitive("pattern", "progress-fill", "progress-fill", "#FFFFFF", order=20)
    primitive["paint"]["stroke"] = "#000000"
    primitive["paint"]["strokeWidth"] = 1
    primitive["pattern"] = {"kind": "diagonal-hatch"}
    findings = evaluate_scene_contrast(_scene(primitive))
    assert len(findings) == 1
    assert findings[0].paint_channel == "stroke"
