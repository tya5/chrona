"""Finite, renderer-neutral annotation connector topology trials."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import (
    ObstacleSegment, SurfaceObstacleIndex, obstacle_envelope,
)
from chrona.presentation.layout.routing import relation_route_quality, route_orthogonal
from chrona.presentation.layout.surface_quality import PathCommand


HARD_CLASSES = ("mark", "text", "label-visual", "annotation-box", "port", "rule")
BRIDGE_CLASSES = ("dependency-route", "leader-route")


@dataclass(frozen=True)
class AnnotationRouteTrial:
    points: tuple[tuple[float, float], ...]
    commands: tuple[PathCommand, ...]
    topology: str
    crossing_ids: tuple[str, ...] = ()


def local_route_bounds(mark: tuple[float, float, float, float],
                       box: tuple[float, float, float, float],
                       attachment: tuple[float, float],
                       content: tuple[float, float, float, float], *,
                       clearance: float = 2.0) -> tuple[float, float, float, float]:
    """Bound detours to the mark/box pair, not the whole slide perimeter."""
    margin = max(box[2] / 2, 2 * clearance)
    left = max(content[0], min(mark[0], attachment[0]) - margin)
    top = max(content[1], min(mark[1], attachment[1]) - margin)
    right = min(content[2], max(mark[0] + mark[2], attachment[0]) + margin)
    bottom = min(content[3], max(mark[1] + mark[3], attachment[1]) + margin)
    return left, top, right, bottom


def route_annotation_candidate(start: tuple[float, float], end: tuple[float, float],
                               index: SurfaceObstacleIndex, *,
                               bounds: tuple[float, float, float, float],
                               port_ids: tuple[str, ...] = (), limit: int = 1024,
                               max_bends: int, max_detour_ratio: float,
                               allow_bridge: bool = False,
                               dense: bool = True,
                               connector_stroke_width: float = 1.0) -> AnnotationRouteTrial | None:
    """Try strict first; a rail may bridge only transverse route strokes."""
    for topology in (("strict", "bridge") if allow_bridge else ("strict",)):
        classes = None if topology == "strict" else HARD_CLASSES
        best: tuple[tuple[int, float, int, tuple[tuple[float, float], ...]],
                    AnnotationRouteTrial] | None = None
        for points in _sparse_elbows(start, end, index, bounds=bounds):
            if not relation_route_quality(points, max_bends=max_bends,
                                          max_detour_ratio=max_detour_ratio):
                continue
            if any(index.collisions(ObstacleSegment(a, b), classes=classes, port_ids=port_ids)
                   for a, b in zip(points, points[1:])):
                continue
            crossings = () if topology == "strict" else _crossings(
                points, index, connector_stroke_width=connector_stroke_width)
            if crossings is None or len(crossings) > 8:
                continue
            commands = () if not crossings else _bridged_commands(points, crossings)
            if commands is None:
                continue
            crossing_ids = tuple(item[2] for item in crossings)
            length = geometry_sum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                                  for a, b in zip(points, points[1:]))
            rank = (len(crossings), length, len(points) - 2, points)
            candidate = AnnotationRouteTrial(points, commands, topology, crossing_ids)
            if best is None or rank < best[0]:
                best = rank, candidate
            if topology == "strict":
                return candidate
        if best is not None:
            return best[1]
        if not dense:
            continue
        try:
            points = route_orthogonal(start, end, index, bounds=bounds,
                                      port_ids=port_ids, classes=classes, limit=limit)
        except ValueError:
            continue
        if not relation_route_quality(points, max_bends=max_bends,
                                      max_detour_ratio=max_detour_ratio):
            continue
        if topology == "strict":
            return AnnotationRouteTrial(points, (), topology)
        crossings = _crossings(points, index, connector_stroke_width=connector_stroke_width)
        if crossings is None or len(crossings) > 8:
            continue
        commands = _bridged_commands(points, crossings)
        if commands is not None:
            return AnnotationRouteTrial(points, commands, topology,
                                        tuple(item[2] for item in crossings))
    return None


def _sparse_elbows(start: tuple[float, float], end: tuple[float, float],
                   index: SurfaceObstacleIndex, *, bounds: tuple[float, float, float, float]
                   ) -> tuple[tuple[tuple[float, float], ...], ...]:
    """At most 1024 stable low-bend paths before dense graph expansion."""
    left, top, right, bottom = bounds
    envelopes = tuple(obstacle_envelope(item.geometry) for item in index.all())
    xs = {start[0], end[0]}
    ys = {start[1], end[1]}
    for box in envelopes:
        xs.update((box[0] - 2.0, box[2] + 2.0))
        ys.update((box[1] - 2.0, box[3] + 2.0))
    xs = {x for x in xs if left <= x <= right}
    ys = {y for y in ys if top <= y <= bottom}
    near_source_x = sorted(xs, key=lambda value: (abs(value - start[0]), value))[:16]
    near_target_x = sorted(xs, key=lambda value: (abs(value - end[0]), value))[:16]
    near_source_y = sorted(ys, key=lambda value: (abs(value - start[1]), value))[:16]
    near_target_y = sorted(ys, key=lambda value: (abs(value - end[1]), value))[:16]
    paths: list[tuple[tuple[float, float], ...]] = []
    seen = set()

    def include(raw: tuple[tuple[float, float], ...]) -> None:
        normalized: list[tuple[float, float]] = []
        for point in raw:
            if normalized and point == normalized[-1]:
                continue
            if len(normalized) >= 2 and ((normalized[-2][0] == normalized[-1][0] == point[0])
                                         or (normalized[-2][1] == normalized[-1][1] == point[1])):
                normalized[-1] = point
            else:
                normalized.append(point)
        path = tuple(normalized)
        if len(path) >= 2 and path[0] != path[-1] and path not in seen:
            seen.add(path)
            paths.append(path)

    if start[0] == end[0] or start[1] == end[1]:
        include((start, end))
    # A previously accepted stroke is a likely local barrier. Probe its
    # adjacent clear corridor before generic endpoint-neighborhood pairs.
    route_x = set()
    route_y = set()
    for item in index.select(classes=BRIDGE_CLASSES):
        geometry = item.geometry
        if not isinstance(geometry, ObstacleSegment):
            continue
        if geometry.start[0] == geometry.end[0]:
            route_x.update((geometry.start[0] - 2.0, geometry.start[0] + 2.0))
        if geometry.start[1] == geometry.end[1]:
            route_y.update((geometry.start[1] - 2.0, geometry.start[1] + 2.0))
    for x in sorted((x for x in route_x if x in xs), key=lambda value: (abs(value - end[0]), value)):
        include((start, (x, start[1]), (x, end[1]), end))
    for y in sorted((y for y in route_y if y in ys), key=lambda value: (abs(value - start[1]), value)):
        include((start, (start[0], y), (end[0], y), end))

    # Low-rank endpoint-relative pairs reach the useful local corridors first.
    for rank in range(31):
        for y_index in range(16):
            x_index = rank - y_index
            if not 0 <= x_index < 16:
                continue
            if y_index < len(near_source_y) and x_index < len(near_target_x):
                y, x = near_source_y[y_index], near_target_x[x_index]
                include((start, (start[0], y), (x, y), (x, end[1]), end))
            if y_index < len(near_source_x) and x_index < len(near_target_y):
                x, y = near_source_x[y_index], near_target_y[x_index]
                include((start, (x, start[1]), (x, y), (end[0], y), end))
            if len(paths) >= 128:
                return tuple(paths[:128])
    for x in (*near_target_x, *near_source_x):
        include((start, (x, start[1]), (x, end[1]), end))
    for y in (*near_source_y, *near_target_y):
        include((start, (start[0], y), (end[0], y), end))
    return tuple(paths[:128])


def _crossings(points: tuple[tuple[float, float], ...], index: SurfaceObstacleIndex, *,
               connector_stroke_width: float = 1.0
               ) -> tuple[tuple[int, float, str, tuple[float, float], float], ...] | None:
    result: list[tuple[int, float, str, tuple[float, float], float]] = []
    for segment_index, (start, end) in enumerate(zip(points, points[1:])):
        candidate = ObstacleSegment(start, end)
        for obstacle in index.collisions(candidate, classes=BRIDGE_CLASSES):
            other = obstacle.geometry
            if not isinstance(other, ObstacleSegment):
                return None
            horizontal = start[1] == end[1] and other.start[0] == other.end[0]
            vertical = start[0] == end[0] and other.start[1] == other.end[1]
            if not (horizontal or vertical):
                return None
            point = ((other.start[0], start[1]) if horizontal else (start[0], other.start[1]))
            length = abs(end[0] - start[0]) + abs(end[1] - start[1])
            distance = abs(point[0] - start[0]) + abs(point[1] - start[1])
            gap = max(4.0, other.stroke_width + connector_stroke_width + 4.0)
            other_distance = min(abs(point[0] - other.start[0]) + abs(point[1] - other.start[1]),
                                 abs(point[0] - other.end[0]) + abs(point[1] - other.end[1]))
            # The gap is cut along this connector, not along the crossed
            # stroke. Its endpoint clearance is governed by stroke width.
            endpoint_clearance = max(0.5, other.stroke_width / 2 + 0.5)
            if not (gap / 2 < distance < length - gap / 2
                    and other_distance > endpoint_clearance):
                return None
            result.append((segment_index, distance, obstacle.placement_id, point, gap))
    result.sort(key=lambda item: (item[0], item[1], item[2]))
    if len({(item[0], item[3]) for item in result}) != len(result):
        return None
    return tuple(result)


def _bridged_commands(points: tuple[tuple[float, float], ...],
                      crossings: tuple[tuple[int, float, str, tuple[float, float], float], ...]
                      ) -> tuple[PathCommand, ...] | None:
    commands = [PathCommand("move", (points[0],))]
    for segment_index, (start, end) in enumerate(zip(points, points[1:])):
        length = abs(end[0] - start[0]) + abs(end[1] - start[1])
        direction = ((end[0] - start[0]) / length, (end[1] - start[1]) / length)
        previous = 0.0
        for _, distance, _, _, gap in (item for item in crossings if item[0] == segment_index):
            before, after = distance - gap / 2, distance + gap / 2
            if before <= previous or after >= length:
                return None
            commands.append(PathCommand("line", ((start[0] + direction[0] * before,
                                                   start[1] + direction[1] * before),)))
            commands.append(PathCommand("move", ((start[0] + direction[0] * after,
                                                   start[1] + direction[1] * after),)))
            previous = after
        commands.append(PathCommand("line", (end,)))
    return tuple(commands)


def visible_segments(trial: AnnotationRouteTrial) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    """Only painted subpaths enter the later-placement obstacle inventory."""
    if not trial.commands:
        return tuple(zip(trial.points, trial.points[1:]))
    current = None
    segments = []
    for command in trial.commands:
        point = command.points[0]
        if command.kind == "move":
            current = point
        elif command.kind == "line":
            if current is not None and current != point:
                segments.append((current, point))
            current = point
    return tuple(segments)
