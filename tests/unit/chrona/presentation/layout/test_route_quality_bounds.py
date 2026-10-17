from pytest import approx

from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.route_quality_bounds import rectangular_detour_lower_bound


def _length(points):
    return sum(abs(right[0] - left[0]) + abs(right[1] - left[1])
               for left, right in zip(points, points[1:]))


def test_vertical_barrier_bound_is_side_excursion_plus_endpoint_distance():
    rect = ObstacleRect(4.0, 2.0, 6.0, 8.0)

    assert rectangular_detour_lower_bound((5.0, 0.0), (5.0, 10.0), (rect,)) == approx(12.0)
    assert rectangular_detour_lower_bound((5.0, 10.0), (5.0, 0.0), (rect,)) == approx(12.0)


def test_horizontal_barrier_bound_is_symmetric():
    rect = ObstacleRect(2.0, 4.0, 8.0, 6.0)

    assert rectangular_detour_lower_bound((0.0, 5.0), (10.0, 5.0), (rect,)) == approx(12.0)
    assert rectangular_detour_lower_bound((10.0, 5.0), (0.0, 5.0), (rect,)) == approx(12.0)


def test_nonseparating_rectangles_do_not_raise_manhattan_lower_bound():
    rect = ObstacleRect(4.0, 2.0, 6.0, 8.0)

    # Endpoints do not straddle the rect's vertical extent.
    assert rectangular_detour_lower_bound((5.0, 0.0), (5.0, 1.0), (rect,)) == approx(1.0)
    # They straddle, but are outside the rectangle's other-axis interval.
    assert rectangular_detour_lower_bound((3.0, 0.0), (3.0, 10.0), (rect,)) == approx(10.0)
    assert rectangular_detour_lower_bound((0.0, 0.0), (10.0, 0.0), ()) == approx(10.0)


def test_multiple_rectangles_take_maximum_not_sum():
    first = ObstacleRect(4.0, 2.0, 6.0, 8.0)   # bound 12
    second = ObstacleRect(3.0, 3.0, 7.0, 7.0)  # bound 14

    assert rectangular_detour_lower_bound((5.0, 0.0), (5.0, 10.0), (first, second)) == approx(14.0)


def test_near_touching_or_degenerate_rectangles_are_conservative():
    # A bound is omitted when strict separation is within the helper's 1e-6 margin.
    near_edge = ObstacleRect(4.0, 2.0, 6.0, 8.0)
    assert rectangular_detour_lower_bound((5.0, 0.0), (5.0, 2.0 + 5e-7), (near_edge,)) == approx(2.0 + 5e-7)
    assert rectangular_detour_lower_bound((4.0 + 5e-7, 0.0), (4.0 + 5e-7, 10.0), (near_edge,)) == approx(10.0)
    narrower_than_margin = ObstacleRect(5.0, 2.0, 5.0 + 5e-7, 8.0)
    assert rectangular_detour_lower_bound((5.0, 0.0), (5.0, 10.0),
        (narrower_than_margin,)) == approx(10.0)


def test_bound_never_exceeds_explicit_safe_orthogonal_detours():
    cases = (
        (ObstacleRect(4.0, 2.0, 6.0, 8.0), (5.0, 0.0), (5.0, 10.0),
         ((5.0, 0.0), (4.0, 0.0), (4.0, 10.0), (5.0, 10.0))),
        (ObstacleRect(2.0, 4.0, 8.0, 6.0), (0.0, 5.0), (10.0, 5.0),
         ((0.0, 5.0), (0.0, 4.0), (10.0, 4.0), (10.0, 5.0))),
        (ObstacleRect(3.0, 2.0, 7.0, 8.0), (4.0, 0.0), (6.0, 10.0),
         ((4.0, 0.0), (3.0, 0.0), (3.0, 10.0), (6.0, 10.0))),
    )
    for rect, start, end, path in cases:
        bound = rectangular_detour_lower_bound(start, end, (rect,))
        assert bound <= _length(path) + 1e-6
