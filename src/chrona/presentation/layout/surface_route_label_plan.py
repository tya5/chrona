"""Complete routes and post-route labels against already placed member content."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from chrona.presentation.layout.labels import LabelRequest
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, SurfaceMemberLabelsBatch, place_member_labels,
)
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.layout.surface_routes import (
    SurfaceRelationLabelsBatch, SurfaceRoutesBatch, SurfaceRoutesContext,
    compose_surface_routes, place_relation_labels,
)


@dataclass(frozen=True)
class RouteLabelPlanContext:
    member_labels: SurfaceMemberLabelContext
    post_route_requests: tuple[LabelRequest, ...]
    base_text: tuple[TextPlacement, ...]
    clean_obstacles: SurfaceObstacleIndex
    routes_for: Callable[[SurfaceObstacleIndex, tuple[TextPlacement, ...]], SurfaceRoutesContext]


@dataclass(frozen=True)
class RouteLabelPlan:
    routes: SurfaceRoutesBatch
    members: SurfaceMemberLabelsBatch
    relation_labels: SurfaceRelationLabelsBatch
    obstacles: SurfaceObstacleIndex


def compose_routes_and_member_labels(context: RouteLabelPlanContext) -> RouteLabelPlan:
    """Route once around actual content; never release names for a second trial."""
    index = context.clean_obstacles.copy()
    route_context = replace(context.routes_for(index, context.base_text),
                            progress_pass="route-content-baseline")
    routes = compose_surface_routes(route_context)
    terminal_labels = place_relation_labels(route_context, routes, terminal=True)
    members = place_member_labels(context.member_labels, context.post_route_requests, index)
    ordinary_labels = place_relation_labels(replace(route_context,
        text=(*context.base_text, *terminal_labels.text, *members.text)), routes, terminal=False)
    relation_labels = SurfaceRelationLabelsBatch(
        (*terminal_labels.text, *ordinary_labels.text),
        (*terminal_labels.diagnostics, *ordinary_labels.diagnostics),
        (*terminal_labels.visible_label_overflows, *ordinary_labels.visible_label_overflows))
    return RouteLabelPlan(routes, members, relation_labels, index)
