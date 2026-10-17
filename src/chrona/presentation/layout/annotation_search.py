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
from math import fsum, log
from typing import Callable, Iterator

from chrona.presentation.layout.annotations import nearest_box_port
from chrona.presentation.layout.balloon_geometry import nearest_eligible_edge, tail_base_points
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.annotation_topology import (
    AnnotationRouteTrial, strict_route_candidates,
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
class _RouteStream:
    """One admitted box/egress/edge strict-route prefix."""

    box_index: int
    box: LabelRect
    egress: ConnectorEgress
    source_points: tuple[tuple[float, float], ...]
    endpoint_ports: tuple[str, ...]
    edge_order: int
    tip: tuple[float, float]
    tail_base_points: tuple[tuple[float, float], tuple[float, float]]
    candidate_index: SurfaceObstacleIndex
    route_iter: Iterator[tuple[tuple[float, float], ...]]


@dataclass(frozen=True)
class _RouteTrial:
    rank: tuple[object, ...]
    box: LabelRect
    tip: tuple[float, float]
    egress: ConnectorEgress
    route: AnnotationRouteTrial
    full_points: tuple[tuple[float, float], ...]


def _advance_route_stream(
        stream: _RouteStream, *, max_bends: int, max_detour_ratio: float,
        rule: ObstacleSegment | None = None,
        crossing_rule_id: str | None = None,
        side_of_as_of: tuple[float, str] | None = None,
        ) -> tuple[_RouteStream | None, _RouteTrial | None, bool]:
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
            or (rule is not None and not _route_crosses_rule_once(points, rule))):
        return stream, None, True
    full_points = (*stream.source_points, *points[1:])
    if not relation_route_quality(full_points, max_bends=max_bends,
                                  max_detour_ratio=max_detour_ratio):
        return stream, None, True
    if side_of_as_of is not None:
        as_of_x, side = side_of_as_of
        all_x = tuple(point[0] for point in full_points)
        all_x += tuple(point[0] for point in stream.tail_base_points)
        if ((side == "start" and max(all_x) > as_of_x)
                or (side == "end" and min(all_x) < as_of_x)):
            return stream, None, True
    route = AnnotationRouteTrial(points, (), "strict")
    route_length = fsum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                        for a, b in zip(points, points[1:]))
    source_order = {"end": 0, "start": 1, "above": 2, "below": 3}[stream.egress.side]
    rank = (stream.box_index, len(points) - 2, route_length, source_order,
            stream.edge_order, stream.egress.exposed_port, stream.tip, points)
    return stream, _RouteTrial(rank, stream.box, stream.tip, stream.egress,
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
    if route_state_limit < 1:
        raise _search_input_error("routed-tail search", route_state_limit=route_state_limit,
                                  box_size=box_size, max_positions=max_positions,
                                  endpoint=endpoint, anchor_id=anchor.placement_id)
    rule = None
    opposite = crossing_rule_id is not None
    if opposite:
        if (side_of_as_of is None
                or crossing_rule_id not in {item.placement_id for item in obstacles.all()}):
            raise _search_input_error("as-of routed-tail search", rule_id=crossing_rule_id,
                                      route_state_limit=route_state_limit,
                                      side_of_as_of=side_of_as_of)
        rule_item = next(item for item in obstacles.all()
                         if item.placement_id == crossing_rule_id)
        if (rule_item.obstacle_class != "rule"
                or not isinstance(rule_item.geometry, ObstacleSegment)):
            raise _search_input_error("as-of routed-tail rule", rule_id=crossing_rule_id,
                                      obstacle_class=rule_item.obstacle_class,
                                      geometry=type(rule_item.geometry).__name__)
        rule = rule_item.geometry
        as_of_x, anchor_side = side_of_as_of
        if rule.start[0] != as_of_x or rule.end[0] != as_of_x:
            raise _search_input_error("as-of routed-tail identity", rule_id=crossing_rule_id,
                                      expected_x=as_of_x, segment=(rule.start, rule.end))
        box_side = "end" if anchor_side == "start" else "start"
    else:
        box_side = None
    anchor_center = (float(anchor.bounds.inline + anchor.bounds.inline_size / 2),
                     float(anchor.bounds.block + anchor.bounds.block_size / 2))
    route_states = box_trials = box_index = 0
    active: list[_RouteStream] = []
    best: _RouteTrial | None = None
    for box in _candidate_positions(region, box_size, anchor_center, max_positions, search_pass):
        if route_states >= route_state_limit:
            break
        box_trials += 1
        current_box_index = box_index
        box_index += 1
        if opposite:
            if ((box_side == "start" and box.right >= side_of_as_of[0])
                    or (box_side == "end" and box.x <= side_of_as_of[0])):
                continue
        elif side_of_as_of is not None:
            x, side = side_of_as_of
            if (side == "start" and box.right > x) or (side == "end" and box.x < x):
                continue
        if obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=obstacle_classes, host_id=host_id):
            continue
        target = (box.x + box.width / 2, box.y + box.height / 2)
        new_streams: list[_RouteStream] = []
        for egress in connector_egress_candidates(anchor, endpoint, target, siblings):
            source_points = egress.corridor or (egress.exposed_port,)
            if opposite:
                source_x = tuple(point[0] for point in source_points)
                anchor_side = side_of_as_of[1]
                if ((anchor_side == "start" and max(source_x) >= side_of_as_of[0])
                        or (anchor_side == "end" and min(source_x) <= side_of_as_of[0])):
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
                base_a, base_b = tail_base_points(box, tip, edge=edge, tail_base=tail_base,
                                                  corner_radius=radius)
                candidate_index = SurfaceObstacleIndex()
                candidate_index.extend(obstacles.all())
                candidate_index.add(SurfaceObstacle("candidate:balloon-box", "annotation-box",
                                                    "plot", ObstacleRect(
                                                        box.x, box.y, box.right, box.bottom)))
                if opposite:
                    far_x = ((lambda value: value > side_of_as_of[0])
                             if box_side == "end"
                             else (lambda value: value < side_of_as_of[0]))
                    if not all(far_x(point[0]) for point in (tip, base_a, base_b)):
                        continue
                tail_clear = not any(
                    candidate_index.collisions(ObstacleSegment(start, end),
                                               classes=obstacle_classes)
                    for start, end in ((base_a, tip), (tip, base_b)))
                if not tail_clear:
                    continue
                left, top, right, bottom = content_bounds
                bounds = (max(left, min(egress.exposed_port[0], tip[0]) - box.width / 2),
                          max(top, min(egress.exposed_port[1], tip[1]) - box.height / 2),
                          min(right, max(egress.exposed_port[0], tip[0]) + box.width / 2),
                          min(bottom, max(egress.exposed_port[1], tip[1]) + box.height / 2))
                if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                    continue
                new_streams.append(_RouteStream(
                    current_box_index, box, egress, source_points, endpoint_ports,
                    edge_order, tip, (base_a, base_b), candidate_index,
                    strict_route_candidates(
                        egress.exposed_port, tip, candidate_index, bounds=bounds,
                        max_bends=max_bends, max_detour_ratio=max_detour_ratio,
                        candidate_limit=route_state_limit, interleave_axial=True)))
        active.extend(new_streams)
        next_active = []
        for stream in active:
            if route_states >= route_state_limit:
                next_active.append(stream)
                continue
            next_stream, trial, consumed = _advance_route_stream(
                stream, max_bends=max_bends, max_detour_ratio=max_detour_ratio,
                rule=rule, crossing_rule_id=crossing_rule_id if opposite else None,
                side_of_as_of=side_of_as_of if not opposite else None)
            route_states += int(consumed)
            if next_stream is not None:
                next_active.append(next_stream)
            if trial is not None and (best is None or trial.rank < best.rank):
                best = trial
        active = next_active
    while active and route_states < route_state_limit:
        next_active = []
        for stream in active:
            if route_states >= route_state_limit:
                next_active.append(stream)
                continue
            next_stream, trial, consumed = _advance_route_stream(
                stream, max_bends=max_bends, max_detour_ratio=max_detour_ratio,
                rule=rule, crossing_rule_id=crossing_rule_id if opposite else None,
                side_of_as_of=side_of_as_of if not opposite else None)
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
