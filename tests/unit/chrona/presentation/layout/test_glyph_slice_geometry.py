"""#848: the nine-slice warp of a catalogue glyph. Hand-built glyphs; no catalogue or `examples/` input."""
from __future__ import annotations

import pytest

from chrona.presentation.layout.glyph_slice_geometry import slice_glyph_parts
from chrona.presentation.scene.ink_touch import fill_touches


def _glyph(width, height, *parts):
    return {"viewport": {"inlineSize": width, "blockSize": height}, "parts": list(parts)}


def _fill(data):
    return {"data": data, "paint": "fill"}


def _stroke(data, width=1.0, cap="round", join="miter"):
    return {"data": data, "paint": "stroke", "strokeWidth": width, "lineCap": cap, "lineJoin": join}


def _points(part):
    return [point for command in part.commands for point in command.points]


def _has(part, *targets):
    """Every target point is a vertex of the part (a boundary-crossing edge adds vertices between corners)."""
    points = _points(part)
    return all(any(abs(point[0] - target[0]) < 1e-6 and abs(point[1] - target[1]) < 1e-6 for point in points)
               for target in targets)


def _ref(value, source, destination):
    """Independent reference: the piecewise-linear map of one axis from four breakpoints."""
    for index in range(3):
        if source[index + 1] > source[index] and value <= source[index + 1] + 1e-9:
            return destination[index] + (value - source[index]) * (destination[index + 1] - destination[index]) / (
                source[index + 1] - source[index])
    return destination[3]


SQUARE = _glyph(30, 20, _fill("M 0 0 L 30 0 L 30 20 L 0 20 Z"))


def test_the_glyphs_own_size_is_the_identity_whatever_the_insets():
    for insets in ((0, 0, 0, 0), (5, 5, 5, 5), (3, 8, 2, 1)):
        (part,) = slice_glyph_parts(SQUARE, (10, 20, 30, 20), slice_insets=insets, unit_px=1)
        assert _has(part, (10, 20), (40, 20), (40, 40), (10, 40))


def test_fixed_borders_keep_their_authored_size_and_the_middle_takes_the_rest():
    glyph = _glyph(30, 20, _fill("M 5 5 L 25 5 L 25 15 L 5 15 Z"))
    (part,) = slice_glyph_parts(glyph, (0, 0, 100, 60), slice_insets=(5, 5, 5, 5), unit_px=2)
    # Left border 5 units = 10 px, right border 10 px, so the middle (5..25) fills 10..90; likewise 10..50 in y.
    assert _has(part, (10, 10), (90, 10), (90, 50), (10, 50))


def test_the_map_is_exact_for_a_point_in_every_cell():
    insets = (4, 6, 3, 5)
    glyph = _glyph(40, 30, _fill("M 1 1 L 39 1 L 39 29 L 1 29 Z"))
    box = (7, 9, 200, 120)
    (part,) = slice_glyph_parts(glyph, box, slice_insets=insets, unit_px=3)
    cols = ((0, 5, 34, 40), (7, 22, 7 + 200 - 18, 207))
    rows = ((0, 4, 27, 30), (9, 21, 9 + 120 - 9, 129))
    for sx, sy in [(1, 1), (39, 1), (39, 29), (1, 29)]:
        assert _has(part, (_ref(sx, *cols), _ref(sy, *rows)))


def test_a_line_crossing_a_cell_boundary_is_split_where_it_crosses():
    glyph = _glyph(30, 20, _stroke("M 0 0 L 30 20"))
    (part,) = slice_glyph_parts(glyph, (0, 0, 90, 60), slice_insets=(5, 5, 5, 5), unit_px=1)
    # The diagonal crosses x = 5 and x = 25 (and y = 5 and y = 15): four crossings, five pieces.
    lines = [command for command in part.commands if command.kind == "line"]
    assert len(lines) == 5
    cols, rows = (0, 5, 25, 30), (0, 5, 15, 20)
    dcols, drows = (0, 5, 85, 90), (0, 5, 55, 60)
    for point in _points(part)[1:]:
        # Every vertex is the image of a point on the source diagonal (y = 2x/3).
        sx = next(value for value in [i / 100 for i in range(0, 3001)] if abs(_ref(value, cols, dcols) - point[0]) < 1e-6)
        assert point[1] == pytest.approx(_ref(sx * 2 / 3, rows, drows), abs=1e-6)


def test_a_quadratic_crossing_a_boundary_is_split_and_every_sample_of_the_curve_lies_on_the_warped_pieces():
    glyph = _glyph(30, 20, _stroke("M 0 18 Q 15 -16 30 18"))
    box = (0, 0, 120, 80)
    (part,) = slice_glyph_parts(glyph, box, slice_insets=(5, 5, 5, 5), unit_px=1)
    quadratics = [command for command in part.commands if command.kind == "quadratic"]
    assert len(quadratics) > 1
    cols, rows = (0, 5, 25, 30), (0, 5, 15, 20)
    dcols, drows = (0, 5, 115, 120), (0, 5, 75, 80)
    start = _points(part)[0]
    pieces, current = [], start
    for command in quadratics:
        control, end = command.points
        pieces.append((current, control, end))
        current = end
    flattened = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                  (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])
                 for p0, c, p1 in pieces for t in [i / 400 for i in range(401)]]
    for i in range(0, 201):
        t = i / 200
        sx = 2 * (1 - t) * t * 15 + t * t * 30
        sy = (1 - t) ** 2 * 18 + 2 * (1 - t) * t * -16 + t * t * 18
        expected = (_ref(sx, cols, dcols), _ref(sy, rows, drows))
        assert min(((expected[0] - px) ** 2 + (expected[1] - py) ** 2) ** 0.5 for px, py in flattened) < 0.35


def test_a_hole_stays_a_hole_and_the_frame_stays_ink():
    ring = _glyph(48, 64, _fill("M 4 4 L 44 4 L 44 60 L 4 60 Z M 8 8 L 8 56 L 40 56 L 40 8 Z"))
    (part,) = slice_glyph_parts(ring, (0, 0, 300, 120), slice_insets=(8, 8, 8, 8), unit_px=1)
    outline = [{"kind": c.kind, "points": [list(p) for p in c.points]} for c in part.commands]
    assert not fill_touches(outline, (40, 20, 220, 80))         # the paper in the hole
    assert fill_touches(outline, (5, 40, 2, 10))                 # the left bar of the frame
    assert fill_touches(outline, (100, 5, 20, 2))                # the top bar, stretched


def test_a_box_smaller_than_the_fixed_borders_scales_them_down_together():
    (part,) = slice_glyph_parts(SQUARE, (0, 0, 8, 8), slice_insets=(5, 10, 5, 10), unit_px=1)
    xs = [point[0] for point in _points(part)]
    ys = [point[1] for point in _points(part)]
    assert min(xs) == pytest.approx(0) and max(xs) == pytest.approx(8)
    assert min(ys) == pytest.approx(0) and max(ys) == pytest.approx(8)
    glyph = _glyph(30, 20, _fill("M 10 5 L 20 5 L 20 15 L 10 15 Z"))
    (inner,) = slice_glyph_parts(glyph, (0, 0, 8, 8), slice_insets=(5, 10, 5, 10), unit_px=1)
    # Both 10-unit side borders become 4 px; the middle has no width left, so the inner rectangle is a line at 4.
    assert {round(point[0], 6) for point in _points(inner)} == {4.0}
    tall = _glyph(30, 20, _fill("M 10 5 L 20 5 L 20 15 L 10 15 Z"))
    (inner_y,) = slice_glyph_parts(tall, (0, 0, 8, 8), slice_insets=(5, 10, 5, 10), unit_px=1)
    # Both 5-unit top and bottom borders become 4 px (10 of 8 scaled by 0.8), the middle row has no height left.
    assert {round(point[1], 6) for point in _points(inner_y)} == {4.0}


def test_zero_insets_stretch_the_glyph_over_the_whole_box():
    (part,) = slice_glyph_parts(_glyph(30, 20, _fill("M 15 10 L 30 10 L 30 20 L 15 20 Z")), (0, 0, 90, 80),
                                slice_insets=(0, 0, 0, 0), unit_px=5)
    assert _has(part, (45, 40), (90, 40), (90, 80), (45, 80))


def test_a_strip_is_fixed_to_one_edge_and_stretched_along_the_other_axis():
    edge = _glyph(64, 8, _fill("M 0 2 L 64 2 L 64 6 L 0 6 Z"))
    (part,) = slice_glyph_parts(edge, (10, 100, 256, 120), slice_insets=(8, 0, 0, 0), unit_px=1.5)
    assert _has(part, (10, 103), (266, 103), (266, 109), (10, 109))
    (bottom,) = slice_glyph_parts(edge, (10, 100, 256, 120), slice_insets=(0, 0, 8, 0), unit_px=1.5)
    assert _has(bottom, (10, 211), (266, 211), (266, 217), (10, 217))


def test_stroke_width_scales_with_the_unit_and_is_not_warped_and_the_finish_is_kept():
    glyph = _glyph(30, 20, _stroke("M 0 10 L 30 10", width=2, cap="square", join="bevel"), _fill("M 0 0 L 1 0 L 1 1 Z"))
    stroke, fill = slice_glyph_parts(glyph, (0, 0, 300, 20), slice_insets=(0, 5, 0, 5), unit_px=3)
    assert (stroke.paint_mode, stroke.stroke_width, stroke.line_cap, stroke.line_join) == ("stroke", 6.0, "square", "bevel")
    assert (fill.paint_mode, fill.stroke_width, fill.line_cap, fill.line_join) == ("fill", None, None, None)


def test_the_warp_is_deterministic():
    glyph = _glyph(30, 20, _stroke("M 0 18 Q 15 -16 30 18"), _fill("M 1 1 L 29 1 L 29 19 Z"))
    first = slice_glyph_parts(glyph, (3, 4, 77, 55), slice_insets=(4, 6, 3, 5), unit_px=1.25)
    assert first == slice_glyph_parts(glyph, (3, 4, 77, 55), slice_insets=(4, 6, 3, 5), unit_px=1.25)


def test_a_closed_sub_path_returns_to_its_start():
    (part,) = slice_glyph_parts(SQUARE, (5, 5, 70, 50), slice_insets=(5, 5, 5, 5), unit_px=1)
    points = _points(part)
    assert points[-1] == pytest.approx(points[0])


@pytest.mark.parametrize("kwargs", [
    {"slice_insets": (10, 0, 11, 0), "unit_px": 1},        # top + bottom exceed the viewport height (20)
    {"slice_insets": (0, 16, 0, 15), "unit_px": 1},        # left + right exceed the viewport width (30)
    {"slice_insets": (-1, 0, 0, 0), "unit_px": 1},
    {"slice_insets": (0, 0, 0, 0), "unit_px": 0},
])
def test_an_inconsistent_declaration_is_a_stable_error(kwargs):
    with pytest.raises(ValueError, match="E_LAYOUT_ARTWORK_SLICE_GEOMETRY"):
        slice_glyph_parts(SQUARE, (0, 0, 10, 10), **kwargs)


def test_an_empty_box_and_a_malformed_glyph_are_stable_errors():
    with pytest.raises(ValueError, match="E_LAYOUT_ARTWORK_SLICE_GEOMETRY"):
        slice_glyph_parts(SQUARE, (0, 0, 0, 10), slice_insets=(0, 0, 0, 0), unit_px=1)
    for glyph in ({"viewport": {"inlineSize": 30, "blockSize": 20}, "parts": []},
                  {"viewport": {"inlineSize": 30, "blockSize": 20}, "parts": [{"data": "M 0 0 A 1 1 0 0 0 5 5", "paint": "fill"}]},
                  {"viewport": {"inlineSize": 30, "blockSize": 20}, "parts": [{"data": "L 1 1", "paint": "fill"}]},
                  {"viewport": {"inlineSize": 30, "blockSize": 20}, "parts": [{"data": "M 0 0 L 1 1", "paint": "stroke"}]},
                  {"parts": [_fill("M 0 0 L 1 1")]}):
        with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
            slice_glyph_parts(glyph, (0, 0, 10, 10), slice_insets=(0, 0, 0, 0), unit_px=1)
