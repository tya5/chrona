"""Frame glyph ink is sparse ground in paint order, not a slot-sized host."""
from __future__ import annotations

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import blend_over


PAPER = "#F2E8D0"
INK = "#231A14"
TEXT = "#231A14"
BOX = {"inline": 0.0, "block": 0.0, "inlineSize": 100.0, "blockSize": 100.0}


def _scene(*primitives):
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": PAPER, "opacity": 1.0},
        "primitives": list(primitives), "decorationDispositions": [],
    }]}


def _outline(paths):
    commands = []
    for points in paths:
        commands.append({"kind": "move", "points": [list(points[0])]})
        commands.extend({"kind": "line", "points": [list(point)]} for point in points[1:])
        commands.append({"kind": "line", "points": [list(points[0])]})
    return {"outline": commands}


RING = _outline((
    ((0, 0), (100, 0), (100, 100), (0, 100)),
    ((25, 25), (25, 75), (75, 75), (75, 25)),
))


def _frame(*, identifier="frame-part", order=10, source="slot-a", outline=RING,
           fill=INK, opacity=1.0, stroke=None, stroke_width=None, role="frame-glyph"):
    paint = {"opacity": opacity}
    if fill is not None:
        paint["fill"] = fill
    if stroke is not None:
        paint.update(stroke=stroke, strokeWidth=stroke_width or 2.0)
    return {"id": identifier, "kind": "Symbol", "sourceRef": source,
            "visualRole": role, "purpose": role, "paintOrder": order,
            "bounds": dict(BOX), "paint": paint, "symbol": outline}


def _text(*, identifier="title", order=50, source="content-b", bounds=None, fill=TEXT):
    return {"id": identifier, "kind": "Text", "sourceRef": source,
            "visualRole": "heading", "purpose": "title-text", "paintOrder": order,
            "bounds": bounds or {"inline": 40.0, "block": 40.0, "inlineSize": 20.0, "blockSize": 10.0},
            "contrastTreatment": "required", "paint": {"fill": fill, "opacity": 1.0}}


def _finding(*primitives, identifier="title"):
    values = [item for item in evaluate_scene_contrast(_scene(*primitives)) if item.primitive_id == identifier]
    assert len(values) == 1, values
    return values[0]


def test_ring_hole_is_not_a_frame_ground_but_actual_ring_contact_is():
    frame = _frame()
    in_hole = _finding(frame, _text())
    on_ring = _finding(frame, _text(bounds={"inline": 5.0, "block": 40.0,
                                           "inlineSize": 15.0, "blockSize": 10.0}))

    assert (in_hole.ground_color, in_hole.ground_kind, in_hole.severity) == (PAPER, "canvas", "info")
    assert (on_ring.ground_id, on_ring.ground_color, on_ring.ground_kind, on_ring.severity) == (
        "frame-part", INK, "frame-glyph-ink", "error")


def test_frame_ink_is_selected_across_source_identity_and_stroke_contact_is_geometric():
    stroke_outline = _outline((((0, 50), (100, 50)),))
    frame = _frame(outline=stroke_outline, fill=None, stroke=INK, stroke_width=2.0)
    hit = _finding(frame, _text(bounds={"inline": 40.0, "block": 49.0,
                                       "inlineSize": 20.0, "blockSize": 2.0}))
    miss = _finding(frame, _text(bounds={"inline": 40.0, "block": 65.0,
                                        "inlineSize": 20.0, "blockSize": 5.0}))

    assert (hit.ground_id, hit.ground_kind, hit.severity) == ("frame-part", "frame-glyph-ink", "error")
    assert (miss.ground_color, miss.ground_kind, miss.severity) == (PAPER, "canvas", "info")


def test_later_opaque_host_hides_frame_but_translucent_host_composites_over_it():
    frame = _frame()
    opaque = {"id": "panel", "kind": "Rect", "sourceRef": "panel", "visualRole": "panel",
              "purpose": "panel", "paintOrder": 20, "bounds": dict(BOX),
              "paint": {"fill": PAPER, "opacity": 1.0}}
    translucent = {**opaque, "paint": {"fill": "#FFFFFF", "opacity": 0.5}}
    on_ring = {"inline": 5.0, "block": 40.0, "inlineSize": 15.0, "blockSize": 10.0}

    hidden = _finding(frame, opaque, _text(order=30, bounds=on_ring))
    composite = _finding(frame, translucent, _text(order=30, bounds=on_ring))
    above_host = _finding({**translucent, "paintOrder": 10}, _frame(order=20),
                          _text(order=30, bounds=on_ring))

    assert (hidden.ground_id, hidden.ground_color, hidden.ground_kind, hidden.severity) == (
        "panel", PAPER, "flat", "info")
    assert composite.ground_kind == "translucent-over-frame-glyph-ink"
    assert composite.ground_id == "panel"
    assert composite.ground_color != PAPER
    assert (above_host.ground_id, above_host.ground_kind, above_host.ground_color) == (
        "frame-part", "frame-glyph-ink", INK)


def _cone(order):
    outline = _outline((((50, 0), (200, 100), (-100, 100)),))
    return {"id": "cone", "kind": "Symbol", "sourceRef": "axis", "visualRole": "as-of-cone",
            "purpose": "as-of-cone", "paintOrder": order,
            "bounds": {"inline": -100.0, "block": 0.0, "inlineSize": 300.0, "blockSize": 100.0},
            "symbol": outline,
            "paint": {"fill": "#FFFFFF", "opacity": 1.0, "gradient": {
                "start": [50.0, 0.0], "end": [50.0, 100.0], "fidelity": "required",
                "stops": [{"offset": 0.0, "color": "#FFFFFF", "opacity": 1.0},
                          {"offset": 1.0, "color": "#FFFFFF", "opacity": 1.0}]}}}


def test_cone_before_frame_tints_its_backdrop_not_frame_ink_and_cone_after_tints_both():
    frame = _frame(order=20)
    subject = _text(order=50, bounds={"inline": 5.0, "block": 40.0,
                                      "inlineSize": 15.0, "blockSize": 10.0})
    before = _finding(_cone(10), frame, subject)
    after = _finding(frame, _cone(30), subject)

    assert (before.ground_id, before.ground_color, before.ground_kind) == (
        "frame-part", INK, "frame-glyph-ink")
    assert (after.ground_id, after.ground_color, after.ground_kind, after.severity) == (
        "cone", "#FFFFFF", "cone-blend", "info")


def test_decoration_keeps_dominant_substrate_instead_of_frame_ink():
    decoration = {"id": "stripe", "kind": "Rect", "sourceRef": "content-b",
                  "visualRole": "row-band", "purpose": "row-decoration", "paintOrder": 50,
                  "bounds": {"inline": 5.0, "block": 40.0, "inlineSize": 15.0, "blockSize": 10.0},
                  "paint": {"fill": "#DDDDEE", "opacity": 1.0}}
    finding = _finding(_frame(), decoration, identifier="stripe")
    assert (finding.ground_color, finding.ground_kind) == (PAPER, "canvas")


def test_no_frame_keeps_existing_canvas_ground_result():
    without = _finding(_text())
    assert (without.ground_id, without.ground_color, without.ground_kind, without.severity) == (
        "canvas", PAPER, "canvas", "info")


def test_translucent_frame_ink_is_composited_over_its_actual_ground():
    finding = _finding(_frame(opacity=0.5), _text(bounds={"inline": 5.0, "block": 40.0,
                                                         "inlineSize": 15.0, "blockSize": 10.0}))
    assert finding.ground_id == "frame-part"
    assert finding.ground_kind == "frame-glyph-ink"
    assert finding.ground_color == blend_over(ink=INK, opacity=0.5, ground=PAPER)


def test_touching_frame_part_with_unreadable_outline_fails_closed():
    malformed = _frame(outline={"outline": [{"kind": "line", "points": []}]})
    finding = _finding(malformed, _text(bounds={"inline": 5.0, "block": 40.0,
                                                "inlineSize": 15.0, "blockSize": 10.0}))
    assert finding.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert finding.severity == "error"


def test_named_frame_glyph_family_and_same_paint_order_document_precedence_are_selected():
    frame = _frame(order=50, role="frame-glyph-crest")
    label = _text(order=50, bounds={"inline": 5.0, "block": 40.0,
                                    "inlineSize": 15.0, "blockSize": 10.0})
    finding = _finding(frame, label)
    assert (finding.ground_id, finding.ground_color, finding.ground_kind, finding.severity) == (
        "frame-part", INK, "frame-glyph-ink", "error")
