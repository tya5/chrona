"""The indexed `SurfaceObstacleIndex.collisions` equals the naive full scan (#721 item 2).

The reference below is the pre-index implementation: select by class and region, drop
exemptions, test envelopes, then the exact predicate, in sorted `placement_id` order.
Generated cases deliberately sit on boundaries: touching and overlapping boxes, zero-extent
envelopes (axis-aligned segments), boundary-exact and one-ulp-off edges, negative and large
coordinates, and per-item and per-query clearance.
"""
from __future__ import annotations

from math import nextafter
from random import Random

import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
    _GRID_AFTER_QUERIES, _GRID_MIN_ITEMS, _envelopes_overlap, _intersects, obstacle_envelope,
)
from chrona.presentation.layout.routing import RouteSearchFailure, route_orthogonal

CLASSES = ("mark", "text", "rule", "dependency-route", "port")
REGIONS = ("timeline", "group-header", "table")


def naive_collisions(index, geometry, *, classes=None, regions=None, exempt=frozenset(), clearance=0.0):
    selected_classes = None if classes is None else frozenset(classes)
    selected_regions = None if regions is None else frozenset(regions)
    candidate_box = obstacle_envelope(geometry)
    return tuple(
        item for item in index.all()
        if (selected_classes is None or item.obstacle_class in selected_classes)
        and (selected_regions is None or item.region_id in selected_regions)
        and item.placement_id not in exempt
        and _envelopes_overlap(candidate_box, obstacle_envelope(item.geometry), clearance + item.clearance)
        and _intersects(geometry, item.geometry, clearance + item.clearance))


class NaiveIndex(SurfaceObstacleIndex):
    """Same inventory, collisions answered by the reference scan (no cache, no grid)."""

    def collisions(self, geometry, *, classes=None, regions=None, host_id=None, rule_host_id=None,
                   port_ids=(), clearance=0.0):
        return naive_collisions(self, geometry, classes=classes, regions=regions,
                                exempt=frozenset(port_ids), clearance=clearance)


def coordinate(rng: Random, scale: float) -> float:
    """Lattice values (touching and shared edges), rounding-offset values, negatives."""
    base = rng.randint(-8, 24) * scale
    kind = rng.randrange(6)
    if base == 0 and kind < 2:
        return base  # a denormal offset from zero is a degenerate segment the predicate never sees
    if kind == 0:
        return nextafter(base, float("inf"))
    if kind == 1:
        return nextafter(base, float("-inf"))
    if kind == 2:
        return base + 0.1 + 0.2 - 0.3
    return base


def random_geometry(rng: Random, scale: float):
    x, y = coordinate(rng, scale), coordinate(rng, scale)
    if rng.random() < 0.5:
        width, height = rng.randint(1, 6) * scale, rng.randint(1, 6) * scale
        return ObstacleRect(x, y, x + width, y + height)
    kind = rng.randrange(3)
    length = rng.randint(1, 9) * scale
    if kind == 0:
        end = (x + length, y)
    elif kind == 1:
        end = (x, y + length)
    else:
        end = (x + length, y + rng.choice((-1, 1)) * length / 2)
    return ObstacleSegment((x, y), end, stroke_width=rng.choice((0.0, 0.0, 2.0)))


def random_index(rng: Random, count: int, scale: float, cls=SurfaceObstacleIndex,
                 offset: float = 0.0) -> SurfaceObstacleIndex:
    index = cls()
    for number in range(count):
        index.add(SurfaceObstacle(
            f"o{rng.randrange(10**6):06d}:{number}", rng.choice(CLASSES), rng.choice(REGIONS),
            shifted(random_geometry(rng, scale), offset), clearance=rng.choice((0.0, 0.0, 0.0, 0.1, 0.25, 0.3, 3.0)) * scale))
    return index


@pytest.mark.parametrize("scale,offset", [(1.0, 0.0), (2.5, -40.0), (1.0, 1e6), (0.01, 0.0), (0.1, 0.0), (0.1, -0.7)])
@pytest.mark.parametrize("count", [0, 1, 5, _GRID_MIN_ITEMS, 40, 150])
def test_indexed_collisions_equal_the_naive_scan(count: int, scale: float, offset: float) -> None:
    rng = Random(f"{count}:{scale}:{offset}")
    index = random_index(rng, count, scale, offset=offset)
    queries = hits = 0
    for _ in range(300):
        geometry = random_geometry(rng, scale)
        if offset:
            geometry = shifted(geometry, offset)
        classes = rng.choice((None, None, ("mark",), ("text", "rule"), ("port", "dependency-route", "mark")))
        regions = rng.choice((None, None, ("timeline",), ("timeline", "group-header")))
        clearance = rng.choice((0.0, 0.0, 0.1, 0.2, 0.3, 0.5, 2.0)) * scale
        expected = naive_collisions(index, geometry, classes=classes, regions=regions, clearance=clearance)
        assert index.collisions(geometry, classes=classes, regions=regions, clearance=clearance) == expected
        queries += 1
        hits += bool(expected)
    assert queries > _GRID_AFTER_QUERIES
    if count >= _GRID_MIN_ITEMS:
        assert hits > 10  # the comparison is not vacuously all-empty
    if _GRID_MIN_ITEMS <= count <= 40 and scale >= 1.0:
        assert hits < queries  # nor vacuously all-colliding


def shifted(geometry, offset):
    if isinstance(geometry, ObstacleRect):
        return ObstacleRect(geometry.left + offset, geometry.top + offset,
                            geometry.right + offset, geometry.bottom + offset)
    return ObstacleSegment((geometry.start[0] + offset, geometry.start[1] + offset),
                           (geometry.end[0] + offset, geometry.end[1] + offset), geometry.stroke_width)


def test_the_grid_path_is_actually_exercised() -> None:
    index = random_index(Random("grid"), 80, 1.0)
    box = ObstacleRect(0, 0, 5, 5)
    for _ in range(_GRID_AFTER_QUERIES + 2):
        index.collisions(box)
    prepared = index._selection(None, None)
    assert prepared._grid is not None and prepared.queries > _GRID_AFTER_QUERIES


def test_boundary_exact_and_one_ulp_edges_match_the_scan() -> None:
    index = SurfaceObstacleIndex()
    for number in range(_GRID_MIN_ITEMS + 4):
        left = float(number * 10)
        index.add(SurfaceObstacle(f"mark:{number:03d}", "mark", "timeline",
                                  ObstacleRect(left, 0.0, left + 10.0, 10.0), clearance=1.0))
    edge = 10.0
    probes = []
    for x in (edge, nextafter(edge, 0.0), nextafter(edge, 99.0), edge - 1.0, nextafter(edge - 1.0, 0.0), edge + 1.0,
              nextafter(edge + 1.0, 99.0), -1.0, nextafter(-1.0, -2.0), 0.0):
        probes.append(ObstacleSegment((x, 5.0), (x + 4.0, 5.0)))      # horizontal, zero-height envelope
        probes.append(ObstacleSegment((x, -3.0), (x, 14.0)))          # vertical, zero-width envelope
        probes.append(ObstacleRect(x, 2.0, x + 1.0, 3.0))
    for clearance in (0.0, 1.0, nextafter(1.0, 2.0)):
        for _ in range(_GRID_AFTER_QUERIES + 1):                      # past the point where the grid is built
            for probe in probes:
                assert (index.collisions(probe, clearance=clearance)
                        == naive_collisions(index, probe, clearance=clearance))


def test_add_between_queries_invalidates_the_prepared_selection() -> None:
    rng = Random("add")
    index = random_index(rng, 60, 1.0)
    box = ObstacleRect(2, 2, 9, 9)
    for _ in range(_GRID_AFTER_QUERIES + 2):
        index.collisions(box)
    index.add(SurfaceObstacle("zz:new", "mark", "timeline", ObstacleRect(3, 3, 4, 4)))
    assert index.collisions(box) == naive_collisions(index, box)
    assert index.collisions(box)[-1].placement_id == "zz:new"
    assert index.select() == index.all()


def test_exemptions_and_generator_filters_match() -> None:
    rng = Random("exempt")
    index = random_index(rng, 50, 1.0)
    index.add(SurfaceObstacle("port:a", "port", "timeline", ObstacleRect(0, 0, 3, 3)))
    for _ in range(40):
        geometry = random_geometry(rng, 1.0)
        got = index.collisions(geometry, classes=(name for name in ("port", "mark")),
                               regions=(name for name in ("timeline", "table")), port_ids=("port:a",))
        assert got == naive_collisions(index, geometry, classes=("port", "mark"), regions=("timeline", "table"),
                                       exempt=frozenset({"port:a"}))


def test_routes_through_the_index_equal_routes_through_the_naive_scan() -> None:
    """Same boolean for every candidate segment means the same A* expansion and the same route."""
    rng = Random("routes")
    compared = 0
    for case in range(40):
        count = rng.choice((4, 12, 30))
        seed = rng.randrange(10**9)
        fast = random_index(Random(seed), count, 1.0)
        slow = random_index(Random(seed), count, 1.0, cls=NaiveIndex)
        start = (coordinate(rng, 1.0), coordinate(rng, 1.0))
        end = (coordinate(rng, 1.0), coordinate(rng, 1.0))
        if start == end:
            continue
        bounds = (-12.0, -12.0, 40.0, 40.0)
        outcomes = []
        for index in (fast, slow):
            try:
                outcomes.append(route_orthogonal(start, end, index, bounds=bounds, limit=600))
            except RouteSearchFailure as error:
                outcomes.append(str(error))
        assert outcomes[0] == outcomes[1], case
        compared += 1
    assert compared >= 30
