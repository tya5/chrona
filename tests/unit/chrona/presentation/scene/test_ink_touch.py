"""#848: does the painted area of a completed Symbol outline meet a rectangle? Pure geometry, no Scene."""
from __future__ import annotations

import pytest

from chrona.presentation.scene.ink_touch import (
    InkTouchError, QUADRATIC_CHORDS, fill_touches, stroke_touches, subpaths)


def _outline(*commands):
    return [{"kind": kind, "points": [list(point) for point in points]} for kind, *points in commands]


def _closed(points):
    first, *rest = points
    return [("move", first), *(("line", point) for point in rest), ("line", first)]


def _ring(outer=(0, 0, 100, 60), hole=(10, 10, 90, 50), *, hole_winding="opposite"):
    """A frame ring: the outer rectangle clockwise and the hole wound the other way (so it is empty)."""
    x0, y0, x1, y1 = outer
    hx0, hy0, hx1, hy1 = hole
    outer_points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    hole_points = ([(hx0, hy0), (hx0, hy1), (hx1, hy1), (hx1, hy0)] if hole_winding == "opposite"
                   else [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)])
    return _outline(*_closed(outer_points), *_closed(hole_points))


def test_a_rectangle_in_the_hole_of_a_ring_does_not_touch_its_ink():
    assert not fill_touches(_ring(), (20, 20, 60, 20))


def test_a_rectangle_crossing_the_inner_edge_touches_the_ring():
    assert fill_touches(_ring(), (5, 20, 30, 10))


def test_a_rectangle_wholly_inside_the_solid_frame_touches_it_without_crossing_any_edge():
    assert fill_touches(_ring(), (2, 20, 4, 10))


def test_a_rectangle_wholly_outside_the_ring_does_not_touch_it():
    assert not fill_touches(_ring(), (120, 20, 10, 10))


def test_a_hole_wound_the_same_way_is_filled_so_the_rectangle_in_it_touches():
    assert fill_touches(_ring(hole_winding="same"), (20, 20, 60, 20))


def test_a_rectangle_containing_the_whole_ring_touches_it_through_its_edges():
    assert fill_touches(_ring(), (-50, -50, 300, 300))


def test_a_rectangle_that_only_shares_an_edge_point_touches():
    assert fill_touches(_ring(), (90, 20, 5, 10))   # x from 90 (the hole's right edge) into the frame


def test_a_curve_is_flattened_and_a_rectangle_in_its_bulge_touches_while_one_beyond_it_does_not():
    # A closed half-disc-like shape: base on y=40, a quadratic bulging up to y=10 at the middle.
    outline = _outline(("move", (0, 40)), ("quadratic", (50, -20), (100, 40)), ("line", (0, 40)))
    assert fill_touches(outline, (45, 20, 10, 5))           # under the curve's apex (y = 10)
    assert not fill_touches(outline, (45, 0, 10, 5))        # above the apex
    assert QUADRATIC_CHORDS >= 8


def test_a_degenerate_rectangle_is_a_point_test():
    assert fill_touches(_ring(), (3, 3, 0, 0))
    assert not fill_touches(_ring(), (50, 30, 0, 0))


def test_a_stroke_touches_within_half_its_width_and_not_beyond():
    line = _outline(("move", (5, 0)), ("line", (5, 60)))
    assert stroke_touches(line, (6.5, 20, 30, 10), 4)       # 1.5 from the line, half width 2
    assert stroke_touches(line, (7, 20, 30, 10), 4)         # exactly half a width away
    assert not stroke_touches(line, (7.5, 20, 30, 10), 4)
    assert stroke_touches(line, (0, 20, 5, 10), 0.0)        # a rectangle that reaches the centre line


def test_a_stroke_measures_to_the_end_of_a_segment_and_not_along_its_extension():
    line = _outline(("move", (0, 0)), ("line", (10, 0)))
    assert not stroke_touches(line, (14, -1, 5, 2), 4)      # 4 past the end, reach 2
    assert stroke_touches(line, (11.5, -1, 5, 2), 4)


def test_a_stroked_curve_is_flattened_too():
    curve = _outline(("move", (0, 40)), ("quadratic", (50, -20), (100, 40)))
    assert stroke_touches(curve, (45, 8, 10, 4), 2)         # the apex is at y = 10
    assert not stroke_touches(curve, (45, 30, 10, 4), 2)


def test_every_subpath_is_kept_and_a_lone_move_is_dropped():
    outline = _outline(("move", (0, 0)), ("line", (1, 0)), ("move", (5, 5)), ("move", (9, 9)), ("line", (9, 10)))
    assert subpaths(outline) == (((0.0, 0.0), (1.0, 0.0)), ((9.0, 9.0), (9.0, 10.0)))


@pytest.mark.parametrize("bad", [
    [{"kind": "line", "points": [[1, 1]]}],                                     # no move first
    [{"kind": "move", "points": [[0, 0], [1, 1]]}],                             # wrong arity
    [{"kind": "move", "points": [[0, 0]]}, {"kind": "arc", "points": [[1, 1]]}],
    [{"kind": "move", "points": [[0, float("nan")]]}],
    [{"kind": "move", "points": [["a", 0]]}],
    [{"kind": "move"}],
])
def test_a_malformed_outline_is_an_error_not_a_guess(bad):
    with pytest.raises(InkTouchError):
        fill_touches(bad, (0, 0, 1, 1))
