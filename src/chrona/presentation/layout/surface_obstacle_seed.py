"""Owns initial surface obstacle registration; reads completed marks, required text and rule shapes."""
from __future__ import annotations

from collections.abc import Sequence
from itertools import chain

from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_quality import MarkPlacement, ShapePlacement, TextPlacement
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView


def seed_surface_obstacles(*, marks: Sequence[MarkPlacement], text: Sequence[TextPlacement],
                           shapes: Sequence[ShapePlacement], theme_tokens: ThemeTokenView) -> SurfaceObstacleIndex:
    """Start the one monotone inventory; background bands deliberately stay out."""
    inventory = SurfaceObstacleIndex()
    for placed, obstacle_class, region in chain(
            ((mark, "mark", "timeline") for mark in marks),
            ((item, "text", item.collision_domain.slot)
             for item in text if item.required and item.overflow != "suppressed")):
        inline, block, width, height = bounds_from_rect(placed.bounds)
        if width > 0 and height > 0:
            inventory.add(SurfaceObstacle(placed.placement_id, obstacle_class, region,
                                          ObstacleRect(inline, block, inline + width, block + height)))
    for shape in shapes:
        if shape.placement_id == "as-of" and len(shape.points) >= 2:
            inventory.add(SurfaceObstacle(shape.placement_id, "rule", "timeline",
                ObstacleSegment(shape.points[0], shape.points[1],
                    float(theme_tokens.number(semantic_binding("asOf").scene_role, "strokeWidth")))))
        elif shape.semantic_id == "deadlineMark":
            width = float(theme_tokens.number(semantic_binding("deadlineMark").scene_role, "strokeWidth"))
            for index, (source, target) in enumerate(zip(shape.points, shape.points[1:])):
                if source != target:
                    inventory.add(SurfaceObstacle(f"{shape.placement_id}:segment:{index}", "rule", "timeline",
                                                  ObstacleSegment(source, target, width)))
    return inventory
