"""#584 A584-3: the tilt rule and the rigid rotation of completed note geometry (pure, no Theme or Project)."""
from __future__ import annotations

from decimal import Decimal
from math import cos, hypot, radians, sin

import pytest

from chrona.presentation.layout.annotation_tilt import (
    nearest_boundary_point, polygon_commands, rotate_point, rotate_shape, rotate_text, rotated_corners,
    rotated_extent, tilt_for,
)
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import PathCommand, ShapePlacement, TextPlacement
from chrona.presentation.scene.model import TextLayout

CENTER = (100.0, 50.0)


def _rect(x, y, w, h) -> Rect:
    return Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(w)), Decimal(str(h)))


def test_the_angle_of_a_position_is_the_declared_list_cycled():
    assert [tilt_for([1, -2, 3], position) for position in range(7)] == [1.0, -2.0, 3.0, 1.0, -2.0, 3.0, 1.0]
    assert [tilt_for([2.5], position) for position in range(3)] == [2.5, 2.5, 2.5]
    assert tilt_for([Decimal("1.5"), Decimal("-1.5")], 1) == -1.5


def test_a_missing_or_empty_declaration_is_no_tilt():
    assert tilt_for(None, 0) == 0.0 and tilt_for([], 5) == 0.0 and tilt_for([0], 3) == 0.0


def test_the_angle_is_rounded_to_two_decimals():
    assert tilt_for([1.23456], 0) == 1.23


def test_a_positive_angle_turns_clockwise_in_the_block_down_frame():
    x, y = rotate_point((110.0, 50.0), CENTER, 90.0)  # a point to the right of the centre swings down
    assert (round(x, 9), round(y, 9)) == (100.0, 60.0)
    assert rotate_point((120.0, 20.0), CENTER, 0.0) == (120.0, 20.0)


def test_rotation_preserves_the_distance_to_the_centre():
    point = (130.0, 20.0)
    for degrees in (-15.0, -3.5, 4.0, 15.0):
        rotated = rotate_point(point, CENTER, degrees)
        assert hypot(rotated[0] - CENTER[0], rotated[1] - CENTER[1]) == pytest.approx(hypot(30, 30))


def test_the_rotated_extent_is_the_axis_aligned_size_of_the_rotated_frame():
    assert rotated_extent(200.0, 80.0, 0.0) == (200.0, 80.0)
    width, height = rotated_extent(200.0, 80.0, 90.0)
    assert (round(width, 9), round(height, 9)) == (80.0, 200.0)
    angle = radians(10.0)
    assert rotated_extent(200.0, 80.0, 10.0) == pytest.approx(
        (200 * cos(angle) + 80 * sin(angle), 200 * sin(angle) + 80 * cos(angle)))
    assert rotated_extent(200.0, 80.0, -10.0) == pytest.approx(rotated_extent(200.0, 80.0, 10.0))


def test_the_rotated_extent_contains_every_corner_of_the_rotated_frame():
    corners = rotated_corners(60.0, 20.0, 80.0, 60.0, CENTER, 12.0)
    width, height = rotated_extent(80.0, 60.0, 12.0)
    assert max(x for x, _ in corners) - min(x for x, _ in corners) == pytest.approx(width)
    assert max(y for _, y in corners) - min(y for _, y in corners) == pytest.approx(height)


def _shape(kind="Rect", **extra) -> ShapePlacement:
    return ShapePlacement("annotation-box:a", "a", kind, _rect(60, 20, 80, 60), semantic_id="annotationNoteBox",
                          paint_order=400, **extra)


def test_a_rect_becomes_a_closed_polygon_with_the_bounds_of_the_rotation():
    rotated = rotate_shape(_shape(), CENTER, 10.0)
    assert rotated.kind == "Tilt" and rotated.semantic_id == "annotationNoteBox" and rotated.paint_order == 400
    kinds = [command.kind for command in rotated.path_commands]
    assert kinds == ["move", "line", "line", "line", "line"]
    assert rotated.path_commands[-1].points == rotated.path_commands[0].points  # closed
    width, height = rotated_extent(80.0, 60.0, 10.0)
    assert (float(rotated.bounds.inline_size), float(rotated.bounds.block_size)) == pytest.approx((width, height))
    # The AABB is centred on the rotation centre, as the search placed it.
    assert float(rotated.bounds.inline) + float(rotated.bounds.inline_size) / 2 == pytest.approx(CENTER[0])
    assert float(rotated.bounds.block) + float(rotated.bounds.block_size) / 2 == pytest.approx(CENTER[1])


def test_a_glyph_keeps_its_parts_and_rotates_their_points():
    part = SymbolPartPlacement((PathCommand("move", ((70.0, 30.0),)), PathCommand("quadratic", ((90.0, 30.0), (90.0, 50.0)))),
                               "stroke", None, 1.5, "round", "round")
    shape = _shape("Glyph", symbol_parts=(part,))
    rotated = rotate_shape(shape, CENTER, 8.0)
    assert rotated.kind == "Glyph" and len(rotated.symbol_parts) == 1
    moved = rotated.symbol_parts[0]
    assert (moved.paint_mode, moved.stroke_width, moved.line_cap) == ("stroke", 1.5, "round")
    assert moved.commands[0].points[0] == pytest.approx(rotate_point((70.0, 30.0), CENTER, 8.0))
    assert moved.commands[1].points[1] == pytest.approx(rotate_point((90.0, 50.0), CENTER, 8.0))


def test_an_unknown_shape_kind_is_not_silently_left_unrotated():
    with pytest.raises(ValueError, match="E_LAYOUT_ANNOTATION_TILT_SHAPE"):
        rotate_shape(_shape("Balloon"), CENTER, 5.0)


def _text(**extra) -> TextPlacement:
    return TextPlacement("annotation-text:a", "a", "hello", _rect(60, 20, 60, 20), "annotation-note-text",
                         baseline=(60.0, 34.0), lines=("hello",), **extra)


def test_a_text_run_rotates_rigidly_about_the_centre():
    rotated = rotate_text(_text(), CENTER, 6.0)
    assert rotated.orientation == "tilt" and rotated.rotation_degrees == 6.0
    assert rotated.baseline == pytest.approx(rotate_point((60.0, 34.0), CENTER, 6.0))
    assert rotated.lines == ("hello",) and rotated.content == "hello"
    corners = rotated_corners(60.0, 20.0, 60.0, 20.0, CENTER, 6.0)
    assert float(rotated.bounds.inline) == pytest.approx(min(x for x, _ in corners))
    assert float(rotated.bounds.block_size) == pytest.approx(max(y for _, y in corners) - min(y for _, y in corners))


def test_only_a_horizontal_text_with_a_baseline_can_tilt():
    with pytest.raises(ValueError, match="E_LAYOUT_ANNOTATION_TILT_TEXT"):
        rotate_text(_text(orientation="rotate-cw", rotation_degrees=90), CENTER, 5.0)
    with pytest.raises(ValueError, match="E_LAYOUT_ANNOTATION_TILT_TEXT"):
        rotate_text(TextPlacement("t", "a", "x", _rect(0, 0, 1, 1), "r"), CENTER, 5.0)


def test_the_nearest_boundary_point_of_a_polygon():
    square = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
    assert nearest_boundary_point(square, (5.0, -4.0)) == (5.0, 0.0)  # above the top edge
    assert nearest_boundary_point(square, (14.0, 5.0)) == (10.0, 5.0)  # right of the right edge
    assert nearest_boundary_point(square, (3.0, 4.0)) == (0.0, 4.0)  # inside: the nearest edge (left, 3 away)
    assert nearest_boundary_point(square, (-3.0, -4.0)) == (0.0, 0.0)  # past a corner


def test_a_polygon_is_closed_by_a_line_back_to_its_start():
    commands = polygon_commands(((0.0, 0.0), (4.0, 0.0), (4.0, 3.0)))
    assert [command.kind for command in commands] == ["move", "line", "line", "line"]
    assert commands[-1].points == ((0.0, 0.0),)


@pytest.mark.parametrize("degrees", [4.0, -3.0, 15.0, -15.0, 0.01])
def test_a_tilt_text_layout_accepts_a_small_non_zero_angle(degrees):
    layout = TextLayout((0.0, 0.0, 1.0, 1.0), (0.0, 1.0), ("x",), "f", 400, 10.0, 1.2, "id", orientation="tilt",
                        rotation_degrees=degrees)
    assert layout.rotation_degrees == degrees


@pytest.mark.parametrize("orientation, degrees", [
    ("tilt", 0), ("tilt", 15.5), ("tilt", -16), ("tilt", float("nan")), ("tilt", True),
    ("horizontal", 4.0), ("rotate-cw", 4.0), ("rotate-cw", 0),
])
def test_a_text_layout_rejects_any_other_rotation(orientation, degrees):
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextLayout((0.0, 0.0, 1.0, 1.0), (0.0, 1.0), ("x",), "f", 400, 10.0, 1.2, "id", orientation=orientation,
                   rotation_degrees=degrees)


def test_the_quarter_turns_are_unchanged():
    for orientation, degrees in (("horizontal", 0), ("rotate-cw", 90), ("rotate-ccw", -90)):
        assert TextLayout((0.0, 0.0, 1.0, 1.0), (0.0, 1.0), ("x",), "f", 400, 10.0, 1.2, "id", orientation=orientation,
                          rotation_degrees=degrees).rotation_degrees == degrees
