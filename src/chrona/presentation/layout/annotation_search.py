"""Finite, deterministic nearest-free search for a plot/content annotation box.

This module owns exactly the ``nearest-free`` search kind from the #466
candidate model: a bounded lattice search for a box that fits completely
inside a resolved region, avoids the candidate's declared obstacle classes,
and (when it lands in the plot) stays on the anchor's side of an as-of rule.
Region resolution, geometry and obstacle queries stay in Layout; nothing here
measures text, reads a Theme or serializes a primitive.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, fsum, log
from typing import Callable, Iterator

from chrona.presentation.layout.annotations import nearest_box_port
from chrona.presentation.layout.balloon_geometry import nearest_eligible_edge, tail_base_points
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, obstacle_envelope,
)
from chrona.presentation.layout.annotation_topology import (
    AnnotationRouteTrial, route_strict_bounded, strict_route_candidates,
)
from chrona.presentation.layout.ports import (
    ConnectorEgress, coincident_endpoint_port_ids, connector_egress_candidates,
)
from chrona.presentation.layout.routing import relation_route_quality
from chrona.presentation.layout.surface_quality import MarkPlacement


def _search_input_error(owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError("E_LAYOUT_ANNOTATION_SEARCH_INPUT: " + owner + " " + ", ".join(fields))


@dataclass(frozen=True)
class NearestFreeTrial:
    """One examined lattice position, whether or not it was accepted."""

    box: LabelRect
    accepted: bool


@dataclass(frozen=True)
class RoutedTailSearchResult:
    box: LabelRect | None
    tip: tuple[float, float] | None
    egress: ConnectorEgress | None
    route: AnnotationRouteTrial | None
    full_points: tuple[tuple[float, float], ...]
    box_trials: int
    route_states: int
    exhausted: bool = False


@dataclass(frozen=True)
class _OppositeRouteStream:
    """One admitted box/egress/edge strict-route prefix in the fallback pass."""

    box_index: int
    box: LabelRect
    egress: ConnectorEgress
    source_points: tuple[tuple[float, float], ...]
    endpoint_ports: tuple[str, ...]
    edge_order: int
    tip: tuple[float, float]
    candidate_index: SurfaceObstacleIndex
    route_iter: Iterator[tuple[tuple[float, float], ...]]


@dataclass(frozen=True)
class _OppositeRouteTrial:
    rank: tuple[object, ...]
    box: LabelRect
    tip: tuple[float, float]
    egress: ConnectorEgress
    route: AnnotationRouteTrial
    full_points: tuple[tuple[float, float], ...]


def _advance_opposite_route_stream(
        stream: _OppositeRouteStream, *, rule: ObstacleSegment,
        crossing_rule_id: str, max_bends: int, max_detour_ratio: float
        ) -> tuple[_OppositeRouteStream | None, _OppositeRouteTrial | None, bool]:
    """Consume and validate exactly one path from one admitted route stream."""
    try:
        points = next(stream.route_iter)
    except StopIteration:
        return None, None, False
    if (not all(a != b and (a[0] == b[0] or a[1] == b[1])
                for a, b in zip(points, points[1:]))
            or not relation_route_quality(points, max_bends=max_bends,
                                          max_detour_ratio=max_detour_ratio)
            or any(stream.candidate_index.collisions(
                ObstacleSegment(a, b), port_ids=stream.endpoint_ports,
                rule_host_id=crossing_rule_id)
                   for a, b in zip(points, points[1:]))
            or not _route_crosses_rule_once(points, rule)):
        return stream, None, True
    full_points = (*stream.source_points, *points[1:])
    if not relation_route_quality(full_points, max_bends=max_bends,
                                  max_detour_ratio=max_detour_ratio):
        return stream, None, True
    route = AnnotationRouteTrial(points, (), "strict")
    route_length = fsum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                        for a, b in zip(points, points[1:]))
    source_order = {"end": 0, "start": 1, "above": 2, "below": 3}[stream.egress.side]
    rank = (stream.box_index, len(points) - 2, route_length, source_order,
            stream.edge_order, stream.egress.exposed_port, stream.tip, points)
    return stream, _OppositeRouteTrial(rank, stream.box, stream.tip, stream.egress,
                                       route, full_points), True


def lattice_positions(region: LabelRect, box_size: tuple[float, float],
                      anchor_center: tuple[float, float], max_positions: int) -> tuple[LabelRect, ...]:
    """Return up to ``max_positions`` candidate boxes, nearest-first, deterministic.

    The lattice step on each axis is half the measured box dimension (at
    least one geometry unit), matching the #466 design.  Ties break by
    Manhattan anchor distance, block distance, inline distance, block
    coordinate, inline coordinate and lattice index.
    """
    width, height = box_size
    if width <= 0 or height <= 0 or max_positions < 1:
        raise _search_input_error("lattice box candidates", box_size=box_size,
                                  max_positions=max_positions, region=(region.x, region.y,
                                                                       region.width, region.height))
    min_x, min_y = region.x, region.y
    max_x, max_y = region.right - width, region.bottom - height
    if max_x < min_x or max_y < min_y:
        return ()
    step_x, step_y = max(width / 2, 1.0), max(height / 2, 1.0)
    columns = list(_axis_positions(min_x, max_x, step_x))
    rows = list(_axis_positions(min_y, max_y, step_y))
    raw = [(x, y) for y in rows for x in columns]

    def key(indexed: tuple[int, tuple[float, float]]) -> tuple[float, float, float, float, float, int]:
        index, (x, y) = indexed
        cx, cy = x + width / 2, y + height / 2
        block_distance = abs(cy - anchor_center[1])
        inline_distance = abs(cx - anchor_center[0])
        return (block_distance + inline_distance, block_distance, inline_distance, y, x, index)

    ordered = sorted(enumerate(raw), key=key)[:max_positions]
    return tuple(LabelRect(x, y, width, height) for _, (x, y) in ordered)


def coarse_lattice_positions(region: LabelRect, box_size: tuple[float, float],
                             anchor_center: tuple[float, float], max_positions: int) -> tuple[LabelRect, ...]:
    """Return a bounded, whole-region grid, nearest-first and deterministic.

    Unlike the fine lattice, this samples legal box-origin extents rather than
    stepping out from the anchor. The existing per-pass position budget is the
    only cap; a one-position pass samples the region center.
    """
    width, height = box_size
    if width <= 0 or height <= 0 or max_positions < 1:
        raise _search_input_error("coarse lattice box candidates", box_size=box_size,
                                  max_positions=max_positions, region=(region.x, region.y,
                                                                       region.width, region.height))
    min_x, min_y = region.x, region.y
    max_x, max_y = region.right - width, region.bottom - height
    if max_x < min_x or max_y < min_y:
        return ()
    if max_positions == 1:
        xs = ((min_x + max_x) / 2,)
        ys = ((min_y + max_y) / 2,)
    else:
        range_x, range_y = max_x - min_x, max_y - min_y
        if range_x == 0:
            columns, rows = 1, max_positions
        elif range_y == 0:
            columns, rows = max_positions, 1
        elif max_positions >= 4:
            dimensions = [(columns, max_positions // columns)
                          for columns in range(2, max_positions // 2 + 1)]

            def grid_score(pair: tuple[int, int]) -> tuple[float, int, int, int]:
                columns, rows = pair
                inline_step = range_x / (columns - 1)
                block_step = range_y / (rows - 1)
                return (abs(log(inline_step / block_step)), -(columns * rows),
                        abs(columns - rows), columns)

            columns, rows = min(dimensions, key=grid_score)
        else:
            if range_x >= range_y:
                columns, rows = max_positions, 1
            else:
                columns, rows = 1, max_positions
        xs = tuple(min_x + range_x * index / (columns - 1) for index in range(columns)) if columns > 1 else ((min_x + max_x) / 2,)
        ys = tuple(min_y + range_y * index / (rows - 1) for index in range(rows)) if rows > 1 else ((min_y + max_y) / 2,)
    raw = tuple(dict.fromkeys((x, y) for y in ys for x in xs))

    def key(indexed: tuple[int, tuple[float, float]]) -> tuple[float, float, float, float, float, int]:
        index, (x, y) = indexed
        cx, cy = x + width / 2, y + height / 2
        block_distance = abs(cy - anchor_center[1])
        inline_distance = abs(cx - anchor_center[0])
        return (block_distance + inline_distance, block_distance, inline_distance, y, x, index)

    ordered = sorted(enumerate(raw), key=key)[:max_positions]
    return tuple(LabelRect(x, y, width, height) for _, (x, y) in ordered)


def _candidate_positions(region: LabelRect, box_size: tuple[float, float],
                         anchor_center: tuple[float, float], max_positions: int,
                         search_pass: str) -> tuple[LabelRect, ...]:
    if search_pass == "fine":
        return lattice_positions(region, box_size, anchor_center, max_positions)
    if search_pass == "coarse":
        return coarse_lattice_positions(region, box_size, anchor_center, max_positions)
    raise _search_input_error("annotation search pass", search_pass=search_pass)


def _route_crosses_rule_once(points: tuple[tuple[float, float], ...],
                             rule: ObstacleSegment) -> bool:
    """Accept exactly one interior transverse crossing of a vertical as-of rule."""
    if rule.start[0] != rule.end[0]:
        return False
    rule_x = rule.start[0]
    low_y, high_y = sorted((rule.start[1], rule.end[1]))
    crossings = 0
    for point in points:
        if point[0] == rule_x and low_y <= point[1] <= high_y:
            # A route vertex on the rule is a touch, not an interior crossing.
            return False
    for start, end in zip(points, points[1:]):
        if start[1] == end[1] and min(start[0], end[0]) < rule_x < max(start[0], end[0]):
            if low_y < start[1] < high_y:
                crossings += 1
            else:
                # Do not sneak from one side to the other around a finite
                # rule endpoint; the single side transition must be the rule
                # crossing itself.
                return False
        elif start[0] == end[0] == rule_x:
            if max(min(start[1], end[1]), low_y) <= min(max(start[1], end[1]), high_y):
                return False
    return crossings == 1


def _axis_positions(minimum: float, maximum: float, step: float) -> tuple[float, ...]:
    positions = [minimum]
    value = minimum
    while value < maximum - 1e-9:
        value = min(value + step, maximum)
        positions.append(value)
    if positions[-1] != maximum:
        positions.append(maximum)
    # Deduplicate while keeping determinism (maximum may equal minimum).
    result: list[float] = []
    for position in positions:
        if not result or abs(result[-1] - position) > 1e-9:
            result.append(position)
    return tuple(result)


def nearest_free_box(*, region: LabelRect, anchor_center: tuple[float, float],
                     box_size: tuple[float, float], max_positions: int,
                     obstacles: SurfaceObstacleIndex, obstacle_classes: tuple[str, ...],
                     exempt_ids: tuple[str, ...] = (), host_id: str | None = None,
                     side_of_as_of: tuple[float, str] | None = None,
                     search_pass: str = "fine",
                     candidate_validator: Callable[[LabelRect], bool] | None = None
                     ) -> tuple[LabelRect | None, int]:
    """Return the first collision-free box on the lattice, and the trial count.

    ``side_of_as_of`` is ``(as_of_x, "start"|"end")``: when given, an
    accepted box must stay entirely on the anchor's declared side of the
    as-of rule's inline coordinate.
    """
    trials = 0
    for box in _candidate_positions(region, box_size, anchor_center, max_positions, search_pass):
        trials += 1
        if side_of_as_of is not None:
            as_of_x, side = side_of_as_of
            if (side == "start" and box.right > as_of_x) or (side == "end" and box.x < as_of_x):
                continue
        collisions = obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                          classes=obstacle_classes, port_ids=exempt_ids, host_id=host_id)
        if not collisions and (candidate_validator is None or candidate_validator(box)):
            return box, trials
    return None, trials


@dataclass(frozen=True)
class LeastCoveringBox:
    """The terminal box of a note with no free placement, and what it still covers."""

    box: LabelRect
    covered_owners: tuple[str, ...]


def _overlap_area(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    return (max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
            * max(0.0, min(first[3], second[3]) - max(first[1], second[1])))


def least_covering_box(*, region: LabelRect, anchor_center: tuple[float, float],
                       box_size: tuple[float, float], max_positions: int,
                       obstacles: SurfaceObstacleIndex, obstacle_classes: tuple[str, ...],
                       mark_owner: Callable[[str], str], own_owner: str,
                       host_id: str | None = None) -> LeastCoveringBox | None:
    """Choose the terminal box for a note that no declared search could place.

    A note box MUST NOT cover a mark of an object other than its anchor's.
    Every fine and coarse lattice position is ranked first by whether it
    covers another object's mark at all, then by the text and label visuals it
    meets (a box never hides a name), the number of other objects' marks it
    covers, the other declared obstacles it meets, the area of those marks it
    covers, and nearest-first.  A position that covers no other object's mark
    always beats one that does; when none exists the least-covering one is
    returned together with the covered owners so the
    caller can name them.
    """
    seen: set[tuple[float, float]] = set()
    best: tuple[tuple[bool, int, int, int, float, int], LabelRect, tuple[str, ...]] | None = None
    order = 0
    for search_pass in ("fine", "coarse"):
        for box in _candidate_positions(region, box_size, anchor_center, max_positions, search_pass):
            if (box.x, box.y) in seen:
                continue
            seen.add((box.x, box.y))
            order += 1
            geometry = ObstacleRect(box.x, box.y, box.right, box.bottom)
            hits = obstacles.collisions(geometry, classes=obstacle_classes, host_id=host_id)
            covered: dict[str, float] = {}
            others = words = 0
            for item in hits:
                if item.obstacle_class == "mark":
                    owner = mark_owner(item.placement_id)
                    if owner != own_owner:
                        envelope = obstacle_envelope(item.geometry)
                        covered[owner] = covered.get(owner, 0.0) + _overlap_area(
                            (box.x, box.y, box.right, box.bottom), envelope)
                elif item.obstacle_class in ("text", "label-visual"):
                    words += 1
                else:
                    others += 1
            key = (bool(covered), words, len(covered), others, fsum(covered.values()), order)
            if best is None or key < best[0]:
                best = (key, box, tuple(sorted(covered)))
            if best[0][:2] == (False, 0) and best[0][3] == 0:
                return LeastCoveringBox(best[1], best[2])
    return None if best is None else LeastCoveringBox(best[1], best[2])


def largest_free_extent(*, region: LabelRect, box_size: tuple[float, float],
                        obstacles: SurfaceObstacleIndex, obstacle_classes: tuple[str, ...],
                        host_id: str | None = None,
                        reach_from: LabelRect | None = None) -> tuple[float, float]:
    """The inline and block size of the largest obstacle-free rectangle in ``region``.

    The region is cut into cells of half the box on each axis (the lattice
    step of the box search, never finer than 1/48 of the region) and every
    cell meeting a declared obstacle is blocked.  With ``reach_from`` (a box
    that needs a connector to its anchor) only the free cells connected to the
    anchor's own cells count, since a box that cannot be joined to its anchor
    is not available to it.  The largest free rectangle of whole cells is the
    space the failed candidate actually had.
    """
    width, height = box_size
    if region.width <= 0 or region.height <= 0:
        return (0.0, 0.0)
    step_x = max(width / 2, 1.0, region.width / 48)
    step_y = max(height / 2, 1.0, region.height / 48)
    columns, rows = max(1, ceil(region.width / step_x)), max(1, ceil(region.height / step_y))
    free = [[not obstacles.collisions(
        ObstacleRect(region.x + column * step_x, region.y + row * step_y,
                     min(region.right, region.x + (column + 1) * step_x),
                     min(region.bottom, region.y + (row + 1) * step_y)),
        classes=obstacle_classes, host_id=host_id)
        for column in range(columns)] for row in range(rows)]
    if reach_from is not None:
        seeds = [(row, column) for row in range(rows) for column in range(columns)
                 if (region.x + column * step_x < reach_from.right
                     and region.x + (column + 1) * step_x > reach_from.x
                     and region.y + row * step_y < reach_from.bottom
                     and region.y + (row + 1) * step_y > reach_from.y)]
        reachable = [[False] * columns for _ in range(rows)]
        pending = list(seeds)
        for row, column in seeds:
            reachable[row][column] = True
        while pending:
            row, column = pending.pop()
            for next_row, next_column in ((row - 1, column), (row + 1, column),
                                          (row, column - 1), (row, column + 1)):
                if (0 <= next_row < rows and 0 <= next_column < columns
                        and free[next_row][next_column] and not reachable[next_row][next_column]):
                    reachable[next_row][next_column] = True
                    pending.append((next_row, next_column))
        free = reachable
    heights = [0] * columns
    best = (0.0, 0.0)
    best_area = 0.0
    for row in range(rows):
        for column in range(columns):
            heights[column] = heights[column] + 1 if free[row][column] else 0
        stack: list[tuple[int, int]] = []
        for column in range(columns + 1):
            current = heights[column] if column < columns else 0
            start = column
            while stack and stack[-1][1] >= current:
                start, level = stack.pop()
                span_x = min(region.width, (column - start) * step_x)
                span_y = min(region.height, level * step_y)
                if span_x * span_y > best_area:
                    best, best_area = (span_x, span_y), span_x * span_y
            stack.append((start, current))
    return best


def nearest_free_tail_box(*, region: LabelRect, anchor: LabelRect,
                          box_size: tuple[float, float], max_positions: int,
                          obstacles: SurfaceObstacleIndex, obstacle_classes: tuple[str, ...],
                          corner_radius: float, tail_base: float,
                          host_id: str | None = None,
                          side_of_as_of: tuple[float, str] | None = None,
                          search_pass: str = "fine"
                          ) -> tuple[LabelRect | None, tuple[float, float] | None, int]:
    """Return the first box whose body *and* tail edges clear every obstacle.

    One trial is one joint box-plus-connector evaluation (#466): a lattice
    position is only accepted once its balloon tail also avoids the
    candidate's mandatory obstacle classes, exempting only the anchor's own
    mark and the box's own (not-yet-registered) geometry.  The tail tip is
    the anchor's own nearest edge port to each trial box, resolved per trial.
    """
    anchor_center = (anchor.x + anchor.width / 2, anchor.y + anchor.height / 2)
    trials = 0
    for box in _candidate_positions(region, box_size, anchor_center, max_positions, search_pass):
        trials += 1
        if side_of_as_of is not None:
            as_of_x, side = side_of_as_of
            if (side == "start" and box.right > as_of_x) or (side == "end" and box.x < as_of_x):
                continue
        if obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=obstacle_classes, host_id=host_id):
            continue
        box_center = (box.x + box.width / 2, box.y + box.height / 2)
        tip = nearest_box_port(anchor, box_center)
        edge = nearest_eligible_edge(box, tip)
        radius = min(corner_radius, box.width / 2, box.height / 2)
        base_a, base_b = tail_base_points(box, tip, edge=edge, tail_base=tail_base, corner_radius=radius)
        tail_collides = any(
            obstacles.collisions(ObstacleSegment(start, end), classes=obstacle_classes, host_id=host_id)
            for start, end in ((base_a, tip), (tip, base_b)))
        if not tail_collides:
            return box, tip, trials
    return None, None, trials


def nearest_free_routed_tail_box(*, region: LabelRect, anchor: MarkPlacement, endpoint: str,
                                 siblings: tuple[MarkPlacement, ...],
                                 box_size: tuple[float, float], max_positions: int,
                                 obstacles: SurfaceObstacleIndex,
                                 obstacle_classes: tuple[str, ...], corner_radius: float,
                                 tail_base: float, content_bounds: tuple[float, float, float, float],
                                 host_id: str | None = None,
                                 side_of_as_of: tuple[float, str] | None = None,
                                 max_bends: int = 4, max_detour_ratio: float = 2.0,
                                 route_state_limit: int = 1024,
                                 search_pass: str = "fine",
                                 crossing_rule_id: str | None = None) -> RoutedTailSearchResult:
    """Find a free box with a strict routed connector ending at an exterior tip.

    Candidate-box trials and connector states have independent finite limits.
    The candidate box is inserted into a private obstacle index for route checks;
    accepted geometry is never written to the caller's monotone index here.
    """
    if crossing_rule_id is not None:
        return _nearest_free_routed_tail_box_across_rule(
            region=region, anchor=anchor, endpoint=endpoint, siblings=siblings,
            box_size=box_size, max_positions=max_positions, obstacles=obstacles,
            obstacle_classes=obstacle_classes, corner_radius=corner_radius,
            tail_base=tail_base, content_bounds=content_bounds, host_id=host_id,
            side_of_as_of=side_of_as_of, max_bends=max_bends,
            max_detour_ratio=max_detour_ratio, route_state_limit=route_state_limit,
            search_pass=search_pass, crossing_rule_id=crossing_rule_id)
    if route_state_limit < 1:
        raise _search_input_error("routed-tail search", route_state_limit=route_state_limit,
                                  box_size=box_size, max_positions=max_positions,
                                  endpoint=endpoint, anchor_id=anchor.placement_id)
    anchor_center = (float(anchor.bounds.inline + anchor.bounds.inline_size / 2),
                     float(anchor.bounds.block + anchor.bounds.block_size / 2))
    route_states = box_trials = 0
    for box in _candidate_positions(region, box_size, anchor_center, max_positions, search_pass):
        box_trials += 1
        if side_of_as_of is not None:
            x, side = side_of_as_of
            if (side == "start" and box.right > x) or (side == "end" and box.x < x):
                continue
        if obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=obstacle_classes, host_id=host_id):
            continue
        target = (box.x + box.width / 2, box.y + box.height / 2)
        box_best = None
        for egress in connector_egress_candidates(anchor, endpoint, target, siblings, painted=True):
            if route_states >= route_state_limit:
                return RoutedTailSearchResult(None, None, None, None, (), box_trials,
                                              route_states, True)
            for edge_order, edge in enumerate(("top", "right", "bottom", "left")):
                if route_states >= route_state_limit:
                    return RoutedTailSearchResult(None, None, None, None, (), box_trials,
                                                  route_states, True)
                clearance = 2.0
                if edge == "top":
                    tip = (box.x + box.width / 2, box.y - clearance)
                elif edge == "right":
                    tip = (box.right + clearance, box.y + box.height / 2)
                elif edge == "bottom":
                    tip = (box.x + box.width / 2, box.bottom + clearance)
                else:
                    tip = (box.x - clearance, box.y + box.height / 2)
                radius = min(corner_radius, box.width / 2, box.height / 2)
                base_a, base_b = tail_base_points(box, tip, edge=edge, tail_base=tail_base,
                                                  corner_radius=radius)
                candidate_index = SurfaceObstacleIndex()
                candidate_index.extend(obstacles.all())
                candidate_index.add(SurfaceObstacle("candidate:balloon-box", "annotation-box",
                                                    "plot", ObstacleRect(
                                                        box.x, box.y, box.right, box.bottom)))
                source_points = egress.corridor or (egress.exposed_port,)
                endpoint_ports = tuple(dict.fromkeys((
                    *coincident_endpoint_port_ids(obstacles, egress.semantic_port,
                                                 (*egress.host_ids, *egress.corridor_host_ids)),
                    *coincident_endpoint_port_ids(obstacles, egress.exposed_port,
                                                 (*egress.host_ids, *egress.corridor_host_ids)),
                )))
                egress_clear = True
                for start, end in zip(source_points, source_points[1:]):
                    segment = ObstacleSegment(start, end)
                    if obstacles.egress_collisions(segment,
                                                   host_ids=(*egress.host_ids, *egress.corridor_host_ids),
                                                   classes=obstacle_classes,
                                                   port_ids=endpoint_ports):
                        egress_clear = False
                        break
                if not egress_clear:
                    continue
                for start, end in ((base_a, tip), (tip, base_b)):
                    if candidate_index.collisions(ObstacleSegment(start, end),
                                                  classes=obstacle_classes):
                        egress_clear = False
                        break
                if not egress_clear:
                    continue
                left, top, right, bottom = content_bounds
                bounds = (max(left, min(egress.exposed_port[0], tip[0]) - box.width / 2),
                          max(top, min(egress.exposed_port[1], tip[1]) - box.height / 2),
                          min(right, max(egress.exposed_port[0], tip[0]) + box.width / 2),
                          min(bottom, max(egress.exposed_port[1], tip[1]) + box.height / 2))
                if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                    continue
                route, count, exhausted = route_strict_bounded(
                    egress.exposed_port, tip, candidate_index, bounds=bounds,
                    port_ids=endpoint_ports,
                    limit=route_state_limit - route_states, max_bends=max_bends,
                    max_detour_ratio=max_detour_ratio)
                route_states += count
                if exhausted and route is None:
                    return RoutedTailSearchResult(None, None, None, None, (), box_trials,
                                                  route_states, True)
                if route is None:
                    continue
                points = (*source_points, *route.points[1:])
                if not relation_route_quality(points, max_bends=max_bends,
                                              max_detour_ratio=max_detour_ratio):
                    continue
                if side_of_as_of is not None:
                    x, side = side_of_as_of
                    all_x = tuple(point[0] for point in (*points, base_a, base_b))
                    if ((side == "start" and max(all_x) > x)
                            or (side == "end" and min(all_x) < x)):
                        continue
                route_length = fsum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                                    for a, b in zip(route.points, route.points[1:]))
                source_order = {"end": 0, "start": 1, "above": 2, "below": 3}[egress.side]
                rank = (len(route.points) - 2, route_length, source_order, edge_order,
                        egress.exposed_port, tip, route.points)
                if box_best is None or rank < box_best[0]:
                    # A valid bounded-prefix route is a fit, not a failed
                    # search. Exhaustion means no fit before the state cap.
                    box_best = (rank, RoutedTailSearchResult(
                        box, tip, egress, route, points, box_trials, route_states, False))
                if exhausted:
                    return box_best[1]
        if box_best is not None:
            # Egress and target order are ranked only after route shape and length.
            return box_best[1]
    return RoutedTailSearchResult(None, None, None, None, (), box_trials, route_states, False)


def _nearest_free_routed_tail_box_across_rule(
        *, region: LabelRect, anchor: MarkPlacement, endpoint: str,
        siblings: tuple[MarkPlacement, ...], box_size: tuple[float, float],
        max_positions: int, obstacles: SurfaceObstacleIndex,
        obstacle_classes: tuple[str, ...], corner_radius: float,
        tail_base: float, content_bounds: tuple[float, float, float, float],
        host_id: str | None, side_of_as_of: tuple[float, str] | None,
        max_bends: int, max_detour_ratio: float, route_state_limit: int,
        search_pass: str, crossing_rule_id: str) -> RoutedTailSearchResult:
    """Opposite-side fallback; only its completed routed centerline may cross one rule."""
    if (route_state_limit < 1 or side_of_as_of is None
            or crossing_rule_id not in {item.placement_id for item in obstacles.all()}):
        raise _search_input_error("as-of routed-tail search", rule_id=crossing_rule_id,
                                  route_state_limit=route_state_limit,
                                  side_of_as_of=side_of_as_of)
    rule_item = next(item for item in obstacles.all() if item.placement_id == crossing_rule_id)
    if rule_item.obstacle_class != "rule" or not isinstance(rule_item.geometry, ObstacleSegment):
        raise _search_input_error("as-of routed-tail rule", rule_id=crossing_rule_id,
                                  obstacle_class=rule_item.obstacle_class,
                                  geometry=type(rule_item.geometry).__name__)
    rule = rule_item.geometry
    as_of_x, anchor_side = side_of_as_of
    box_side = "end" if anchor_side == "start" else "start"
    if rule.start[0] != as_of_x or rule.end[0] != as_of_x:
        raise _search_input_error("as-of routed-tail identity", rule_id=crossing_rule_id,
                                  expected_x=as_of_x, segment=(rule.start, rule.end))
    anchor_center = (float(anchor.bounds.inline + anchor.bounds.inline_size / 2),
                     float(anchor.bounds.block + anchor.bounds.block_size / 2))
    route_states = box_trials = box_index = 0
    active: list[_OppositeRouteStream] = []
    best: _OppositeRouteTrial | None = None
    for box in _candidate_positions(region, box_size, anchor_center, max_positions, search_pass):
        if route_states >= route_state_limit:
            break
        box_trials += 1
        current_box_index = box_index
        box_index += 1
        if ((box_side == "start" and box.right >= as_of_x)
                or (box_side == "end" and box.x <= as_of_x)):
            continue
        if obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=obstacle_classes, host_id=host_id):
            continue
        target = (box.x + box.width / 2, box.y + box.height / 2)
        streams = []
        for egress in connector_egress_candidates(anchor, endpoint, target, siblings, painted=True):
            source_points = egress.corridor or (egress.exposed_port,)
            source_x = tuple(point[0] for point in source_points)
            if ((anchor_side == "start" and max(source_x) >= as_of_x)
                    or (anchor_side == "end" and min(source_x) <= as_of_x)):
                continue
            endpoint_ports = tuple(dict.fromkeys((
                *coincident_endpoint_port_ids(obstacles, egress.semantic_port,
                                             (*egress.host_ids, *egress.corridor_host_ids)),
                *coincident_endpoint_port_ids(obstacles, egress.exposed_port,
                                             (*egress.host_ids, *egress.corridor_host_ids)),
            )))
            egress_clear = True
            for start, end in zip(source_points, source_points[1:]):
                if obstacles.egress_collisions(
                        ObstacleSegment(start, end),
                        host_ids=(*egress.host_ids, *egress.corridor_host_ids),
                        classes=obstacle_classes, port_ids=endpoint_ports):
                    egress_clear = False
                    break
            if not egress_clear:
                continue
            for edge_order, edge in enumerate(("top", "right", "bottom", "left")):
                clearance = 2.0
                if edge == "top":
                    tip = (box.x + box.width / 2, box.y - clearance)
                elif edge == "right":
                    tip = (box.right + clearance, box.y + box.height / 2)
                elif edge == "bottom":
                    tip = (box.x + box.width / 2, box.bottom + clearance)
                else:
                    tip = (box.x - clearance, box.y + box.height / 2)
                radius = min(corner_radius, box.width / 2, box.height / 2)
                base_a, base_b = tail_base_points(box, tip, edge=edge,
                                                  tail_base=tail_base, corner_radius=radius)
                far_x = ((lambda value: value > as_of_x) if box_side == "end"
                         else (lambda value: value < as_of_x))
                if not all(far_x(point[0]) for point in (tip, base_a, base_b)):
                    continue
                candidate_index = SurfaceObstacleIndex()
                candidate_index.extend(obstacles.all())
                candidate_index.add(SurfaceObstacle(
                    "candidate:balloon-box", "annotation-box", "plot",
                    ObstacleRect(box.x, box.y, box.right, box.bottom)))
                if any(candidate_index.collisions(ObstacleSegment(start, end),
                                                  classes=obstacle_classes)
                       for start, end in ((base_a, tip), (tip, base_b))):
                    continue
                left, top, right, bottom = content_bounds
                bounds = (max(left, min(egress.exposed_port[0], tip[0]) - box.width / 2),
                          max(top, min(egress.exposed_port[1], tip[1]) - box.height / 2),
                          min(right, max(egress.exposed_port[0], tip[0]) + box.width / 2),
                          min(bottom, max(egress.exposed_port[1], tip[1]) + box.height / 2))
                if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                    continue
                route_iter = strict_route_candidates(
                    egress.exposed_port, tip, candidate_index, bounds=bounds,
                    max_bends=max_bends, max_detour_ratio=max_detour_ratio,
                    candidate_limit=route_state_limit, interleave_axial=True)
                streams.append(_OppositeRouteStream(
                    current_box_index, box, egress, source_points, endpoint_ports,
                    edge_order, tip, candidate_index, route_iter))
        active.extend(streams)
        # One route candidate per active egress/edge stream per coarse-box
        # sweep. This dovetails route work across boxes while retaining the
        # single aggregate state cap and original box/route ranking.
        next_active = []
        for stream in active:
            if route_states >= route_state_limit:
                next_active.append(stream)
                continue
            next_stream, trial, consumed = _advance_opposite_route_stream(
                stream, rule=rule, crossing_rule_id=crossing_rule_id,
                max_bends=max_bends, max_detour_ratio=max_detour_ratio)
            route_states += int(consumed)
            if next_stream is not None:
                next_active.append(next_stream)
            if trial is not None and (best is None or trial.rank < best.rank):
                best = trial
        active = next_active
    # Once the coarse-position budget is fully admitted, continue dovetailing
    # the admitted route streams. Otherwise a low maxPositions value could
    # truncate valid route prefixes despite unused aggregate route budget.
    while active and route_states < route_state_limit:
        next_active = []
        for stream in active:
            if route_states >= route_state_limit:
                next_active.append(stream)
                continue
            next_stream, trial, consumed = _advance_opposite_route_stream(
                stream, rule=rule, crossing_rule_id=crossing_rule_id,
                max_bends=max_bends, max_detour_ratio=max_detour_ratio)
            route_states += int(consumed)
            if next_stream is not None:
                next_active.append(next_stream)
            if trial is not None and (best is None or trial.rank < best.rank):
                best = trial
        active = next_active
    if best is not None:
        return RoutedTailSearchResult(best.box, best.tip, best.egress, best.route,
                                      best.full_points, box_trials, route_states, False)
    return RoutedTailSearchResult(None, None, None, None, (), box_trials, route_states,
                                  bool(active and route_states >= route_state_limit))
