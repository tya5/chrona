"""Relation ink keeps the shared label gap from note indices (#1848).

A completed relation's painted stroke and arrowheads keep the Spec 07 label gap from every placed member name
(handled where names and routes are composed) and from every note index. An index is placed after the routes:
once the unchanged side ladder has placed it, this refinement looks for a candidate on the same declared sides
(sliding along a side by at most its reach) that also keeps the gap from the completed relation ink. An index
the ladder suppressed stays suppressed, except one that only the completed relation ink beside its anchor
blocks: keeping the gap in a route must not cost an index.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from chrona.presentation.layout.labels import LabelPlacement, LabelRect, place_label
from chrona.presentation.layout.member_name_yield import route_candidate_ink
from chrona.presentation.layout.obstacles import (
    ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect,
)
from chrona.presentation.layout.surface_quality import RelationPlacement
from chrona.presentation.model.semantic_registry import semantic_binding


def completed_relation_ink(request: Any, relations: tuple[RelationPlacement, ...]) -> tuple[SurfaceObstacle, ...]:
    """The completed stroke and arrowhead ink of every drawn relation fragment, as routing protects it."""
    ink: list[SurfaceObstacle] = []
    for relation in relations:
        if relation.suppressed or len(relation.points) < 2:
            continue
        width = float(request.theme_tokens.number(
            semantic_binding(relation.semantic_id).theme_role, "strokeWidth"))
        try:
            ink.extend(route_candidate_ink(relation.relation_id, relation.points, relation.marker_start,
                relation.marker_end, width, path_commands=relation.path_commands))
        except ValueError:
            ink.extend(route_candidate_ink(relation.relation_id, relation.points, None, None, width))
    return tuple(ink)


def refine_note_index(placed: LabelPlacement | None, *, anchor: LabelRect, size: tuple[float, float],
                      sides: tuple[str, ...], bounds: LabelRect, obstacles: SurfaceObstacleIndex,
                      relation_ink: tuple[SurfaceObstacle, ...], label_gap: float, anchor_gap: float,
                      reach: float) -> LabelPlacement | None:
    """`placed`, or the first clear candidate that also keeps `label_gap` from completed relation ink.

    `placed` is what the unchanged side ladder chose. When it chose nothing, an index is only recovered if
    the completed relation ink beside its anchor is what blocks the ladder, so that keeping the gap in a
    route never costs an index: the ladder must succeed without that ink, and the index then slides along
    its declared sides by at most `reach`. Any other suppression stays.
    """
    routes = tuple(item for item in obstacles.all() if item.obstacle_class == "dependency-route")
    if placed is None:
        window = ObstacleRect(anchor.x - reach - label_gap - size[0], anchor.y - reach - label_gap - size[1],
                              anchor.right + reach + label_gap + size[0], anchor.bottom + reach + label_gap + size[1])
        if not routes or not any(obstacles_intersect(item.geometry, window) for item in routes):
            return None
        # The caller's verdict stands unless the unchanged ladder, asked again, really finds nothing, and
        # then only if it would succeed without the completed relation ink.
        if place_label(anchor, size, sides, bounds=bounds, obstacles=obstacles, gap=anchor_gap, required=False,
                       overflow="suppress") is not None:
            return None
        free = obstacles.copy(excluded_ids=[item.placement_id for item in routes])
        if place_label(anchor, size, sides, bounds=bounds, obstacles=free, gap=anchor_gap, required=False,
                       overflow="suppress") is None:
            return None
        placed = place_label(anchor, size, sides, bounds=bounds, obstacles=obstacles, gap=anchor_gap, required=False,
                             overflow="suppress", search_side_neighborhood=True, maximum_side_gap=reach)
        if placed is None:
            return None
    spaced = obstacles.copy(clearance_overrides={item.placement_id: label_gap for item in routes})
    spaced.extend(replace(item, clearance=label_gap) for item in relation_ink if not spaced.has(item.placement_id))
    found = place_label(anchor, size, sides, bounds=bounds, obstacles=spaced, gap=anchor_gap, required=False,
                        overflow="suppress", search_side_neighborhood=True, maximum_side_gap=reach)
    return found or placed
