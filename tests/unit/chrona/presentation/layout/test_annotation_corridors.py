from __future__ import annotations

from itertools import product
from random import Random

from chrona.presentation.layout.annotation_corridors import (
    StrictCorridorRequest,
    StrictCorridorSearch,
    strict_route_is_valid,
)
from chrona.presentation.layout.annotation_topology import route_strict_bounded
from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleSegment,
    SurfaceObstacle,
    SurfaceObstacleIndex,
    obstacle_envelope,
)
from chrona.presentation.layout.routing import route_quality_metrics


def _index(rectangles: tuple[ObstacleRect, ...]) -> SurfaceObstacleIndex:
    index = SurfaceObstacleIndex()
    for position, rectangle in enumerate(rectangles):
        index.add(SurfaceObstacle(f"rect:{position}", "mark", "plot", rectangle))
    return index


def _axes(request: StrictCorridorRequest) -> tuple[tuple[float, ...], tuple[float, ...]]:
    left, top, right, bottom = request.bounds
    xs, ys = {request.start[0], request.end[0]}, {request.start[1], request.end[1]}
    for item in request.index.all():
        x1, y1, x2, y2 = obstacle_envelope(item.geometry)
        padding = item.clearance + 2.0
        if x2 + padding < left or x1 - padding > right or y2 + padding < top or y1 - padding > bottom:
            continue
        xs.update((x1 - 2.0, x2 + 2.0))
        ys.update((y1 - 2.0, y2 + 2.0))
    return (tuple(sorted(x for x in xs if left <= x <= right)),
            tuple(sorted(y for y in ys if top <= y <= bottom)))


def _compact(points: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float], ...]:
    result: list[tuple[float, float]] = []
    for point in points:
        if result and point == result[-1]:
            continue
        if len(result) >= 2 and (
            result[-2][0] == result[-1][0] == point[0]
            or result[-2][1] == result[-1][1] == point[1]
        ):
            result[-1] = point
        else:
            result.append(point)
    return tuple(result)


def _reference_paths(request: StrictCorridorRequest) -> set[tuple[tuple[float, float], ...]]:
    """Unpruned finite family; used to check that interval compilation loses no fit."""
    xs, ys = _axes(request)
    start, end = request.start, request.end
    paths = set()
    if start[0] == end[0] or start[1] == end[1]:
        paths.add((start, end))
    for swapped in (False, True):
        flip = (lambda point: (point[1], point[0])) if swapped else (lambda point: point)
        s, e = flip(start), flip(end)
        xx, yy = (ys, xs) if swapped else (xs, ys)
        if s[0] != e[0] and s[1] != e[1]:
            paths.add(_compact(tuple(flip(point) for point in (s, (e[0], s[1]), e))))
        for x in xx:
            paths.add(_compact(tuple(flip(point) for point in (s, (x, s[1]), (x, e[1]), e))))
        for y, x in product(yy, xx):
            paths.add(_compact(tuple(flip(point) for point in (s, (s[0], y), (x, y), (x, e[1]), e))))
    return {path for path in paths if len(path) >= 2 and path[0] == start and path[-1] == end
            and all(a != b for a, b in zip(path, path[1:]))}


def _rank(request: StrictCorridorRequest, points: tuple[tuple[float, float], ...]):
    length, _, bends = route_quality_metrics(points)
    return bends, length, *request.tie_break, tuple(value for point in points for value in point)


def test_interval_compiler_preserves_every_exact_clear_family_path_in_small_corpus() -> None:
    rng = Random(1114)
    grid = tuple(range(-4, 5))
    cases = 0
    for _ in range(200):
        start = (rng.choice(grid), rng.choice(grid))
        end = (rng.choice(grid), rng.choice(grid))
        if start == end:
            continue
        rectangles = []
        for _ in range(3):
            left, right = sorted(rng.sample(grid, 2))
            top, bottom = sorted(rng.sample(grid, 2))
            rectangles.append(ObstacleRect(left, top, right, bottom))
        request = StrictCorridorRequest(start, end, _index(tuple(rectangles)), (-6, -6, 6, 6))
        expected = {
            path for path in _reference_paths(request)
            if strict_route_is_valid(path, request, max_bends=6, max_detour_ratio=20)
        }
        search = StrictCorridorSearch((request,))
        actual = set()
        while search.has_candidates:
            _, points = search.pop()
            assert all(a != b for a, b in zip(points, points[1:]))
            if strict_route_is_valid(points, request, max_bends=6, max_detour_ratio=20):
                actual.add(points)
        assert actual == expected
        cases += 1
    assert cases >= 190


def test_epsilon_and_boundary_contacts_preserve_exact_clear_paths() -> None:
    eps = 1e-9
    rectangle = ObstacleRect(0, 0, 1, 1)
    starts_and_ends = (
        ((eps / 2, 0.5), (-2.0, 2.0)),
        ((1.0 - eps / 2, 0.5), (2.0, 2.0)),
        ((eps, -1.0), (1.0 + eps, 2.0)),
        ((-2.0, 0.0), (2.0, 1.0)),
    )
    axes = (-2.0, -1.0, -eps, 0.0, eps / 2, eps, 2 * eps, 1.0 - eps / 2,
            1.0, 1.0 + eps, 2.0)
    for start, end in starts_and_ends:
        request = StrictCorridorRequest(start, end, _index((rectangle,)), (-3, -3, 3, 3))
        expected = {
            path for path in _reference_paths(request)
            if all(point[0] in axes and point[1] in axes for point in path)
            and strict_route_is_valid(path, request, max_bends=6, max_detour_ratio=20)
        }
        search = StrictCorridorSearch((request,))
        actual = set()
        while search.has_candidates:
            _, points = search.pop()
            if all(point[0] in axes and point[1] in axes for point in points):
                if strict_route_is_valid(points, request, max_bends=6, max_detour_ratio=20):
                    actual.add(points)
        assert actual == expected


def test_search_emits_compact_unique_paths_in_global_rank_for_aligned_and_transposed_routes() -> None:
    def request(start, end, tie):
        # Envelope offsets add enough distinct rows and columns for the prefix
        # to include genuine two- and three-bend candidates in either axis.
        blockers = (ObstacleRect(2.25, 2.75, 2.75, 3.25),
                    ObstacleRect(5.25, 4.25, 5.75, 4.75))
        return StrictCorridorRequest(start, end, _index(blockers),
                                     (-3.0, -3.0, 12.0, 12.0), tie_break=(tie,))

    requests = (request((0, 0), (8, 6), 0),
                request((0, 0), (0, 7), 1),
                request((0, 0), (7, 0), 2),
                request((8, 6), (0, 0), 3),
                request((0.125, -0.375), (9.875, 7.625), 4),
                request((-0.000125, 0.000375), (1000000.125, 0.000625), 5))
    search = StrictCorridorSearch(requests)
    observed = []
    while search.has_candidates:
        request_id, points = search.pop()
        assert all(a != b for a, b in zip(points, points[1:]))
        assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(points, points[1:]))
        assert _compact(points) == points
        observed.append((_rank(requests[request_id], points), request_id, points))
    assert len({(request_id, points) for _, request_id, points in observed}) == len(observed)
    assert [rank for rank, _, _ in observed] == sorted(rank for rank, _, _ in observed)
    assert len(observed) > 17
    families = {
        (rank[0], "vertical-first" if len(points) > 1 and points[0][0] == points[1][0]
         else "horizontal-first")
        for rank, _, points in observed
    }
    assert (2, "vertical-first") in families and (2, "horizontal-first") in families
    assert (3, "vertical-first") in families and (3, "horizontal-first") in families
    assert search.generated == len(observed)
    prefix = StrictCorridorSearch(requests)
    limited = []
    for _ in range(min(17, len(observed))):
        request_id, points = prefix.pop()
        limited.append((_rank(requests[request_id], points), request_id, points))
    assert limited == observed[:17]


def test_exact_validator_keeps_nonrectangular_obstacles_and_named_port_exemptions() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("barrier", "dependency-route", "plot",
                              ObstacleSegment((0, 5), (10, 5))))
    index.add(SurfaceObstacle("port:source", "port", "plot", ObstacleRect(1, 4, 2, 6)))
    request = StrictCorridorRequest((0, 5), (10, 5), index, (-2, -2, 12, 12),
                                    port_ids=("port:source",))
    direct = ((0, 5), (10, 5))
    assert not strict_route_is_valid(direct, request, max_bends=4, max_detour_ratio=2)

    only_port = SurfaceObstacleIndex()
    only_port.add(SurfaceObstacle("port:source", "port", "plot", ObstacleRect(1, 4, 2, 6)))
    exempt_request = StrictCorridorRequest((0, 5), (10, 5), only_port, (-2, -2, 12, 12),
                                           port_ids=("port:source",))
    assert strict_route_is_valid(direct, exempt_request, max_bends=4, max_detour_ratio=2)
    assert not strict_route_is_valid(direct,
        StrictCorridorRequest((0, 5), (10, 5), only_port, (-2, -2, 12, 12)),
        max_bends=4, max_detour_ratio=2)


def test_single_pair_budget_reports_exact_drain_vs_truncated_prefix() -> None:
    request = StrictCorridorRequest((0, 0), (7, 5), _index(()), (-2, -2, 10, 10))
    full = StrictCorridorSearch((request,))
    while full.has_candidates:
        full.pop()
    total = full.generated
    assert total > 1

    exact, exact_count, exact_exhausted = route_strict_bounded(
        request.start, request.end, request.index, bounds=request.bounds,
        limit=total, max_bends=0, max_detour_ratio=2)
    short, short_count, short_exhausted = route_strict_bounded(
        request.start, request.end, request.index, bounds=request.bounds,
        limit=total - 1, max_bends=0, max_detour_ratio=2)
    assert exact is None and exact_count == total and not exact_exhausted
    assert short is None and short_count == total - 1 and short_exhausted
