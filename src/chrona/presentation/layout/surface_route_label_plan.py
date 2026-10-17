"""Owns provisional member-name reservations, route repair and final labels; reads completed label requests and geometry."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from chrona.presentation.layout.labels import LabelRequest
from chrona.presentation.layout.obstacles import SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, SurfaceMemberLabelsBatch, place_member_labels,
)
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.layout.surface_routes import (
    SurfaceRelationLabelsBatch, SurfaceRoutesBatch, SurfaceRoutesContext,
    compose_surface_routes, place_relation_labels,
)
from chrona.presentation.model.info_diagnostics import RelationResolutionInfo, RelationResolutionStage


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


@dataclass(frozen=True)
class MemberLabelReservation:
    """One already-measured optional candidate, never a committed label batch."""
    text: TextPlacement
    obstacles: tuple[SurfaceObstacle, ...]


@dataclass(frozen=True)
class _Trial:
    plan: RouteLabelPlan
    route_ink: tuple[SurfaceObstacle, ...]


def _empty_members() -> SurfaceMemberLabelsBatch:
    return SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())


def _reservations(context: RouteLabelPlanContext) -> tuple[MemberLabelReservation, ...]:
    requests = tuple(item for item in context.post_route_requests
                     if item.semantic_id == "memberLabel" and not item.is_required_before_routes)
    if not requests:
        return ()
    probe_index = context.clean_obstacles.copy()
    probe = place_member_labels(context.member_labels, requests, probe_index, reserve_only=True)
    added = {item.placement_id: item for item in probe_index.all()
             if not context.clean_obstacles.has(item.placement_id)}
    return tuple(MemberLabelReservation(replace(text, required=False), tuple(
        added[identifier] for identifier in (text.placement_id, f"label-footprint:{text.placement_id}")
        if identifier in added)) for text in probe.text if text.overflow == "fit")


def _relation_status(routes: SurfaceRoutesBatch) -> dict[str, int]:
    """Compare stable logical identities, including the two fragments of a stub."""
    status = {}
    for item in routes.relations:
        endpoint = getattr(item, "fragment_endpoint", None)
        identifier = item.relation_id.removesuffix(f":stub-{endpoint}") if endpoint else item.relation_id
        status[identifier] = max(status.get(identifier, 0), 6 if item.suppressed else 0)
    for item in routes.visible_route_fallbacks:
        status[item.relation_id] = max(status.get(item.relation_id, 0), 4)
    stages = {RelationResolutionStage.LABEL_VISUALS: 1, RelationResolutionStage.TEXT: 2,
              RelationResolutionStage.MARKS: 3, RelationResolutionStage.OVERLAP: 4,
              RelationResolutionStage.STUB: 5}
    for item in routes.resolution_info:
        if isinstance(item, RelationResolutionInfo):
            status[item.relation_id] = max(status.get(item.relation_id, 0), stages.get(item.stage, 0))
    return status


def _run_trial(context: RouteLabelPlanContext, reservations: tuple[MemberLabelReservation, ...],
               requests: tuple[LabelRequest, ...], *, progress_pass: str) -> _Trial:
    index = context.clean_obstacles.copy()
    provisional_ids = {item.placement_id for reserve in reservations for item in reserve.obstacles}
    index.extend(item for reserve in reservations for item in reserve.obstacles)
    route_context = replace(context.routes_for(index, (*context.base_text, *(item.text for item in reservations))),
                            progress_pass=progress_pass)
    routes = compose_surface_routes(route_context)
    route_ink = index.select(classes=("dependency-route",))
    # Revalidate through the same placement owner against actual route ink;
    # no probe facts or ghost boxes reach Scene or later obstacle phases.
    final_index = SurfaceObstacleIndex()
    final_index.extend(item for item in index.all() if item.placement_id not in provisional_ids)
    members = (place_member_labels(context.member_labels, requests, final_index)
               if requests else _empty_members())
    relation_labels = place_relation_labels(replace(route_context, obstacles=final_index,
        text=(*context.base_text, *members.text)), routes)
    return _Trial(RouteLabelPlan(routes, members, relation_labels, final_index), route_ink)


def _trial(context: RouteLabelPlanContext, reservations: tuple[MemberLabelReservation, ...],
           requests: tuple[LabelRequest, ...], *, progress_pass: str = "route-label-reference") -> RouteLabelPlan:
    """Expose a completed unreserved reference for characterization tests."""
    return _run_trial(context, reservations, requests, progress_pass=progress_pass).plan


def _preserves(reference: RouteLabelPlan, candidate: RouteLabelPlan) -> bool:
    baseline, selected = _relation_status(reference.routes), _relation_status(candidate.routes)
    if baseline.keys() != selected.keys() or any(selected[key] > baseline[key] for key in baseline):
        return False
    visible = lambda batch: {item.placement_id for item in batch.text if item.overflow != "suppressed"}
    return visible(reference.relation_labels) <= visible(candidate.relation_labels)


def _crossed_reservations(ink: tuple[SurfaceObstacle, ...],
                          reservations: tuple[MemberLabelReservation, ...]) -> frozenset[str]:
    return frozenset(reserve.text.placement_id for reserve in reservations
        if any(obstacles_intersect(paint.geometry, footprint.geometry, paint.clearance + footprint.clearance)
               for paint in ink for footprint in reserve.obstacles))


def _relation_ink(ink: tuple[SurfaceObstacle, ...], relation_ids: set[str]) -> tuple[SurfaceObstacle, ...]:
    return tuple(item for item in ink
                 if any(item.placement_id.startswith(identifier + ":") for identifier in relation_ids))


def _crossing_relations(trial: _Trial,
                        reservations: tuple[MemberLabelReservation, ...]) -> set[str]:
    return {identifier for identifier in _relation_status(trial.plan.routes)
            if _crossed_reservations(_relation_ink(trial.route_ink, {identifier}), reservations)}


def compose_routes_and_member_labels(context: RouteLabelPlanContext) -> RouteLabelPlan:
    """Reserve once, with at most one reference and one selective-release retry."""
    reservations = _reservations(context)
    reserved = _run_trial(context, reservations, context.post_route_requests,
                          progress_pass="route-label-reserved")
    trials = [reserved]

    def finish(chosen: _Trial) -> RouteLabelPlan:
        return replace(chosen.plan, routes=replace(chosen.plan.routes, routing_info=tuple(
            fact for trial in trials for fact in trial.plan.routes.routing_info)))

    if not reservations:
        return finish(reserved)
    if (not any(_relation_status(reserved.plan.routes).values())
            and not _crossed_reservations(reserved.route_ink, reservations)):
        return finish(reserved)
    reference = _run_trial(context, (), context.post_route_requests, progress_pass="route-label-reference")
    trials.append(reference)
    baseline, selected = _relation_status(reference.plan.routes), _relation_status(reserved.plan.routes)
    affected = {key for key in baseline if selected.get(key, 6) > baseline[key]}
    crossed = _crossed_reservations(reserved.route_ink, reservations)
    if crossed:
        affected.update(_crossing_relations(reserved, reservations))
    reference_ink = _relation_ink(reference.route_ink, affected)
    release = _crossed_reservations(reference_ink, reservations)
    if not release:
        return finish(reserved if _preserves(reference.plan, reserved.plan) and not crossed else reference)
    kept = tuple(item for item in reservations if item.text.placement_id not in release)
    if not kept:
        return finish(reference)  # already the exact released trial; no replay
    retry = _run_trial(context, kept, context.post_route_requests, progress_pass="route-label-release")
    trials.append(retry)
    return finish(retry if _preserves(reference.plan, retry.plan) else reference)
