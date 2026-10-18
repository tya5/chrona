"""The orthogonal segment/rectangle shortcut preserves the prior distance oracle."""
from __future__ import annotations

from math import hypot
import random

import pytest

from chrona.presentation.layout.obstacles import (
    BOUNDARY_CONTACT_TOLERANCE,
    ObstacleRect,
    ObstacleSegment,
    _intersects,
)


def _old_segment_length_inside_rect(segment: ObstacleSegment, rect: ObstacleRect) -> float:
    x1, y1 = segment.start
    x2, y2 = segment.end
    low, high = 0.0, 1.0
    for value, delta, start, end in ((x1, x2 - x1, rect.left, rect.right),
                                     (y1, y2 - y1, rect.top, rect.bottom)):
        if delta == 0:
            if not start + BOUNDARY_CONTACT_TOLERANCE < value < end - BOUNDARY_CONTACT_TOLERANCE:
                return 0.0
            continue
        first, second = sorted(((start - value) / delta, (end - value) / delta))
        low, high = max(low, first), min(high, second)
    return max(0.0, high - low) * hypot(x2 - x1, y2 - y1)


def _old_point_segment_distance(point, start, end) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    position = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy)
                            / (dx * dx + dy * dy)))
    return hypot(point[0] - start[0] - position * dx, point[1] - start[1] - position * dy)


def _old_segment_distance(a, b, c, d) -> float:
    def cross(first, second, third):
        return ((second[0] - first[0]) * (third[1] - first[1])
                - (second[1] - first[1]) * (third[0] - first[0]))

    cross1, cross2 = cross(a, b, c), cross(a, b, d)
    cross3, cross4 = cross(c, d, a), cross(c, d, b)
    if cross1 * cross2 <= 0 and cross3 * cross4 <= 0:
        if (max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
                and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1]))):
            return 0.0
    return min(_old_point_segment_distance(a, c, d), _old_point_segment_distance(b, c, d),
               _old_point_segment_distance(c, a, b), _old_point_segment_distance(d, a, b))


def _old_segment_rect_intersects(segment: ObstacleSegment, rect: ObstacleRect, clearance: float) -> bool:
    radius = segment.stroke_width / 2 + clearance
    if _old_segment_length_inside_rect(segment, rect) > BOUNDARY_CONTACT_TOLERANCE:
        return True
    if radius == 0:
        return False
    corners = ((rect.left, rect.top), (rect.right, rect.top),
               (rect.right, rect.bottom), (rect.left, rect.bottom))
    return any(_old_segment_distance(segment.start, segment.end, corners[index], corners[(index + 1) % 4])
               < radius for index in range(4))


@pytest.mark.parametrize("segment,clearance", (
    (ObstacleSegment((-5, -2), (15, -2)), 2.0),  # exact radius contact is open
    (ObstacleSegment((15, -2), (-5, -2), stroke_width=1.0), 1.5),  # reversed axis, same strict contact
    (ObstacleSegment((5, 5), (5 + BOUNDARY_CONTACT_TOLERANCE / 2, 5)), 0.0),
    (ObstacleSegment((5, 5), (5 + BOUNDARY_CONTACT_TOLERANCE * 2, 5)), 0.0),
    (ObstacleSegment((5, 0), (8, 0)), 0.0),  # open boundary touch
    (ObstacleSegment((8, 0), (5, 0), stroke_width=0.2), 0.0),
    (ObstacleSegment((-1, -1), (0, 0)), 0.0),  # corner contact
    (ObstacleSegment((-1, -1), (0, 0), stroke_width=0.2), 0.0),
    (ObstacleSegment((-2, 5), (-1, 5), stroke_width=0.5), 1.6),
    (ObstacleSegment((5, -2), (5, -1), stroke_width=0.5), 1.6),  # vertical/reversed geometry
    (ObstacleSegment((5, -1), (5, -2), stroke_width=0.5), 1.6),
    (ObstacleSegment((-2, 12), (-1, 11)), 2.0),  # diagonal remains on the old path
))
def test_fastpath_matches_prior_segment_rect_rule(segment, clearance):
    rect = ObstacleRect(0, 0, 10, 10)
    expected = _old_segment_rect_intersects(segment, rect, clearance)

    assert _intersects(segment, rect, clearance) is expected
    assert _intersects(rect, segment, clearance) is expected


def test_fastpath_matches_prior_rule_for_bounded_seeded_geometry_sample():
    rng = random.Random(1723)
    for _ in range(12_000):
        left, top = rng.uniform(-100, 100), rng.uniform(-100, 100)
        rect = ObstacleRect(left, top, left + rng.uniform(1e-8, 80), top + rng.uniform(1e-8, 80))
        if rng.randrange(3) == 0:
            segment = ObstacleSegment((rng.uniform(-120, 120), rng.uniform(-120, 120)),
                                      (rng.uniform(-120, 120), rng.uniform(-120, 120)),
                                      rng.choice((0.0, 1e-9, 0.1, 3.0)))
        elif rng.randrange(2):
            y = rng.uniform(top - 2, rect.bottom + 2)
            segment = ObstacleSegment((rng.uniform(-120, 120), y),
                                      (rng.uniform(-120, 120), y), rng.choice((0.0, 0.1, 3.0)))
        else:
            x = rng.uniform(left - 2, rect.right + 2)
            segment = ObstacleSegment((x, rng.uniform(-120, 120)),
                                      (x, rng.uniform(-120, 120)), rng.choice((0.0, 0.1, 3.0)))
        clearance = rng.choice((0.0, 1e-9, 0.01, 2.0))
        expected = _old_segment_rect_intersects(segment, rect, clearance)
        assert _intersects(segment, rect, clearance) is expected
        assert _intersects(rect, segment, clearance) is expected
