"""Bounded sparse candidate search for orthogonal Layout routes."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from heapq import heappop, heappush
from itertools import count
from math import isfinite

from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleSegment,
    SurfaceObstacleIndex,
    obstacle_envelope,
    obstacles_intersect,
)


class RouteSearchFailure(ValueError):
    """A bounded orthogonal search found no route; unrelated ValueErrors propagate."""


Point = tuple[float, float]
Path = tuple[Point, ...]
Edge = tuple[int, int, float]
SparseGraph = tuple[
    tuple[Point, ...],
    tuple[tuple[Edge, ...], ...],
    tuple[tuple[tuple[int, int], tuple[int, float]], ...],
]


def _build_sparse_graph(
    start: Point,
    end: Point,
    rects: tuple[tuple[float, float, float, float], ...],
    *,
    grid_offset: float,
    bounds: tuple[float, float, float, float] | None,
    clear,
) -> SparseGraph:
    """Build an immutable finite visibility graph and its reverse heuristic."""
    boxes = rects
    x_events: set[float] = {start[0], end[0]}
    y_events: set[float] = {start[1], end[1]}
    for left, top, right, bottom in boxes:
        x_events.update((left - grid_offset, right + grid_offset))
        y_events.update((top - grid_offset, bottom + grid_offset))
    if bounds is not None:
        left, top, right, bottom = bounds
        x_events.update((left, right))
        y_events.update((top, bottom))
        x_events = {x for x in x_events if left <= x <= right} | {start[0], end[0]}
        y_events = {y for y in y_events if top <= y <= bottom} | {start[1], end[1]}

    nodes: set[Point] = {start, end}
    for left, top, right, bottom in boxes:
        for x in (left - grid_offset, right + grid_offset):
            for y in (top - grid_offset, bottom + grid_offset):
                if bounds is None or (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
                    nodes.add((x, y))
    for x in x_events:
        for y in (start[1], end[1]):
            if bounds is None or bounds[1] <= y <= bounds[3]:
                nodes.add((x, y))
    for y in y_events:
        for x in (start[0], end[0]):
            if bounds is None or bounds[0] <= x <= bounds[2]:
                nodes.add((x, y))
    if bounds is not None:
        left, top, right, bottom = bounds
        for x in x_events:
            nodes.update(((x, top), (x, bottom)))
        for y in y_events:
            nodes.update(((left, y), (right, y)))

    ordered = tuple(sorted(nodes))
    node_id = {point: number for number, point in enumerate(ordered)}
    target = node_id[end]
    adjacency_lists: list[list[Edge]] = [[] for _ in ordered]
    by_x: dict[float, list[tuple[float, int]]] = {}
    by_y: dict[float, list[tuple[float, int]]] = {}
    for number, (x, y) in enumerate(ordered):
        by_x.setdefault(x, []).append((y, number))
        by_y.setdefault(y, []).append((x, number))
    for groups, axis in ((by_x.values(), 1), (by_y.values(), 0)):
        for group in groups:
            group.sort()
            for (_, first), (_, second) in zip(group, group[1:]):
                a, b = ordered[first], ordered[second]
                if clear(a, b):
                    direction = 0 if axis == 0 else 1
                    distance = abs(a[axis] - b[axis])
                    adjacency_lists[first].append((second, direction, distance))
                    adjacency_lists[second].append((first, direction, distance))
    for neighbors in adjacency_lists:
        neighbors.sort(key=lambda entry: (ordered[entry[0]], entry[1], entry[2]))
    adjacency = tuple(tuple(neighbors) for neighbors in adjacency_lists)

    # Reverse Dijkstra over directed-node states supplies an admissible
    # lexicographic lower bound without discarding path-dependent histories.
    reverse: dict[tuple[int, int], list[tuple[tuple[int, int], int, float]]] = {}
    for origin, neighbors in enumerate(adjacency):
        for destination, direction, distance in neighbors:
            state = (destination, direction)
            for previous_direction in (0, 1):
                predecessor = (origin, previous_direction)
                reverse.setdefault(state, []).append(
                    (predecessor, int(previous_direction != direction), distance))
    remaining: dict[tuple[int, int], tuple[int, float]] = {
        (target, 0): (0, 0.0), (target, 1): (0, 0.0)
    }
    reverse_queue: list[tuple[int, float, tuple[int, int]]] = [
        (0, 0.0, (target, 0)), (0, 0.0, (target, 1))
    ]
    while reverse_queue:
        bends, length, state = heappop(reverse_queue)
        if remaining.get(state) != (bends, length):
            continue
        for predecessor, added_bends, distance in reverse.get(state, ()):
            candidate = (bends + added_bends, length + distance)
            if candidate < remaining.get(predecessor, (float("inf"), float("inf"))):
                remaining[predecessor] = candidate
                heappush(reverse_queue, (candidate[0], candidate[1], predecessor))
    return ordered, adjacency, tuple(sorted(remaining.items()))


def orthogonal_route_candidates(
    start: Point,
    end: Point,
    obstacles: Iterable[tuple[float, float, float, float]] | SurfaceObstacleIndex,
    *,
    grid_offset: float = 2.0,
    bend_penalty: float | None = None,
    limit: int = 4096,
    bounds: tuple[float, float, float, float] | None = None,
    port_ids: tuple[str, ...] = (),
    classes: tuple[str, ...] | None = None,
    regions: tuple[str, ...] | None = None,
    initial_direction: int = -1,
) -> Iterator[Path]:
    """Yield deterministic orthogonal paths from a finite sparse event graph.

    ``bend_penalty=None`` orders candidates by bends then length. A numeric
    penalty orders them by ``length + penalty * bends``. Expansion accounting
    is shared by the whole iterator; if a consumer asks for another candidate
    after the limit is reached, ``RouteSearchFailure`` reports that the bounded
    frontier was not exhausted.
    """
    if (len(start) != 2 or len(end) != 2
            or not all(isfinite(value) for value in (*start, *end))
            or not isfinite(grid_offset) or grid_offset < 0
            or (bend_penalty is not None and (not isfinite(bend_penalty) or bend_penalty < 0))
            or isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
            or initial_direction not in {-1, 0, 1}):
        raise ValueError("E_LAYOUT_ROUTE_SEARCH_INPUT")
    if bounds is not None:
        if (len(bounds) != 4 or not all(isfinite(value) for value in bounds)
                or bounds[0] > bounds[2] or bounds[1] > bounds[3]):
            raise ValueError("E_LAYOUT_ROUTE_SEARCH_INPUT")
        if not (bounds[0] <= start[0] <= bounds[2]
                and bounds[1] <= start[1] <= bounds[3]
                and bounds[0] <= end[0] <= bounds[2]
                and bounds[1] <= end[1] <= bounds[3]):
            raise RouteSearchFailure("E_CONNECTOR_UNROUTABLE")

    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    rects: tuple[tuple[float, float, float, float], ...]
    if index is None:
        rects = tuple(tuple(box) for box in obstacles)
        if any(len(box) != 4 or not all(isfinite(value) for value in box)
               or box[0] > box[2] or box[1] > box[3] for box in rects):
            raise ValueError("E_LAYOUT_ROUTE_SEARCH_INPUT")
        items = ()
    else:
        items = index.select(classes=classes, regions=regions)
        rects = tuple(obstacle_envelope(item.geometry) for item in items)
        all_by_id = {item.placement_id: item for item in index.all()}
        if any(not isinstance(port_id, str) or port_id not in all_by_id
               or all_by_id[port_id].obstacle_class != "port" for port_id in port_ids):
            raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")

    def clear(a: Point, b: Point) -> bool:
        if a == b:
            return True
        if index is not None:
            return not index.collisions(ObstacleSegment(a, b), port_ids=port_ids,
                                        classes=classes, regions=regions)
        for left, top, right, bottom in rects:
            if a[1] == b[1] and top < a[1] < bottom and max(a[0], b[0]) > left and min(a[0], b[0]) < right:
                return False
            if a[0] == b[0] and left < a[0] < right and max(a[1], b[1]) > top and min(a[1], b[1]) < bottom:
                return False
        return True

    # Clear Manhattan candidates achieve the global raw bend/length floor.
    # Yield both finite elbows before building a visibility graph; a caller's
    # terminal preparation may reject one but accept the other.
    seeded = set()
    if initial_direction == -1:
        for via in sorted({(end[0], start[1]), (start[0], end[1])}):
            path = []
            for point in (start, via, end):
                if not path or point != path[-1]:
                    path.append(point)
            candidate = tuple(path)
            if candidate not in seeded and all(clear(a, b) for a, b in zip(candidate, candidate[1:])):
                if len(seeded) >= limit:
                    raise RouteSearchFailure("E_PRESENTATION_ROUTE_LIMIT")
                seeded.add(candidate)
                yield candidate
        if start == end:
            return

    memo_scope = index.route_memo_scope(classes, regions, port_ids) if index is not None else None
    graph_key = None
    memo = None
    if memo_scope is not None:
        memo, content_id = memo_scope
        graph_key = (
            "sparse-graph-v1", content_id, repr((start, end, grid_offset, bounds)),
            frozenset(port_ids), None if classes is None else frozenset(classes),
            None if regions is None else frozenset(regions),
        )
        graph = memo.results.get(graph_key)
    else:
        graph = None
    if graph is None:
        event_rects = rects
        if index is not None:
            event_rects = tuple(
                (left - item.clearance, top - item.clearance,
                 right + item.clearance, bottom + item.clearance)
                for item in items
                for left, top, right, bottom in (obstacle_envelope(item.geometry),)
            )
        graph = _build_sparse_graph(
            start, end, event_rects, grid_offset=grid_offset, bounds=bounds, clear=clear)
        if memo is not None and graph_key is not None:
            memo.store(graph_key, graph)
    ordered, adjacency, remaining_items = graph
    node_id = {point: number for number, point in enumerate(ordered)}
    source, target = node_id[start], node_id[end]
    remaining = dict(remaining_items)

    serial = count()
    # Completed-route callbacks are path-dependent. Only the same canonical
    # prefix can dominate another constrained label; a cheaper different path
    # may fail terminal preparation or whole-route acceptance later.
    initial = (source, initial_direction, 0, 0.0, (source,))
    histories = {(source,): 0.0}
    weighted_best: dict[tuple[int, int], float] = {(source, initial_direction): 0.0}
    queue: list[tuple[float, ...] | tuple] = []

    def lower_bound(node: int, direction: int) -> tuple[int, float]:
        if node == target:
            return (0, 0.0)
        if direction in (0, 1):
            return remaining.get((node, direction), (float("inf"), float("inf")))
        # The initial state has no incoming direction, so its first edge costs
        # no bend. Account for that special case directly.
        candidates = [
            (remaining.get((neighbor, edge_direction), (float("inf"), float("inf")))[0],
             distance + remaining.get((neighbor, edge_direction), (float("inf"), float("inf")))[1])
            for neighbor, edge_direction, distance in adjacency[node]
        ]
        return min(candidates, default=(float("inf"), float("inf")))

    def priority(state: tuple[int, int, int, float, tuple[int, ...]]):
        node, direction, bends, length, path = state
        if bend_penalty is None:
            lower_bends, lower_length = lower_bound(node, direction)
            return (bends + lower_bends, length + lower_length,
                    length, next(serial), state)
        point = ordered[node]
        heuristic = abs(point[0] - end[0]) + abs(point[1] - end[1])
        cost = length + bends * bend_penalty
        return (cost + heuristic, heuristic, cost, bends, length, next(serial), state)

    if lower_bound(source, initial_direction)[0] == float("inf"):
        raise RouteSearchFailure("E_CONNECTOR_UNROUTABLE")
    heappush(queue, priority(initial))
    expanded = len(seeded)
    yielded: set[tuple[Point, ...]] = set(seeded)
    while queue:
        entry = heappop(queue)
        state = entry[-1]
        node, direction, bends, length, path = state
        key = (node, direction)
        if bend_penalty is None:
            if length != histories.get(path):
                continue
        elif length + bend_penalty * bends != weighted_best.get(key):
            continue
        expanded += 1
        if expanded > limit:
            raise RouteSearchFailure("E_PRESENTATION_ROUTE_LIMIT")
        if node == target:
            points: list[Point] = []
            for point in (ordered[index_] for index_ in path):
                if len(points) >= 2:
                    first, second = points[-2:]
                    same_axis = (first[0] == second[0] == point[0]
                                 or first[1] == second[1] == point[1])
                    same_direction = ((second[0] - first[0]) * (point[0] - second[0]) >= 0
                                      and (second[1] - first[1]) * (point[1] - second[1]) >= 0)
                    if same_axis and same_direction:
                        points.pop()
                if not points or point != points[-1]:
                    points.append(point)
            candidate = tuple(points)
            if candidate not in yielded:
                yielded.add(candidate)
                yield candidate
            continue
        for neighbor, next_direction, distance in adjacency[node]:
            if neighbor in path:
                continue
            if bend_penalty is None and (neighbor, next_direction) not in remaining:
                continue
            segment = ObstacleSegment(ordered[node], ordered[neighbor])
            if any(obstacles_intersect(segment,
                    ObstacleSegment(ordered[path[index_]], ordered[path[index_ + 1]]))
                    for index_ in range(len(path) - 2)):
                continue
            next_bends = bends + int(direction not in (-1, next_direction))
            next_length = length + distance
            next_key = (neighbor, next_direction)
            next_path = (*path, neighbor)
            if direction == next_direction and len(path) > 1:
                a, b, c = ordered[path[-2]], ordered[node], ordered[neighbor]
                if ((b[0] - a[0]) * (c[0] - b[0]) >= 0
                        and (b[1] - a[1]) * (c[1] - b[1]) >= 0):
                    next_path = (*path[:-1], neighbor)
            if bend_penalty is None:
                if next_length >= histories.get(next_path, float("inf")):
                    continue
                histories[next_path] = next_length
            else:
                score = next_length + bend_penalty * next_bends
                previous_score = weighted_best.get(next_key)
                if previous_score is not None and score >= previous_score:
                    continue
                weighted_best[next_key] = score
            child = (neighbor, next_direction, next_bends, next_length, next_path)
            heappush(queue, priority(child))
    if not yielded:
        raise RouteSearchFailure("E_CONNECTOR_UNROUTABLE")
