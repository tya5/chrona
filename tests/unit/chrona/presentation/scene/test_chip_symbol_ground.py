"""Chip Symbol grounds are judged from painted paths, not their enclosing bounds."""
from __future__ import annotations

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import blend_over


WHITE = "#FFFFFF"
BLACK = "#000000"
TEXT_BOUNDS = {"inline": 4.0, "block": 4.0, "inlineSize": 2.0, "blockSize": 2.0}
CHIP_BOUNDS = {"inline": 0.0, "block": 0.0, "inlineSize": 10.0, "blockSize": 10.0}


def _path(points):
    return [{"kind": "move", "points": [points[0]]},
            *({"kind": "line", "points": [point]} for point in points[1:])]


def _symbol(identifier, fill, points, *, order, opacity=1, outline=None):
    return {
        "id": identifier, "kind": "Symbol", "sourceRef": "label-1", "sourceKind": "review",
        "purpose": "label-chip", "visualRole": "member-label-chip", "paintOrder": order,
        "bounds": dict(CHIP_BOUNDS), "paint": {"fill": fill, "opacity": opacity},
        "symbol": {"outline": _path(points) if outline is None else outline},
    }


def _rect(identifier, fill, *, order, opacity=1):
    return {
        "id": identifier, "kind": "Rect", "sourceRef": identifier, "sourceKind": "decoration",
        "purpose": "label-chip", "visualRole": "member-label-chip", "paintOrder": order,
        "bounds": dict(CHIP_BOUNDS), "paint": {"fill": fill, "opacity": opacity},
    }


def _label(fill=BLACK):
    return {
        "id": "text:label-1", "kind": "Text", "sourceRef": "view:label-1", "sourceKind": "review",
        "purpose": "as-of-label", "visualRole": "text", "paintOrder": 200,
        "bounds": dict(TEXT_BOUNDS), "paint": {"fill": fill, "opacity": 1},
    }


def _scene(*primitives, canvas=WHITE):
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": canvas, "opacity": 1},
        "primitives": list(primitives), "decorationDispositions": [],
    }]}


def _text_finding(*primitives, canvas=WHITE):
    findings = [item for item in evaluate_scene_contrast(_scene(*primitives, canvas=canvas))
                if item.primitive_id == "text:label-1"]
    assert len(findings) == 1, findings
    return findings[0]


def test_later_chip_symbol_uses_actual_fill_and_does_not_cover_by_bbox_alone():
    # Both Symbols have the full chip bounds, but the later white fill is confined
    # to the right. The text sample (5, 5) is touched by the earlier black part only.
    earlier = _symbol("chip:label-1", BLACK,
                      [(0, 0), (6.5, 0), (6.5, 10), (0, 10), (0, 0)], order=100)
    later = _symbol("chip:label-1:part1", WHITE,
                    [(7, 0), (10, 0), (10, 10), (7, 10), (7, 0)], order=101)

    finding = _text_finding(earlier, later, _label())

    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == (
        "chip:label-1", BLACK, "flat")


def test_chip_symbol_nonzero_winding_hole_is_not_a_ground():
    outer = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    inner_reverse = [(3, 3), (3, 7), (7, 7), (7, 3), (3, 3)]
    outline = _path(outer) + _path(inner_reverse)
    chip = _symbol("chip:label-1", BLACK, (), order=100, outline=outline)

    finding = _text_finding(chip, _label())

    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == (
        "canvas", WHITE, "canvas")


def test_overlapping_translucent_chip_symbol_parts_composite_in_paint_order():
    lower = _symbol("chip:label-1", BLACK,
                    [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], order=100, opacity=0.5)
    upper = _symbol("chip:label-1:part1", "#0000FF",
                    [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], order=101, opacity=0.5)

    finding = _text_finding(lower, upper, _label("#FFFF00"))
    expected = blend_over(ink="#0000FF", opacity=0.5,
                          ground=blend_over(ink=BLACK, opacity=0.5, ground=WHITE))

    assert (finding.ground_id, finding.ground_color) == ("chip:label-1:part1", expected)
    assert finding.ground_kind == "translucent-over-translucent-over-canvas"


def test_malformed_chip_symbol_outline_that_could_cover_sample_fails_closed():
    malformed = _symbol("chip:label-1", BLACK, (), order=100, outline=[])

    finding = _text_finding(malformed, _label())

    assert (finding.code, finding.severity, finding.severity_class, finding.ground_id) == (
        "E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", "legibility", "chip:label-1")


def test_rectangular_chip_ground_keeps_existing_bounds_and_blend_behavior():
    finding = _text_finding(_rect("chip:label-1", BLACK, order=100, opacity=0.5), _label("#FFFF00"))
    expected = blend_over(ink=BLACK, opacity=0.5, ground=WHITE)

    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == (
        "chip:label-1", expected, "translucent-over-canvas")
