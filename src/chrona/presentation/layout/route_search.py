"""Bounded sparse candidate search for orthogonal Layout routes."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import hypot, isfinite, nextafter

from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleSegment,
    SurfaceObstacleIndex,
    obstacle_envelope,
)


class RouteSearchFailure(ValueError):
    """A bounded orthogonal search found no route; unrelated ValueErrors propagate."""

    def __init__(self, code: str, *, detail: str | None = None) -> None:
        # Keep the stable error string used by typed transport and route memoization.
        super().__init__(code)
        self.detail = detail


Point = tuple[float, float]
Path = tuple[Point, ...]
Edge = tuple[int, int, float]
SparseGraph = tuple[
    tuple[Point, ...],
    tuple[tuple[Edge, ...], ...],
    tuple[tuple[tuple[int, int], tuple[int, float]], ...],
]

HistoryEntry = tuple[float, float, float, tuple[Point, Point]]


@dataclass(frozen=True, slots=True)
class _HistoryIndex:
    """Branch-local completed prefix; the current terminal is not indexed.

    Coordinates select nearby lines, intervals reject distant segments, and
    the existing exact predicate alone decides intersection. Immutable tuples
    let straight extensions reuse a prefix without changing sibling branches.
    """

    horizontal: tuple[HistoryEntry, ...] = ()
    vertical: tuple[HistoryEntry, ...] = ()

    def add(self, segment: tuple[Point, Point]) -> _HistoryIndex:
        a, b = segment
        horizontal = a[1] == b[1]
        axis = 0 if horizontal else 1
        entry = (a[1 - axis], min(a[axis], b[axis]),
                 max(a[axis], b[axis]), segment)
        entries = self.horizontal if horizontal else self.vertical
        position = bisect_right(entries, entry)
        updated = (*entries[:position], entry, *entries[position:])
        return (type(self)(updated, self.vertical) if horizontal
                else type(self)(self.horizontal, updated))

    def intersects(self, segment: tuple[Point, Point]) -> bool:
        a, b = segment
        for entries, axis in ((self.horizontal, 0), (self.vertical, 1)):
            # Round the broad phase outwards; never discard an exact hit at
            # a floating-point boundary. This does not relax the oracle.
            line_low = nextafter(min(a[1 - axis], b[1 - axis]) - 1e-9, -float("inf"))
            line_high = nextafter(max(a[1 - axis], b[1 - axis]) + 1e-9, float("inf"))
            low = nextafter(min(a[axis], b[axis]) - 1e-9, -float("inf"))
            high = nextafter(max(a[axis], b[axis]) + 1e-9, float("inf"))
            first = bisect_left(entries, line_low, key=lambda entry: entry[0])
            last = bisect_right(entries, line_high, key=lambda entry: entry[0])
            for index in range(first, last):
                _, start, end, previous = entries[index]
                if end >= low and start <= high and _history_segments_intersect(segment, previous):
                    return True
        return False


def _history_segments_intersect(
    first: tuple[Point, Point], second: tuple[Point, Point],
) -> bool:
    """Fast equivalent of Layout's collision predicate for zero-stroke orthogonal segments."""
    (a, b), (c, d) = first, second
    if a == b or c == d:
        raise ValueError("E_LAYOUT_OBSTACLE_GEOMETRY: history segments must have positive length.")
    first_horizontal, second_horizontal = a[1] == b[1], c[1] == d[1]

    def interval_gap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, max(min(a0, a1), min(b0, b1)) - min(max(a0, a1), max(b0, b1)))

    if first_horizontal and second_horizontal:
        dx = interval_gap(a[0], b[0], c[0], d[0])
        dy = abs(a[1] - c[1])
    elif not first_horizontal and not second_horizontal:
        dx = abs(a[0] - c[0])
        dy = interval_gap(a[1], b[1], c[1], d[1])
    else:
        dx = interval_gap(a[0], b[0], c[0], d[0])
        dy = interval_gap(a[1], b[1], c[1], d[1])
    if hypot(dx, dy) > 1e-9:
        return False

    shared = set((a, b)).intersection((c, d))
    if not shared:
        return True
    if len(shared) == 2:
        return True
    point = next(iter(shared))
    other_first = b if a == point else a
    other_second = d if c == point else c
    cross = ((other_first[0] - point[0]) * (other_second[1] - point[1])
             - (other_first[1] - point[1]) * (other_second[0] - point[0]))
    dot = ((other_first[0] - point[0]) * (other_second[0] - point[0])
           + (other_first[1] - point[1]) * (other_second[1] - point[1]))
    return abs(cross) < 1e-9 and dot > 0


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
        raise ValueError(
            "E_LAYOUT_ROUTE_SEARCH_INPUT: start/end must be finite 2D points; grid_offset and bend_penalty "
            "must be finite and non-negative; limit must be a positive integer; initial_direction must be -1, 0, or 1."
        )
    if bounds is not None:
        if (len(bounds) != 4 or not all(isfinite(value) for value in bounds)
                or bounds[0] > bounds[2] or bounds[1] > bounds[3]):
            raise ValueError(
                "E_LAYOUT_ROUTE_SEARCH_INPUT: bounds must be finite ordered "
                "(left, top, right, bottom) coordinates."
            )
        if not (bounds[0] <= start[0] <= bounds[2]
                and bounds[1] <= start[1] <= bounds[3]
                and bounds[0] <= end[0] <= bounds[2]
                and bounds[1] <= end[1] <= bounds[3]):
            raise RouteSearchFailure(
                "E_CONNECTOR_UNROUTABLE", detail="The supplied bounds exclude the start or end point.")

    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    rects: tuple[tuple[float, float, float, float], ...]
    if index is None:
        rects = tuple(tuple(box) for box in obstacles)
        if any(len(box) != 4 or not all(isfinite(value) for value in box)
               or box[0] > box[2] or box[1] > box[3] for box in rects):
            raise ValueError(
                "E_LAYOUT_ROUTE_SEARCH_INPUT: each obstacle must be a finite ordered "
                "(left, top, right, bottom) rectangle."
            )
        items = ()
    else:
        items = index.select(classes=classes, regions=regions)
        rects = tuple(obstacle_envelope(item.geometry) for item in items)
        all_by_id = {item.placement_id: item for item in index.all()}
        if any(not isinstance(port_id, str) or port_id not in all_by_id
               or all_by_id[port_id].obstacle_class != "port" for port_id in port_ids):
            raise ValueError(
                "E_LAYOUT_OBSTACLE_EXEMPTION_INVALID: port_ids must identify existing port obstacles "
                "in this surface index."
            )

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
                    raise RouteSearchFailure(
                        "E_PRESENTATION_ROUTE_LIMIT",
                        detail="The candidate limit was reached while yielding clear Manhattan seed routes.",
                    )
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
    initial = (source, initial_direction, 0, 0.0, (source,), _HistoryIndex())
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

    def priority(state: tuple[int, int, int, float, tuple[int, ...], _HistoryIndex]):
        node, direction, bends, length, path, history = state
        if bend_penalty is None:
            lower_bends, lower_length = lower_bound(node, direction)
            return (bends + lower_bends, length + lower_length,
                    length, next(serial), state)
        point = ordered[node]
        heuristic = abs(point[0] - end[0]) + abs(point[1] - end[1])
        cost = length + bends * bend_penalty
        return (cost + heuristic, heuristic, cost, bends, length, next(serial), state)

    if lower_bound(source, initial_direction)[0] == float("inf"):
        raise RouteSearchFailure(
            "E_CONNECTOR_UNROUTABLE",
            detail="No sparse-graph route connects the requested endpoints within the supplied obstacles and bounds.",
        )
    heappush(queue, priority(initial))
    expanded = len(seeded)
    yielded: set[tuple[Point, ...]] = set(seeded)
    while queue:
        entry = heappop(queue)
        state = entry[-1]
        node, direction, bends, length, path, history = state
        key = (node, direction)
        if bend_penalty is None:
            if length != histories.get(path):
                continue
        elif length + bend_penalty * bends != weighted_best.get(key):
            continue
        expanded += 1
        if expanded > limit:
            raise RouteSearchFailure(
                "E_PRESENTATION_ROUTE_LIMIT",
                detail="The route-search expansion limit was reached before the candidate frontier was exhausted.",
            )
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
            segment = (ordered[node], ordered[neighbor])
            if history.intersects(segment):
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
            next_history = history
            if len(path) > 1 and len(next_path) > len(path):
                next_history = history.add((ordered[path[-2]], ordered[node]))
            child = (neighbor, next_direction, next_bends, next_length, next_path, next_history)
            heappush(queue, priority(child))
    if not yielded:
        raise RouteSearchFailure(
            "E_CONNECTOR_UNROUTABLE", detail="No clear route candidate connects the requested endpoints.")
