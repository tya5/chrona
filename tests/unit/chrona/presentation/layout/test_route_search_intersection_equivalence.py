"""Fast path-history checks remain equivalent to Layout obstacle collisions."""

from random import Random

import pytest

from chrona.presentation.layout.obstacles import ObstacleSegment, obstacles_intersect
from chrona.presentation.layout.route_search import _history_segments_intersect


def _segment(start, end):
    return ObstacleSegment(start, end)


@pytest.mark.parametrize(("first", "second"), [
    (((-4.0, -2.0), (3.0, -2.0)), ((0.0, -2.0), (5.0, -2.0))),  # collinear overlap
    (((-4.0, -2.0), (0.0, -2.0)), ((0.0, -2.0), (5.0, -2.0))),  # opposite-direction touch
    (((-4.0, -2.0), (0.0, -2.0)), ((-4.0, -2.0), (5.0, -2.0))),  # same-side touch/overlap
    (((0.0, 0.0), (4.0, 0.0)), ((2.0, -2.0), (2.0, 3.0))),  # transverse interior crossing
    (((0.0, 0.0), (4.0, 0.0)), ((4.0, 0.0), (4.0, 3.0))),  # perpendicular shared endpoint
    (((-1.0e12, -1.0e12), (1.0e12, -1.0e12)), ((0.0, -1.0e12), (0.0, 1.0e12))),
    (((-1.0e12, -1.0e12), (-1.0e12, 0.0)), ((-1.0e12, 0.0), (-1.0e12, 1.0e12))),
    (((-4.0, 0.0), (0.0, 0.0)), ((5.0e-10, 0.0), (4.0, 0.0))),  # sub-epsilon gap
    (((-4.0, 0.0), (0.0, 0.0)), ((1.1e-9, 0.0), (4.0, 0.0))),  # over-epsilon gap
    (((0.0, 0.0), (4.0, 0.0)), ((0.0, 5.0e-10), (4.0, 5.0e-10))),
    (((0.0, 0.0), (4.0, 0.0)), ((0.0, 1.1e-9), (4.0, 1.1e-9))),
])
def test_axis_aligned_fast_check_matches_obstacle_predicate(first, second):
    assert _history_segments_intersect(first, second) == obstacles_intersect(
        _segment(*first), _segment(*second))


def test_zero_length_segment_validation_matches_obstacle_geometry():
    zero = ((-3.0, 7.0), (-3.0, 7.0))
    valid = ((-3.0, 7.0), (2.0, 7.0))
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_GEOMETRY"):
        _history_segments_intersect(zero, valid)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_GEOMETRY"):
        obstacles_intersect(_segment(*zero), _segment(*valid))


def test_deterministic_random_axis_segments_match_reference_predicate():
    random = Random(1109)
    for _ in range(2000):
        segments = []
        for _ in range(2):
            start = (random.uniform(-1e6, 1e6), random.uniform(-1e6, 1e6))
            if random.randrange(2):
                end = (random.uniform(-1e6, 1e6), start[1])
            else:
                end = (start[0], random.uniform(-1e6, 1e6))
            if end == start:
                end = (end[0] + 1.0, end[1])
            segments.append((start, end))
        first, second = segments
        assert _history_segments_intersect(first, second) == obstacles_intersect(
            _segment(*first), _segment(*second))
