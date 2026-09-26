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

from chrona.presentation.layout.annotations import nearest_box_port
from chrona.presentation.layout.balloon_geometry import nearest_eligible_edge, tail_base_points
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacleIndex


@dataclass(frozen=True)
class NearestFreeTrial:
    """One examined lattice position, whether or not it was accepted."""

    box: LabelRect
    accepted: bool


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
        raise ValueError("E_LAYOUT_ANNOTATION_SEARCH_INPUT")
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
