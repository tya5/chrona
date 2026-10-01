"""Owns the lane route-protection plan (corridors member names must keep clear); reads the pre-name obstacle index and the label and route phase inputs, mutates nothing shared."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from chrona.presentation.layout.labels import LabelRequest
from chrona.presentation.layout.obstacles import (
    ROUTE_RESERVE_CLASS, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.routing import ROUTE_GRID_OFFSET
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, SurfaceMemberLabelsBatch, place_member_labels,
)
from chrona.presentation.layout.surface_quality import RelationPlacement, TextPlacement
from chrona.presentation.layout.surface_routes import (
    SurfaceRoutesBatch, SurfaceRoutesContext, compose_surface_routes,
)
from chrona.presentation.model.semantic_registry import semantic_binding


@dataclass(frozen=True)
class LaneRoutePlanContext:
    labels: SurfaceMemberLabelContext
    requests: tuple[LabelRequest, ...]
    base_text: tuple[TextPlacement, ...]
    obstacles: SurfaceObstacleIndex
    routes_for: Callable[[SurfaceObstacleIndex, tuple[TextPlacement, ...]], SurfaceRoutesContext]


@dataclass(frozen=True)
class LaneRoutePlan:
    """Corridors to register before the member names are placed; empty keeps today's order exactly."""

    reservations: tuple[SurfaceObstacle, ...] = ()
    protected: tuple[str, ...] = ()


def _degraded(routes: SurfaceRoutesBatch) -> frozenset[str]:
    """Relations that are suppressed or completed only as the visible direct fallback."""
    return frozenset(item.relation_id for item in routes.relations if item.suppressed) | frozenset(
        item.relation_id for item in routes.visible_route_fallbacks)


def _rehearse(context: LaneRoutePlanContext,
              reservations: tuple[SurfaceObstacle, ...]) -> tuple[SurfaceMemberLabelsBatch, SurfaceRoutesBatch]:
    """Run the names and then the routes on a private copy of the index, as the real phases will."""
    index = context.obstacles.copy()
    index.extend(reservations)
    names = place_member_labels(context.labels, context.requests, index)
    routes = compose_surface_routes(context.routes_for(index, (*context.base_text, *names.text)))
    return names, routes


def _suppressed_names(names: SurfaceMemberLabelsBatch) -> frozenset[str]:
    return frozenset(item.placement_id for item in names.text if item.overflow == "suppressed")


def _corridor(relation: RelationPlacement, context: LaneRoutePlanContext) -> tuple[SurfaceObstacle, ...]:
    request = context.labels.request
    stroke = float(request.theme_tokens.number(semantic_binding(relation.semantic_id).theme_role, "strokeWidth"))
    width = stroke + 2 * ROUTE_GRID_OFFSET
    return tuple(SurfaceObstacle(f"{ROUTE_RESERVE_CLASS}:{relation.relation_id}:segment:{index}",
                                 ROUTE_RESERVE_CLASS, "timeline", ObstacleSegment(source, target, width))
                 for index, (source, target) in enumerate(zip(relation.points, relation.points[1:]))
                 if source != target)


def plan_lane_route_reservations(context: LaneRoutePlanContext) -> LaneRoutePlan:
    """Reserve the corridor of each lane route that member names alone would lose or degrade.

    The names are placed before the routes (Spec 50 section 3.3), so a name can leave a dependency no
    corridor. The plan rehearses today's order; when a relation is lost or degraded and a route for it
    exists without any name, that route's corridor is reserved so the names yield to it. The plan is
    accepted only if the rehearsal with the reservations loses a strict subset of those relations and
    suppresses no name that is shown without them; otherwise the plan is empty and nothing changes.
    """
    request = context.labels.request
    if (context.labels.projection.lane_membership is None or not request.surface_content.relations
            or not any(item.semantic_id == "memberLabel" for item in context.requests)):
        return LaneRoutePlan()
    names, routes = _rehearse(context, ())
    lost = _degraded(routes)
    if not lost:
        return LaneRoutePlan()
    reference = compose_surface_routes(context.routes_for(context.obstacles.copy(), context.base_text))
    unplaced = _degraded(reference)
    rescued = tuple(item for item in reference.relations if item.relation_id in lost
                    and item.relation_id not in unplaced)
    if not rescued:
        return LaneRoutePlan()
    reservations = tuple(obstacle for item in rescued for obstacle in _corridor(item, context))
    rehearsed_names, rehearsed_routes = _rehearse(context, reservations)
    if _degraded(rehearsed_routes) < lost and _suppressed_names(rehearsed_names) <= _suppressed_names(names):
        return LaneRoutePlan(reservations, tuple(sorted(item.relation_id for item in rescued)))
    return LaneRoutePlan()
