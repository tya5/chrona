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
from math import fsum

from chrona.presentation.layout.annotations import nearest_box_port
from chrona.presentation.layout.balloon_geometry import nearest_eligible_edge, tail_base_points
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.annotation_topology import (
    AnnotationRouteTrial, route_strict_bounded,
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
                     side_of_as_of: tuple[float, str] | None = None) -> tuple[LabelRect | None, int]:
    """Return the first collision-free box on the lattice, and the trial count.

    ``side_of_as_of`` is ``(as_of_x, "start"|"end")``: when given, an
    accepted box must stay entirely on the anchor's declared side of the
    as-of rule's inline coordinate.
    """
    trials = 0
    for box in lattice_positions(region, box_size, anchor_center, max_positions):
        trials += 1
        if side_of_as_of is not None:
            as_of_x, side = side_of_as_of
            if (side == "start" and box.right > as_of_x) or (side == "end" and box.x < as_of_x):
                continue
        collisions = obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                          classes=obstacle_classes, port_ids=exempt_ids, host_id=host_id)
        if not collisions:
            return box, trials
    return None, trials


def nearest_free_tail_box(*, region: LabelRect, anchor: LabelRect,
                          box_size: tuple[float, float], max_positions: int,
                          obstacles: SurfaceObstacleIndex, obstacle_classes: tuple[str, ...],
                          corner_radius: float, tail_base: float,
                          host_id: str | None = None,
                          side_of_as_of: tuple[float, str] | None = None
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
    for box in lattice_positions(region, box_size, anchor_center, max_positions):
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
                                 route_state_limit: int = 1024) -> RoutedTailSearchResult:
    """Find a free box with a strict routed connector ending at an exterior tip.

    Candidate-box trials and connector states have independent finite limits.
    The candidate box is inserted into a private obstacle index for route checks;
    accepted geometry is never written to the caller's monotone index here.
    """
    if route_state_limit < 1:
        raise _search_input_error("routed-tail search", route_state_limit=route_state_limit,
                                  box_size=box_size, max_positions=max_positions,
                                  endpoint=endpoint, anchor_id=anchor.placement_id)
    anchor_center = (float(anchor.bounds.inline + anchor.bounds.inline_size / 2),
                     float(anchor.bounds.block + anchor.bounds.block_size / 2))
    route_states = box_trials = 0
    for box in lattice_positions(region, box_size, anchor_center, max_positions):
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
        for egress in connector_egress_candidates(anchor, endpoint, target, siblings):
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
                    *coincident_endpoint_port_ids(obstacles, egress.semantic_port, egress.host_ids),
                    *coincident_endpoint_port_ids(obstacles, egress.exposed_port, egress.host_ids),
                )))
                egress_clear = True
                for start, end in zip(source_points, source_points[1:]):
                    segment = ObstacleSegment(start, end)
                    if obstacles.egress_collisions(segment, host_ids=egress.host_ids,
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
