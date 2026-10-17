"""Owns one on-demand repair; reads closed label requests, route and annotation batches."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from chrona.presentation.layout.labels import LabelRequest
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.surface_annotations import SurfaceAnnotationBatch
from chrona.presentation.layout.surface_member_labels import (
    MemberLabelReservation, SurfaceMemberLabelContext, SurfaceMemberLabelsBatch, place_member_labels,
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
class RouteLabelOptions:
    """Private completed alternatives; annotations must complete before selection."""
    first: RouteLabelPlan
    retry: RouteLabelPlan | None = None


def _empty_members() -> SurfaceMemberLabelsBatch:
    return SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())


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
               requests: tuple[LabelRequest, ...], *, progress_pass: str,
               preserve: RouteLabelPlan | None = None) -> RouteLabelPlan:
    index = context.clean_obstacles.copy()
    provisional_ids = {item.placement_id for reserve in reservations for item in reserve.obstacles}
    # A repair must not route through names already completed by the normal
    # pass. Carry their measured footprints, except the names being repaired;
    # this is retention of completed geometry, not another speculative probe.
    repairing = {item.text.placement_id for item in reservations}
    retained_text = tuple(item for item in preserve.members.text
        if item.overflow != "suppressed" and item.placement_id not in repairing) if preserve else ()
    retained_ids = frozenset(identifier for item in retained_text
        for identifier in (item.placement_id, f"label-footprint:{item.placement_id}"))
    if preserve:
        index.extend(item for item in preserve.obstacles.all() if item.placement_id in retained_ids)
    provisional_ids.update(retained_ids)
    index.extend(item for reserve in reservations for item in reserve.obstacles)
    route_context = context.routes_for(index, (*context.base_text, *retained_text,
                                              *(item.text for item in reservations)))
    route_context = replace(route_context, progress_pass=progress_pass,
        required_label_obstacle_ids=route_context.required_label_obstacle_ids | retained_ids,
        label_repair_obstacle_ids=frozenset(item.placement_id
            for reserve in reservations for item in reserve.obstacles))
    routes = compose_surface_routes(route_context)
    # Revalidate through the same placement owner against actual route ink;
    # no probe facts or ghost boxes reach Scene or later obstacle phases.
    final_index = index
    if provisional_ids:
        final_index = SurfaceObstacleIndex()
        final_index.extend(item for item in index.all() if item.placement_id not in provisional_ids)
    members = (place_member_labels(context.member_labels, requests, final_index)
               if requests else _empty_members())
    relation_labels = place_relation_labels(replace(route_context, obstacles=final_index,
        text=(*context.base_text, *members.text)), routes)
    return RouteLabelPlan(routes, members, relation_labels, final_index)


def _trial(context: RouteLabelPlanContext, reservations: tuple[MemberLabelReservation, ...],
           requests: tuple[LabelRequest, ...], *, progress_pass: str = "route-label-reference") -> RouteLabelPlan:
    """Expose a completed unreserved reference for characterization tests."""
    return _run_trial(context, reservations, requests, progress_pass=progress_pass)


def _visible_text_preserved(reference: tuple[TextPlacement, ...], candidate: tuple[TextPlacement, ...]) -> bool:
    """A stable placement identity must retain its actual text, not just its ID."""
    visible = lambda texts: {item.placement_id: item.content for item in texts
                             if item.overflow != "suppressed"}
    before, after = visible(reference), visible(candidate)
    return all(identifier in after and after[identifier] == content
               for identifier, content in before.items())


def _preserves(reference: RouteLabelPlan, candidate: RouteLabelPlan) -> bool:
    baseline, selected = _relation_status(reference.routes), _relation_status(candidate.routes)
    if baseline.keys() != selected.keys() or any(selected[key] > baseline[key] for key in baseline):
        return False
    return (_visible_text_preserved(reference.members.text, candidate.members.text)
            and _visible_text_preserved(reference.relation_labels.text, candidate.relation_labels.text))


def compose_routes_and_member_labels(context: RouteLabelPlanContext) -> RouteLabelOptions:
    """Run normally first; only recorded route-blocked candidates trigger one retry."""
    first = _run_trial(context, (), context.post_route_requests,
                       progress_pass="route-label-baseline")
    reserves = first.members.route_blocked_candidates
    if not reserves:
        return RouteLabelOptions(first)
    retry = _run_trial(context, reserves, context.post_route_requests,
                       progress_pass="route-label-recovery", preserve=first)
    return RouteLabelOptions(first, retry)


def _annotations_preserved(first: SurfaceAnnotationBatch, retry: SurfaceAnnotationBatch) -> bool:
    if not _visible_text_preserved(first.text, retry.text):
        return False
    for attribute, identity in (("shapes", "placement_id"), ("icons", "placement_id"),
                                ("relations", "relation_id")):
        ids = lambda batch: {getattr(item, identity) for item in getattr(batch, attribute)
                             if not getattr(item, "suppressed", False)}
        if not ids(first) <= ids(retry):
            return False
    selected = {item.decision_id: item for item in retry.decisions}
    for previous in first.decisions:
        if previous.outcome != "placed":
            continue
        current = selected.get(previous.decision_id)
        if current is None or current.outcome != "placed":
            return False
        connected = {"direct-tail", "routed-tail", "strict", "bridged-orthogonal"}
        if previous.selected_topology in connected and current.selected_topology not in connected:
            return False
        ladder = previous.requested_ladder
        if previous.selected_rung in ladder:
            if (current.requested_ladder != ladder or current.selected_rung not in ladder
                    or ladder.index(current.selected_rung) > ladder.index(previous.selected_rung)):
                return False
    return True


def select_completed_route_label_plan(options: RouteLabelOptions,
                                      first_annotations: SurfaceAnnotationBatch,
                                      retry_annotations: SurfaceAnnotationBatch | None = None,
                                      ) -> tuple[RouteLabelPlan, SurfaceAnnotationBatch]:
    """Choose completed batches only; never replay or leak discarded geometry."""
    if options.retry is None:
        return options.first, first_annotations
    if retry_annotations is None:
        raise ValueError("retry annotations must be completed before route-label selection")
    accepted = (_preserves(options.first, options.retry)
                and _annotations_preserved(first_annotations, retry_annotations))
    chosen, annotations = ((options.retry, retry_annotations) if accepted
                           else (options.first, first_annotations))
    facts = (*options.first.routes.routing_info, *options.retry.routes.routing_info)
    return replace(chosen, routes=replace(chosen.routes, routing_info=facts)), annotations
