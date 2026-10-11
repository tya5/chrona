"""Ordinary graph exhaustion is not protected-route impossibility (#1300).

The narrow dogleg has a safe stroked witness, but the current ordinary graph
offers only unsafe boundary routes. This characterizes the ordinary algorithm;
it is not a completeness claim for the pending protected feasibility pass.
"""
from math import hypot

import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.route_search import orthogonal_route_candidates
from chrona.presentation.layout.routing import route_self_overlaps


@pytest.mark.parametrize("shift", (0.0, -100.0, 1000.0))
def test_exhausted_ordinary_graph_can_miss_a_safe_stroked_dogleg(shift):
    rectangles = ((0.0, 0.0, 30.0, 4.0), (0.0, 6.0, 14.0, 30.0),
                  (16.0, 0.0, 30.0, 24.0), (0.0, 26.0, 30.0, 30.0))
    obstacles = SurfaceObstacleIndex()
    for number, rectangle in enumerate(rectangles):
        obstacles.add(SurfaceObstacle(str(number), "mark", "timeline",
                                      ObstacleRect(*(value + shift for value in rectangle))))
    witness = tuple((x + shift, y + shift)
                    for x, y in ((2.0, 5.0), (15.0, 5.0), (15.0, 25.0), (28.0, 25.0)))

    def safe(path):
        return (not route_self_overlaps(path)
                and all(hypot(b[0] - a[0], b[1] - a[1]) >= 1.0
                        and not obstacles.collisions(ObstacleSegment(a, b, 1.0))
                        for a, b in zip(path, path[1:])))

    assert safe(witness)
    # Natural exhaustion, not an expansion-limit exception; quality limits
    # are absent here, so relaxing maxBends/maxDetourRatio cannot repair this.
    candidates = tuple(orthogonal_route_candidates(
        witness[0], witness[-1], obstacles,
        bounds=tuple(value + shift for value in (0.0, 0.0, 30.0, 30.0))))
    assert candidates
    assert not any(safe(path) for path in candidates)


@pytest.mark.parametrize("shift", (0.0, -100.0, 1000.0))
def test_minimum_leg_walk_is_not_a_safe_simple_route(shift):
    """A walk can satisfy minimum legs by revisiting the source/target.

    On the six-vertex perimeter cycle s-t-r-ur-ul-l-s, the only simple
    s-t paths are the direct edge and the long way around. Both have a
    final maximal straight run of length one. The walk around the other
    way revisits s and t and has every maximal run at least two, but is
    forbidden by Chrona's self-overlap rule. This is a finite-graph
    characterization, not a geometric completeness claim.

    Ahrens, Efficient Algorithms for Routing a Net Subject to VLSI Design
    Rules (2020), section4.2 and corollary4.2 distinguish these problems:
    https://d-nb.info/1224966090/34
    """
    def translated(points):
        return tuple((x + shift, y + shift) for x, y in points)

    simple_paths = (
        translated(((0, 0), (1, 0))),
        translated(((0, 0), (-2, 0), (-2, 2), (2, 2), (2, 0), (1, 0))),
    )
    walk = translated(((0, 0), (2, 0), (2, 2), (-2, 2), (-2, 0), (1, 0)))

    def minimum_leg(path):
        return min(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))

    assert all(not route_self_overlaps(path) and minimum_leg(path) < 2 for path in simple_paths)
    assert minimum_leg(walk) >= 2
    assert route_self_overlaps(walk)
