"""Finite relation-shape proposals; no visibility graph or acceptance policy."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from heapq import heappop, heappush
from math import isfinite
from collections.abc import Callable, Iterator

from chrona.presentation.layout.obstacles import ObstacleSegment, SurfaceObstacleIndex, obstacle_envelope
from chrona.presentation.layout.ports import ConnectorEgress, outward_corridor_ends
from chrona.presentation.layout.route_search import RouteSearchFailure

Point = tuple[float, float]
Path = tuple[Point, ...]
Bounds = tuple[float, float, float, float]


@dataclass(frozen=True)
class RelationShapeChannels:
    columns: tuple[float, ...]
    rows: tuple[float, ...]

    def __post_init__(self):
        for values in (self.columns, self.rows):
            if (not isinstance(values, tuple) or any(not _finite(value) for value in values)
                    or values != tuple(sorted(set(values)))):
                raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape channels must be finite, sorted and unique")


def shape_channels(obstacles: SurfaceObstacleIndex, *, bounds: Bounds,
                   row_edges: tuple[tuple[float, float], ...] = (), grid_offset: float = 2.0,
                   classes: tuple[str, ...] = ("mark", "text", "label-visual"),
                   regions: tuple[str, ...] = ("timeline", "group-header")) -> RelationShapeChannels:
    """Prepare contacts from the selected inventory and completed row gaps only."""
    _check_bounds(bounds)
    if not _finite(grid_offset) or grid_offset < 0:
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape grid offset must be finite and nonnegative")
    if any(len(row) != 2 or not all(_finite(value) for value in row) or row[0] > row[1] for row in row_edges):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape row edges must be finite and ordered")
    left, top, right, bottom = bounds
    columns = {left, right}
    for obstacle in obstacles.select(classes=classes, regions=regions):
        x1, _, x2, _ = obstacle_envelope(obstacle.geometry)
        for value in (x1 - obstacle.clearance - grid_offset, x2 + obstacle.clearance + grid_offset):
            if left <= value <= right:
                columns.add(value)
    rows = {top, bottom}
    ordered = sorted(row_edges)
    for before, after in zip(ordered, ordered[1:]):
        if before[1] <= after[0]:
            value = (before[1] + after[0]) / 2
            if top <= value <= bottom:
                rows.add(value)
    return RelationShapeChannels(tuple(sorted(columns)), tuple(sorted(rows)))


def recovery_shape_channels(obstacles: SurfaceObstacleIndex, *, bounds: Bounds,
                            row_edges: tuple[tuple[float, float], ...] = (), grid_offset: float = 2.0,
                            classes: tuple[str, ...] = ("mark", "text", "label-visual"),
                            regions: tuple[str, ...] = ("timeline", "group-header")) -> RelationShapeChannels:
    """Complete recovery channels from selected obstacle edges and row gaps."""
    base = shape_channels(obstacles, bounds=bounds, row_edges=row_edges, grid_offset=grid_offset,
                          classes=classes, regions=regions)
    top, bottom = bounds[1], bounds[3]
    rows = set(base.rows)
    for obstacle in obstacles.select(classes=classes, regions=regions):
        _, y1, _, y2 = obstacle_envelope(obstacle.geometry)
        for value in (y1 - obstacle.clearance - grid_offset,
                      y2 + obstacle.clearance + grid_offset):
            if top <= value <= bottom:
                rows.add(value)
    return RelationShapeChannels(base.columns, tuple(sorted(rows)))


def relation_channel_candidates(
    start: Point, end: Point, *, bounds: Bounds, channels: RelationShapeChannels,
    obstacles: SurfaceObstacleIndex, port_ids: tuple[str, ...],
    classes: tuple[str, ...] = ("mark", "text", "label-visual"),
    regions: tuple[str, ...] = ("timeline", "group-header"),
    max_bends: int, initial_axis: int, initial_sign: int,
    terminal_axis: int, terminal_sign: int,
    max_detour_ratio: float, direct_length: float,
    source_prefix_length: float, target_suffix_length: float,
    stroke_width: float, expansion_limit: int, on_expansion: Callable[[], None],
) -> Iterator[Path]:
    """Enumerate simple completed-channel paths in stable least-bend/length order.

    Every processed path-history state consumes the caller's existing expansion
    allowance. The implicit channel grid is finite; the caller's ordinary
    pair/stage limits bound traversal without an independent proposal cap.
    """
    _check_bounds(bounds)
    if any(len(point) != 2 or not all(_finite(value) for value in point) for point in (start, end)):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: channel endpoints must be finite")
    if (isinstance(expansion_limit, bool) or not isinstance(expansion_limit, int)
            or expansion_limit < 1 or isinstance(max_bends, bool) or not isinstance(max_bends, int)
            or max_bends < 0 or initial_axis not in {0, 1} or terminal_axis not in {0, 1}
            or initial_sign not in {-1, 1} or terminal_sign not in {-1, 1}
            or not all(_finite(value) for value in (max_detour_ratio, direct_length,
                                                     source_prefix_length, target_suffix_length, stroke_width))
            or max_detour_ratio <= 0 or min(direct_length, source_prefix_length, target_suffix_length) < 0
            or stroke_width < 0
            or not callable(on_expansion)):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: channel expansion limit must be positive")
    if start == end:
        return
    if any(not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]) for x, y in (start, end)):
        return
    if (direct_length > 0 and source_prefix_length + abs(start[0] - end[0])
            + abs(start[1] - end[1]) + target_suffix_length > direct_length * max_detour_ratio):
        return

    columns = tuple(sorted({value for value in (*channels.columns, start[0], end[0])
                            if bounds[0] <= value <= bounds[2]}))
    rows = tuple(sorted({value for value in (*channels.rows, start[1], end[1])
                         if bounds[1] <= value <= bounds[3]}))
    # Generate neighboring visible channel intersections lazily. This avoids
    # materializing the potentially large Cartesian grid before bounded work.
    def neighbors(point: Point):
        x, y = point
        x_index = columns.index(x)
        y_index = rows.index(y)
        candidates = []
        if x_index:
            candidates.append((columns[x_index - 1], y))
        if x_index + 1 < len(columns):
            candidates.append((columns[x_index + 1], y))
        if y_index:
            candidates.append((x, rows[y_index - 1]))
        if y_index + 1 < len(rows):
            candidates.append((x, rows[y_index + 1]))
        for candidate in sorted(candidates):
            if obstacles.collisions(ObstacleSegment(point, candidate, stroke_width), port_ids=port_ids,
                                    classes=classes, regions=regions):
                continue
            yield candidate

    def remaining_bend_bound(point: Point, incoming_axis: int) -> int:
        dx, dy = end[0] - point[0], end[1] - point[1]
        if dx == 0 and dy == 0:
            return int(incoming_axis != terminal_axis)
        legs = ((1,),) if dx == 0 else (((0,),) if dy == 0 else ((0, 1), (1, 0)))
        values = []
        for route_axes in legs:
            turns = int(incoming_axis != route_axes[0])
            turns += sum(left != right for left, right in zip(route_axes, route_axes[1:]))
            turns += int(route_axes[-1] != terminal_axis)
            values.append(turns)
        return min(values)

    # A* orders by admissible completed-route bend/length lower bounds; ties
    # keep canonical coordinate history order.
    start_bound = remaining_bend_bound(start, initial_axis)
    pending = [(start_bound, abs(start[0] - end[0]) + abs(start[1] - end[1]),
                (start,), start, initial_axis, initial_sign, 0, 0.0)]
    best_state_path = {(start, initial_axis, initial_sign, 0): (0.0, (start,))}
    expansions = 0
    while pending and expansions < expansion_limit:
        _, _, history, point, previous_axis, previous_sign, bends, length = heappop(pending)
        state = (point, previous_axis, previous_sign, bends)
        if best_state_path.get(state) != (length, history):
            continue
        on_expansion()
        expansions += 1
        if point == end:
            path = _canonical_shape_path(history, bounds)
            if (path is not None and (previous_axis != terminal_axis or previous_sign == terminal_sign)
                    and bends + int(previous_axis != terminal_axis) <= max_bends):
                yield path
            continue
        visited = set(history)
        for candidate in neighbors(point):
            if candidate in visited:
                continue
            axis = 0 if candidate[1] == point[1] else 1
            sign = (candidate[axis] > point[axis]) - (candidate[axis] < point[axis])
            if axis == previous_axis and sign != previous_sign:
                continue
            next_bends = bends + int(previous_axis not in {-1, axis})
            remaining = remaining_bend_bound(candidate, axis)
            if next_bends + remaining > max_bends:
                continue
            next_length = length + abs(candidate[0] - point[0]) + abs(candidate[1] - point[1])
            if (direct_length > 0 and source_prefix_length + next_length
                    + abs(candidate[0] - end[0]) + abs(candidate[1] - end[1]) + target_suffix_length
                    > direct_length * max_detour_ratio):
                continue
            state = (candidate, axis, sign, next_bends)
            next_history = (*history, candidate)
            previous_path = best_state_path.get(state)
            if previous_path is not None and previous_path <= (next_length, next_history):
                continue
            best_state_path[state] = (next_length, next_history)
            lower_length = next_length + abs(candidate[0] - end[0]) + abs(candidate[1] - end[1])
            heappush(pending, (next_bends + remaining, lower_length,
                next_history, candidate, axis, sign, next_bends, next_length))
    if pending and expansions == expansion_limit:
        raise RouteSearchFailure("E_PRESENTATION_ROUTE_LIMIT",
            detail="The port pair expansion quota was reached during recovery channel completion.")


def first_fit_port_pairs(pairs: tuple[tuple[ConnectorEgress, ConnectorEgress], ...]
                         ) -> tuple[tuple[ConnectorEgress, ConnectorEgress], ...]:
    """Sort admitted ports only; stable ties retain full/minimum entry-stub order."""
    source_order = {"end": 0, "start": 1, "above": 2, "below": 3}
    target_order = {"start": 0, "end": 1, "above": 2, "below": 3}
    if any(source.side not in source_order or target.side not in target_order for source, target in pairs):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape port sides must be end, start, above or below")
    return tuple(sorted(pairs, key=lambda pair: (source_order[pair[0].side], target_order[pair[1].side],
                                                not pair[1].stub)))


def relation_shape_candidates(start: Point, end: Point, *, bounds: Bounds,
                              channels: RelationShapeChannels) -> tuple[Path, ...]:
    """At most seven raw straight/L/Z/U proposals, canonical and bounds-contained."""
    _check_bounds(bounds)
    if any(len(point) != 2 or not all(_finite(value) for value in point) for point in (start, end)):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape endpoints must be finite")
    if start == end:
        return ()
    x1, y1 = start
    x2, y2 = end
    proposed = [(start, end)] if x1 == x2 or y1 == y2 else []
    proposed.extend(((start, (x2, y1), end), (start, (x1, y2), end)))
    for x in _nearest(channels.columns, (x1 + x2) / 2):
        proposed.append((start, (x, y1), (x, y2), end))
    for y in _nearest(channels.rows, (y1 + y2) / 2):
        proposed.append((start, (x1, y), (x2, y), end))
    result = []
    for raw in proposed:
        path = []
        for point in raw:
            if path and point == path[-1]:
                continue
            if len(path) >= 2:
                a, b = path[-2:]
                if ((a[0] == b[0] == point[0] or a[1] == b[1] == point[1])
                        and (b[0] - a[0]) * (point[0] - b[0]) >= 0
                        and (b[1] - a[1]) * (point[1] - b[1]) >= 0):
                    path.pop()
            path.append(point)
        candidate = tuple(path)
        if (len(candidate) >= 2 and candidate not in result
                and all(bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3] for x, y in candidate)):
            result.append(candidate)
    return tuple(result)


def outward_relation_shape_candidates(
    pair: tuple[ConnectorEgress, ConnectorEgress], *, source_run: float, target_run: float,
    bounds: Bounds, channels: RelationShapeChannels,
) -> tuple[Path, ...]:
    """Propose channel shapes between the already-reserved outward endpoint leads.

    The returned path begins/ends at the exposed ports; semantic-to-exposed
    comparison corridors remain the caller's responsibility. All candidates
    use the existing finite straight/L/Z/U grammar and are only proposals:
    callers still run normal route preparation and acceptance.
    """
    _check_bounds(bounds)
    source, target = pair
    source_lead, target_lead = outward_corridor_ends(
        pair, source_run=source_run, target_run=target_run)
    middle_paths = relation_shape_candidates(source_lead, target_lead,
                                            bounds=bounds, channels=channels)
    result = []
    for middle in middle_paths:
        path = _canonical_shape_path((source.exposed_port, *middle, target.exposed_port), bounds)
        if path is not None and path not in result:
            result.append(path)
    return tuple(result)


def _canonical_shape_path(raw: Path, bounds: Bounds) -> Path | None:
    path = []
    for point in raw:
        if path and point == path[-1]:
            continue
        if len(path) >= 2:
            a, b = path[-2:]
            if ((a[0] == b[0] == point[0] or a[1] == b[1] == point[1])
                    and (b[0] - a[0]) * (point[0] - b[0]) >= 0
                    and (b[1] - a[1]) * (point[1] - b[1]) >= 0):
                path.pop()
        path.append(point)
    candidate = tuple(path)
    if (len(candidate) < 2 or any(not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3])
                                   for x, y in candidate)
            or any(a[0] != b[0] and a[1] != b[1] for a, b in zip(candidate, candidate[1:]))):
        return None
    return candidate


def _nearest(values: tuple[float, ...], middle: float) -> tuple[float, ...]:
    candidates = set()
    low, high = bisect_right(values, middle) - 1, bisect_left(values, middle)
    if low >= 0:
        candidates.add(values[low])
    if high < len(values):
        candidates.add(values[high])
    return tuple(sorted(candidates, key=lambda value: (abs(value - middle), value)))


def _check_bounds(bounds: Bounds) -> None:
    if (len(bounds) != 4 or not all(_finite(value) for value in bounds)
            or bounds[0] > bounds[2] or bounds[1] > bounds[3]):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape bounds must be finite and ordered")


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
