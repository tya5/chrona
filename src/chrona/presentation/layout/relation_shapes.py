"""Finite relation-shape proposals; no visibility graph or acceptance policy."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite

from chrona.presentation.layout.obstacles import ObstacleSegment, SurfaceObstacleIndex, obstacle_envelope
from chrona.presentation.layout.ports import ConnectorEgress

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


def supplemental_relation_channel_candidates(
    start: Point,
    end: Point,
    *,
    bounds: Bounds,
    channels: RelationShapeChannels,
    obstacles: SurfaceObstacleIndex,
    route_stroke_width: float,
    grid_offset: float = 2.0,
    classes: tuple[str, ...] = ("mark", "text", "label-visual"),
    regions: tuple[str, ...] = ("timeline", "group-header"),
) -> Iterator[Path]:
    """Yield at most eight outer-channel shapes for a label-repair route.

    These finite supplemental proposals are intentionally separate from the
    normal first-fit candidate grammar. The caller enables them only when a
    route-label repair domain contains retained label obstacles.
    """
    _check_bounds(bounds)
    if any(len(point) != 2 or not all(_finite(value) for value in point) for point in (start, end)):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape endpoints must be finite")
    if not _finite(route_stroke_width) or route_stroke_width < 0:
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: route stroke width must be finite and nonnegative")
    if not _finite(grid_offset) or grid_offset < 0:
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: shape grid offset must be finite and nonnegative")
    if start == end:
        return

    left, top, right, bottom = bounds
    x1, y1 = start
    x2, y2 = end
    low_y, high_y = sorted((y1, y2))
    rows = set(channels.rows)
    label_classes = tuple(name for name in classes if name in {"text", "label-visual"})
    for item in obstacles.select(classes=classes, regions=regions):
        _, obstacle_top, _, obstacle_bottom = obstacle_envelope(item.geometry)
        contact_offset = item.clearance + grid_offset
        for value in (obstacle_top - contact_offset, obstacle_bottom + contact_offset):
            if top <= value <= bottom:
                rows.add(value)
    interior_rows = tuple(value for value in rows if low_y < value < high_y)
    if len(interior_rows) < 2:
        return
    start_rows = tuple(sorted(interior_rows, key=lambda value: (abs(value - y1), value))[:2])
    end_rows = tuple(sorted(interior_rows, key=lambda value: (abs(value - y2), value))[:2])
    if not start_rows or not end_rows:
        return

    x_low, x_high = sorted((x1, x2))

    def clear_channel(x: float, vertical_top: float, vertical_bottom: float) -> bool:
        segment = ObstacleSegment((x, vertical_top), (x, vertical_bottom))
        if obstacles.collisions(segment, classes=classes, regions=regions):
            return False
        return not label_classes or not obstacles.collisions(
            ObstacleSegment(segment.start, segment.end, route_stroke_width),
            classes=label_classes, regions=regions)

    proposals = []
    for start_row in start_rows:
        for end_row in end_rows:
            if start_row == end_row:
                continue
            vertical_top, vertical_bottom = sorted((start_row, end_row))
            outward_columns = []
            for candidate in sorted((value for value in channels.columns if value < x_low), reverse=True):
                if clear_channel(candidate, vertical_top, vertical_bottom):
                    outward_columns.append(candidate)
                    break
            for candidate in sorted(value for value in channels.columns if value > x_high):
                if clear_channel(candidate, vertical_top, vertical_bottom):
                    outward_columns.append(candidate)
                    break
            for column in outward_columns:
                raw = (start, (x1, start_row), (column, start_row), (column, end_row),
                       (x2, end_row), end)
                path = _canonical_shape_path(raw, bounds)
                if path is None or path in proposals:
                    continue
                if label_classes and any(obstacles.collisions(
                        ObstacleSegment(a, b, route_stroke_width), classes=label_classes, regions=regions)
                        for a, b in zip(path, path[1:])):
                    continue
                proposals.append(path)
    yield from proposals[:8]


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
