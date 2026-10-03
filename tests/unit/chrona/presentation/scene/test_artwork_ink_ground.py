"""#848: the ink of a vector artwork behind an annotation is a ground for the text it touches, and only that.

The artwork is a few sibling `annotation-artwork` Symbol parts over the note box. Their bounds are the whole note,
so the gate never takes a part as a host by bounds (the frame ring would be the ground of every line in its hole);
it adds a part's ink as one more ground exactly where the part's painted area meets the label. Hand-built Scene
documents; no `examples/` input.
"""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import blend_over, composited_contrast

PAPER = "#F2E8D0"
DARK = "#2A1C12"
WOOD = "#C9B48C"
TEXT = "#231A14"
NOTE = {"inline": 0.0, "block": 0.0, "inlineSize": 100.0, "blockSize": 60.0}
IN_HOLE = {"inline": 20.0, "block": 20.0, "inlineSize": 60.0, "blockSize": 20.0}
ON_RING = {"inline": 4.0, "block": 20.0, "inlineSize": 40.0, "blockSize": 20.0}


def _scene(*primitives):
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": "#0E2B31", "opacity": 1}, "primitives": list(primitives),
        "decorationDispositions": []}]}


def _box(*, order=400, source="n1", fill=PAPER, opacity=1):
    return {"id": f"annotation-box:{source}", "kind": "Rect", "sourceRef": source, "visualRole": "annotation-note-box",
            "purpose": "annotation-box", "paintOrder": order, "bounds": dict(NOTE),
            "paint": {"fill": fill, "opacity": opacity}}


def _outline(commands):
    return {"outline": [{"kind": kind, "points": [list(point) for point in points]} for kind, *points in commands]}


def _closed(points):
    first, *rest = points
    return [("move", first), *(("line", point) for point in rest), ("line", first)]


RING = _closed([(0, 0), (100, 0), (100, 60), (0, 60)]) + _closed([(10, 10), (10, 50), (90, 50), (90, 10)])


def _part(identifier="annotation-artwork:n1:part0", *, commands=RING, ink=DARK, opacity=1, order=400, source="n1",
          stroke_width=None, role="annotation-artwork"):
    paint = ({"stroke": ink, "strokeWidth": stroke_width, "opacity": opacity} if stroke_width is not None
             else {"fill": ink, "opacity": opacity})
    return {"id": identifier, "kind": "Symbol", "sourceRef": source, "visualRole": role,
            "purpose": "annotation-artwork", "paintOrder": order, "bounds": dict(NOTE), "paint": paint,
            "symbol": _outline(commands)}


def _prose(*, bounds=IN_HOLE, fill=TEXT, order=401, source="n1", identifier="label"):
    return {"id": identifier, "kind": "Text", "sourceRef": source, "visualRole": "annotation-note-text",
            "purpose": "annotation-text", "paintOrder": order, "bounds": dict(bounds), "contrastTreatment": "required",
            "paint": {"fill": fill, "opacity": 1}}


def _header(*, bounds=IN_HOLE, fill=TEXT, order=401, source="n1", identifier="label"):
    return {"id": identifier, "kind": "Text", "sourceRef": source, "visualRole": "annotation-kind-label",
            "purpose": "annotation-kind-label", "paintOrder": order, "bounds": dict(bounds),
            "contrastTreatment": "required", "paint": {"fill": fill, "opacity": 1}}


def _judge(*primitives, identifier="label"):
    findings = [item for item in evaluate_scene_contrast(_scene(*primitives)) if item.primitive_id == identifier]
    assert len(findings) == 1, findings
    return findings[0]


def _ratio(ink, ground):
    return composited_contrast(fill=ink, opacity=1.0, ground=ground)


# --- a part is not a host by bounds ----------------------------------------------------------------------------

def test_text_in_the_hole_of_a_frame_is_judged_on_the_paper_not_on_the_ring_whose_bounds_cover_it():
    finding = _judge(_box(), _part(), _prose())
    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == ("annotation-box:n1", PAPER, "flat")
    assert finding.contrast_ratio == pytest.approx(_ratio(TEXT, PAPER))
    assert finding.severity == "info"


def test_dark_ink_the_colour_of_the_text_does_not_fail_text_that_never_touches_it():
    # Ink and text are the same colour: were the ring the ground by bounds, the ratio would be 1.0.
    finding = _judge(_box(), _part(ink=TEXT), _prose())
    assert finding.severity == "info" and finding.ground_kind == "flat"


def test_a_header_with_no_bar_in_the_hole_is_judged_on_the_note_box_too():
    finding = _judge(_box(), _part(), _header())
    assert (finding.ground_id, finding.ground_kind, finding.severity) == ("annotation-box:n1", "flat", "info")


# --- ink is a ground where it is touched ---------------------------------------------------------------------

def test_text_that_touches_the_ring_is_judged_on_the_ink_and_fails_when_it_vanishes_there():
    finding = _judge(_box(), _part(ink=TEXT), _prose(bounds=ON_RING))
    assert (finding.ground_id, finding.ground_kind, finding.ground_color) == (
        "annotation-artwork:n1:part0", "artwork-ink", TEXT)
    assert finding.contrast_ratio == pytest.approx(1.0)
    assert (finding.code, finding.severity, finding.severity_class) == (
        "E_SCENE_STATE_TEXT_CONTRAST", "error", "legibility")


def test_text_that_touches_the_ring_passes_when_it_is_legible_on_the_paper_and_on_the_ink():
    finding = _judge(_box(), _part(ink=WOOD), _prose(bounds=ON_RING))
    assert finding.severity == "info"
    # The worst of the two grounds decides.
    assert finding.contrast_ratio == pytest.approx(min(_ratio(TEXT, PAPER), _ratio(TEXT, WOOD)))
    assert finding.ground_kind == "artwork-ink" and finding.ground_color == WOOD


def test_the_header_that_touches_the_ring_is_judged_on_the_ink_as_well():
    finding = _judge(_box(), _part(ink=TEXT), _header(bounds=ON_RING))
    assert (finding.ground_kind, finding.severity) == ("artwork-ink", "error")


def test_a_translucent_ink_is_composited_over_the_paper():
    finding = _judge(_box(), _part(ink=DARK, opacity=0.5), _prose(bounds=ON_RING))
    composite = blend_over(ink=DARK, opacity=0.5, ground=PAPER)
    assert (finding.ground_kind, finding.ground_color) == ("artwork-ink", composite)
    assert finding.contrast_ratio == pytest.approx(min(_ratio(TEXT, PAPER), _ratio(TEXT, composite)))


def test_a_stroke_part_is_a_ground_within_half_its_width_and_not_beyond():
    line = [("move", (5, 0)), ("line", (5, 60))]
    near = {"inline": 6.5, "block": 20.0, "inlineSize": 30.0, "blockSize": 10.0}
    far = {"inline": 7.5, "block": 20.0, "inlineSize": 30.0, "blockSize": 10.0}
    touching = _judge(_box(), _part(commands=line, ink=TEXT, stroke_width=4), _prose(bounds=near))
    clear = _judge(_box(), _part(commands=line, ink=TEXT, stroke_width=4), _prose(bounds=far))
    assert (touching.ground_kind, touching.severity) == ("artwork-ink", "error")
    assert (clear.ground_kind, clear.severity) == ("flat", "info")


def test_a_frame_without_a_hole_is_ground_everywhere_so_the_hole_is_what_keeps_the_paper_clear():
    solid = _closed([(0, 0), (100, 0), (100, 60), (0, 60)])
    finding = _judge(_box(), _part(commands=solid, ink=TEXT), _prose())
    assert (finding.ground_kind, finding.severity) == ("artwork-ink", "error")


def test_every_touched_part_is_a_ground_and_the_worst_decides():
    left_bar = _closed([(0, 0), (10, 0), (10, 60), (0, 60)])
    other = _part("annotation-artwork:n1:part1", commands=left_bar, ink=TEXT)
    finding = _judge(_box(), _part(ink=WOOD), other, _prose(bounds=ON_RING))
    assert (finding.ground_id, finding.severity) == ("annotation-artwork:n1:part1", "error")


# --- what the artwork does not reach ---------------------------------------------------------------------------

def test_another_notes_artwork_is_not_this_notes_ground():
    finding = _judge(_box(), _part(source="n2", ink=TEXT), _prose(bounds=ON_RING))
    assert (finding.ground_kind, finding.severity) == ("flat", "info")


def test_an_artwork_painted_after_the_text_is_not_beneath_it():
    finding = _judge(_box(), _prose(bounds=ON_RING), _part(order=402, ink=TEXT))
    assert finding.ground_kind == "flat"


def test_a_decoration_over_the_artwork_keeps_the_dominant_substrate_model():
    bar = {"id": "bar", "kind": "Rect", "sourceRef": "n1", "visualRole": "annotation-kind-bar",
           "purpose": "annotation-kind-bar", "paintOrder": 400, "bounds": dict(ON_RING),
           "paint": {"fill": TEXT, "opacity": 1}}
    finding = _judge(_box(), _part(ink=TEXT), bar, identifier="bar")
    assert (finding.ground_id, finding.ground_kind, finding.severity_class) == ("annotation-box:n1", "flat", "decoration")


def test_a_part_that_cannot_be_read_fails_closed_for_the_text_of_its_note():
    broken = {k: v for k, v in _part().items() if k != "symbol"}
    finding = _judge(_box(), broken, _prose())
    assert (finding.code, finding.severity) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error")
    assert finding.ground_id == "annotation-artwork:n1:part0"


def test_a_touching_part_with_an_unreadable_opacity_fails_closed():
    finding = _judge(_box(), _part(opacity=2), _prose(bounds=ON_RING))
    assert (finding.code, finding.severity) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error")


def test_note_prose_still_needs_its_own_opaque_flat_box_with_artwork_present():
    finding = _judge(_box(opacity=0.5), _part(), _prose())
    assert (finding.code, finding.ground_id) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "annotation-box:n1")


def test_the_paper_decides_when_it_is_the_worse_ground_of_a_touching_label():
    # Pale text is legible on the dark ink but not on the paper: the substrate is still a ground.
    finding = _judge(_box(), _part(ink=DARK), _prose(bounds=ON_RING, fill="#EFE5CC"))
    assert (finding.ground_id, finding.ground_kind, finding.severity) == ("annotation-box:n1", "flat", "error")


def test_a_part_with_a_malformed_outline_fails_closed():
    broken = {**_part(), "symbol": {"outline": [{"kind": "arc", "points": [[0, 0]]}]}}
    finding = _judge(_box(), broken, _prose())
    assert (finding.code, finding.severity, finding.ground_id) == (
        "E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", "annotation-artwork:n1:part0")


def test_the_verdict_is_deterministic():
    scene = _scene(_box(), _part(ink=WOOD), _prose(bounds=ON_RING))
    assert evaluate_scene_contrast(scene) == evaluate_scene_contrast(scene)
