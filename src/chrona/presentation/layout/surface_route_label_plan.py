"""Coordinates one route composition and relation-label completion; reads completed member content and the single route plan."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from chrona.presentation.layout.labels import LabelRequest
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import (
    MemberLabelAllocationSession, SurfaceMemberLabelContext, SurfaceMemberLabelsBatch,
    place_member_labels,
)
from chrona.presentation.layout.member_name_yield import MemberNameYieldRequest, MemberNameYieldResult
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
    pre_route_members: MemberLabelAllocationSession | None = None


@dataclass(frozen=True)
class RouteLabelPlan:
    routes: SurfaceRoutesBatch
    pre_route_members: SurfaceMemberLabelsBatch
    members: SurfaceMemberLabelsBatch
    relation_labels: SurfaceRelationLabelsBatch
    obstacles: SurfaceObstacleIndex


def compose_routes_and_member_labels(context: RouteLabelPlanContext) -> RouteLabelPlan:
    """Route once; finalize names after the required-endpoint exception closes."""
    index = context.clean_obstacles.copy()
    if context.pre_route_members is not None:
        context.pre_route_members.adopt_obstacles(index)
    projected_text = ((*context.base_text, *context.pre_route_members.text)
                      if context.pre_route_members is not None else context.base_text)
    route_context = context.routes_for(index, projected_text)
    if context.pre_route_members is not None:
        def yield_member_names(request: MemberNameYieldRequest,
                               current: SurfaceObstacleIndex) -> MemberNameYieldResult | None:
            result = context.pre_route_members.yield_for_endpoint(request, current)
            if result is None:
                return None
            return replace(result, text=(*context.base_text, *result.text))

        route_context = replace(route_context,
            member_name_yield=yield_member_names,
            required_label_obstacle_ids=context.pre_route_members.required_obstacle_ids)
    route_context = replace(route_context, progress_pass="route-content-baseline")
    routes = compose_surface_routes(route_context)
    if context.pre_route_members is not None:
        index = context.pre_route_members.obstacles
        route_context = replace(route_context, obstacles=index,
            text=(*context.base_text, *context.pre_route_members.text))
        pre_route_members = context.pre_route_members.finish()
    else:
        pre_route_members = SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())
    terminal_labels = place_relation_labels(route_context, routes, terminal=True)
    members = place_member_labels(context.member_labels, context.post_route_requests, index)
    ordinary_labels = place_relation_labels(replace(route_context,
        text=(*route_context.text, *terminal_labels.text, *members.text)), routes, terminal=False)
    relation_labels = SurfaceRelationLabelsBatch(
        (*terminal_labels.text, *ordinary_labels.text),
        (*terminal_labels.diagnostics, *ordinary_labels.diagnostics),
        (*terminal_labels.visible_label_overflows, *ordinary_labels.visible_label_overflows))
    return RouteLabelPlan(routes, pre_route_members, members, relation_labels, index)
