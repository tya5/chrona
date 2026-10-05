"""Coordinates one bounded route/name recovery; reads completed marks, label requests and a clean obstacle index."""
from __future__ import annotations

from dataclasses import dataclass, fields
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


def _empty_members() -> SurfaceMemberLabelsBatch:
    return SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())


def _combine_members(*batches: SurfaceMemberLabelsBatch) -> SurfaceMemberLabelsBatch:
    values = {}
    for item in fields(SurfaceMemberLabelsBatch):
        if item.name == "handled_visual_sources":
            values[item.name] = frozenset().union(*(batch.handled_visual_sources for batch in batches))
        else:
            values[item.name] = tuple(value for batch in batches for value in getattr(batch, item.name))
    return SurfaceMemberLabelsBatch(**values)


def _lost_requests(requests: tuple[LabelRequest, ...], batch: SurfaceMemberLabelsBatch) -> tuple[LabelRequest, ...]:
    lost = {item.placement_id for item in batch.text
            if item.semantic_id == "memberLabel" and item.overflow == "suppressed"}
    return tuple(request for request in requests
                 if request.semantic_id == "memberLabel" and request.placement_id in lost)


def _relation_status(routes: SurfaceRoutesBatch) -> dict[str, int]:
    status = {item.relation_id: 0 for item in routes.relations}
    for item in routes.visible_route_fallbacks:
        status[item.relation_id] = max(status.get(item.relation_id, 0), 1)
    for item in routes.relations:
        if item.suppressed:
            status[item.relation_id] = 2
    return status


def _trial(context: RouteLabelPlanContext, pre_requests: tuple[LabelRequest, ...],
           post_requests: tuple[LabelRequest, ...]) -> RouteLabelPlan:
    obstacles = context.clean_obstacles.copy()
    pre = (place_member_labels(context.member_labels, pre_requests, obstacles)
           if pre_requests else _empty_members())
    route_context = context.routes_for(obstacles, (*context.base_text, *pre.text))
    routes = compose_surface_routes(route_context)
    post = (place_member_labels(context.member_labels, post_requests, obstacles)
            if post_requests else _empty_members())
    relation_labels = place_relation_labels(route_context, routes)
    return RouteLabelPlan(routes, _combine_members(pre, post), relation_labels, obstacles)


def _relation_labels_preserved(baseline: SurfaceRelationLabelsBatch,
                               candidate: SurfaceRelationLabelsBatch) -> bool:
    baseline_ids = {item.placement_id for item in baseline.text if item.overflow != "suppressed"}
    candidate_ids = {item.placement_id for item in candidate.text if item.overflow != "suppressed"}
    return baseline_ids <= candidate_ids


def compose_routes_and_member_labels(context: RouteLabelPlanContext) -> RouteLabelPlan:
    """Complete routes and labels; retry once only to recover post-route member names."""
    baseline = _trial(context, (), context.post_route_requests)
    lost = _lost_requests(context.post_route_requests, baseline.members)
    if not lost:
        return baseline

    lost_ids = {item.placement_id for item in lost}
    remaining = tuple(item for item in context.post_route_requests if item.placement_id not in lost_ids)
    retry = _trial(context, lost, remaining)
    retry_lost_ids = {item.placement_id for item in _lost_requests(context.post_route_requests, retry.members)}
    if not retry_lost_ids < lost_ids:
        return baseline
    baseline_relations = _relation_status(baseline.routes)
    retry_relations = _relation_status(retry.routes)
    if baseline_relations.keys() != retry_relations.keys():
        return baseline
    if any(retry_relations[key] > baseline_relations[key] for key in baseline_relations):
        return baseline
    if not _relation_labels_preserved(baseline.relation_labels, retry.relation_labels):
        return baseline
    return retry
