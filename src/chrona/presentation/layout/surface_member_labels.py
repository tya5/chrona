"""Owns member/item label requests and placement; reads completed marks, rows and Layout inputs."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
import json
from typing import Any, Callable, Mapping

from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT, BELOW_PLOT_FALLBACK, as_of_label_typography_role
from chrona.presentation.layout.labels import (
    LabelPlacement, LabelRect, LabelRequest, MemberNameAssociation, place_label, start_member_name_search,
)
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.layout.style_text import resolve_label_candidate_styles
from chrona.presentation.model.hierarchy_names import member_name_key
from chrona.presentation.layout.obstacles import (
    ROUTE_RESERVE_CLASS, ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.presentation import TrackPlacement
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.layout.chip_geometry import ChipGeometryError
from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip, complete_label_chip_placement
from chrona.presentation.layout.label_footprint_measurement import measure_label_footprint
from chrona.presentation.layout.surface_member_label_measurement import (
    prepare_member_label_candidate, project_prepared_member_text,
)
from chrona.presentation.layout.surface_member_label_allocation import (
    MemberLabelAllocation, repair_member_names, member_group_obstacles, member_text_candidate,
)
from chrona.presentation.model.semantic_registry import semantic_binding, forecast_delta_semantic_ids
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, GroupPlacement, IconPlacement, LaneLabelSuppression,
    MarkPlacement, PlacementDecision, RowPlacement, ScalePlacement, ShapePlacement,
    SlotPlacement, SurfaceLayoutRequest, TextPlacement,
)
from chrona.presentation.layout.surface_geometry import (
    HOSTED_TEXT_PAINT_ORDER, bounds_from_rect, coordinate_for_date,
)
from chrona.presentation.layout.surface_lanes import lane_owner
from chrona.presentation.layout.key_row_lanes import key_row_label_ladder
from chrona.presentation.layout.lane_mark_facets import span_mark_footprint
from chrona.presentation.layout.surface_mark_visibility import MarkOccurrence, MarkOccurrenceKind
from chrona.presentation.layout.window_label_admission import WindowLabelAbsence
from chrona.presentation.model.projection import (WindowMode, active_placement, finish_delta_text,
    finish_delta_semantic, is_estimated_finish_delta, signed_delta_text)


@dataclass(frozen=True)
class SurfaceMemberLabelContext:
    request: SurfaceLayoutRequest
    projection: Any
    layout_manifest: Any
    by_source: Mapping[str, SlotPlacement]
    text_slot: Callable[[TextPlacement], str]
    review_rows: tuple[Any, ...]
    rows: tuple[RowPlacement, ...]
    tracks: tuple[TrackPlacement, ...]
    groups: tuple[GroupPlacement, ...]
    scale: ScalePlacement
    marks: tuple[MarkPlacement, ...]
    timeline_bounds: tuple[float, float, float, float]
    as_of_label: tuple[float, str] | None
    # #1063: Layout reserved the block under the last row for a `below-plot` chip; `rows_bottom` is where the plot ends.
    as_of_below_plot: bool = False
    rows_bottom: float = 0.0
    as_of_chip_measurement: MeasuredLabelChip | None = None
    intrinsic_endpoint_footprints: tuple[SurfaceObstacle, ...] = ()


@dataclass(frozen=True)
class SurfaceMemberLabelRequests:
    pre_route: tuple[LabelRequest, ...]
    post_route: tuple[LabelRequest, ...]
    window_absences: tuple[WindowLabelAbsence, ...] = ()

    def routing_phases(self, *, first_fit: bool) -> tuple[tuple[LabelRequest, ...], tuple[LabelRequest, ...]]:
        """Complete member names and hard required labels before route search."""
        requests = (*self.pre_route, *self.post_route)
        route_independent = tuple(item for item in requests
            if item.semantic_id != "memberLabel"
            and (item.is_required_before_routes or item.rule_host_obstacle_id is not None))
        member_names = tuple(item for item in requests if item.semantic_id == "memberLabel")
        pre_ids = {id(item) for item in (*route_independent, *member_names)}
        return (*route_independent, *member_names), tuple(item for item in requests if id(item) not in pre_ids)


@dataclass(frozen=True)
class SurfaceMemberLabelsBatch:
    text: tuple[TextPlacement, ...]
    shapes: tuple[ShapePlacement, ...]
    icons: tuple[IconPlacement, ...]
    visible_overflows: tuple[tuple[TextPlacement, LabelRect], ...]
    decisions: tuple[PlacementDecision, ...]
    diagnostics: tuple[str, ...]
    lane_label_suppressions: tuple[LaneLabelSuppression, ...]
    handled_visual_sources: frozenset[str]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()
    visible_overflow_subjects: tuple[tuple[str, tuple[DiagnosticSubject, ...]], ...] = ()


def _lane_label_candidates(side: str, fallback: tuple[str, ...], preferred: str | None) -> tuple[str, ...]:
    ordered = []
    if preferred and preferred != "auto":
        ordered.append(preferred)
    if side != "auto":
        ordered.append(side)
    ordered.extend(fallback if fallback else (("end", "start") if side == "auto" else ()))
    result = []
    for candidate in ordered:
        if candidate == "suppress":
            break
        if candidate not in result:
            result.append(candidate)
    return tuple(result)


def _own_marks(host: MarkPlacement, marks: Mapping[str, MarkPlacement]) -> tuple[MarkPlacement, ...]:
    """The item's own drawn marks, the requested host first: its planned/baseline and actual marks."""
    instance_id = host.placement_id.split(":", 1)[1]
    others = tuple(mark for kind in ("planned", "actual")
                   if (mark := marks.get(f"{kind}:{instance_id}")) is not None
                   and mark.placement_id != host.placement_id)
    return (host, *others)


def _member_full_band(label_request: LabelRequest, layout_manifest: Any) -> bool:
    declared = layout_manifest.member_names.get("search")
    if declared is not None:
        return declared == "full-band"
    return label_request.lane_row_id is not None and layout_manifest.row_distribution == "fill"


def _member_association_outcome(candidate: LabelPlacement | None, association: MemberNameAssociation, *,
                                overflow: str, placement_id: str) -> LabelPlacement | None:
    if candidate is not None and not association.allows(candidate.bounds):
        candidate = None
    if candidate is None and overflow != "suppress":
        raise LayoutError("E_LAYOUT_LABEL_ASSOCIATION_UNPLACEABLE", f"/placement/{placement_id}")
    return candidate


def _validate_member_allocation(allocation: MemberLabelAllocation) -> None:
    """Retain the existing completed-text association/failure authority."""
    geometry = allocation.selected_preparation().geometry
    candidate = allocation.candidate
    association = (geometry.final_association
                   if candidate is not None and candidate.final_rung else geometry.association)
    if allocation.delta_extra and association is not None:
        association = replace(association,
            maximum_distance=association.maximum_distance + allocation.delta_extra)
    if association is not None:
        allocation.candidate = _member_association_outcome(candidate, association,
            overflow=allocation.request.overflow, placement_id=allocation.request.placement_id)


def _finish_delta_anchor_diagnostic(request: LabelRequest, candidate: LabelPlacement) -> str | None:
    """Project the selector's completed obstruction evidence, never re-query geometry."""
    if request.semantic_id not in ("finishDelta", *forecast_delta_semantic_ids()):
        return None
    preferred = next((item for item in candidate.canonical_obstructions if item.side == "end"), None)
    if preferred is None:
        return None
    return "I_LAYOUT_FINISH_DELTA_ANCHOR_FALLBACK:" + json.dumps({
        "placementId": request.placement_id, "preferredSide": "end", "selectedSide": candidate.side,
        "blockerPlacementIds": list(preferred.blocker_placement_ids),
        "outsideBounds": preferred.outside_bounds,
    }, sort_keys=True, separators=(",", ":"))


def build_member_label_requests(context: SurfaceMemberLabelContext) -> SurfaceMemberLabelRequests:
    """Build fixed-lane and optional label requests from closed View/Theme facts."""
    request, projection = context.request, context.projection
    contract = request.presentation_contract
    marks = {item.placement_id: item for item in context.marks}
    tracks = {item.instance_id: item for item in context.tracks}
    groups = {item.group_id: item for item in context.groups}
    timeline = context.by_source["timeline"]
    timeline_bounds = context.timeline_bounds
    row_bands = {row.row_id: LabelRect(float(timeline.bounds.inline), float(row.bounds.block),
                                       float(timeline.bounds.inline_size), float(row.bounds.block_size))
                 for row in context.rows}
    preflight = request.fixed_lane_preflight
    measured = {item.placement_id: item for item in preflight.measured_labels} if preflight else {}
    requests: list[LabelRequest] = []
    window_absences: list[WindowLabelAbsence] = []
    style_index = getattr(request.surface_content, "style_intents", None)
    style_sources = (StyleSourceOccurrences.from_projection(projection, as_of=contract.time.as_of)
                     if style_index is not None and style_index.intents else None)

    def style_key(item, container_id, semantic_id, *, folded=False):
        return (style_sources.label_key(item, container_id, semantic_id, folded=folded)
                if style_sources is not None else None)

    def admission_for(item, container_id, *, folded=False):
        mode = getattr(projection, "window_mode", None)
        if mode is None or not mode.is_bounded:
            return None, None
        kind = (MarkOccurrenceKind.FOLDED if folded else MarkOccurrenceKind.LANE_FINAL
                if projection.lane_membership is not None else MarkOccurrenceKind.ROW
                if projection.rows else MarkOccurrenceKind.AUTO)
        occurrence = MarkOccurrence(kind, container_id if kind != MarkOccurrenceKind.AUTO else item.object_id,
            item.item_id or item.object_id, item.object_id,
            "combined" if kind == MarkOccurrenceKind.AUTO else item.source_kind)
        index = request.mark_visibility_index
        if index is None:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                              detail="stage=label-admission; reason=missing-visibility-index")
        return occurrence, index.lookup_label(occurrence, projection=projection,
                                              as_of=request.surface_content.as_of)

    def normalize(placement_id, item, components, occurrence, admission, *, semantic_id="memberLabel", lane=None):
        if admission is None:
            return tuple(value for _, value in components)
        parts = admission.admit_components(tuple(components), semantic_id=semantic_id)
        if not parts:
            absence = WindowLabelAbsence(placement_id, item.object_id, occurrence, semantic_id,
                admission, tuple(components), lane[0] if lane else None, lane[1] if lane else None,
                visibility_index=request.mark_visibility_index)
            absence.validate_cache(request.mark_visibility_index)
            window_absences.append(absence)
            return ()
        return parts

    def admit_forecast_delta(item, container_id, placement_id, *, folded=False):
        row_admission = getattr(request, "row_admission", None)
        if row_admission is None or not row_admission.omit_outside:
            return True
        if not folded and projection.lane_membership is not None:
            # Forecast IDs belong to the original source row, not its physical
            # lane alias. Keep that identity for a source-temporal absence too.
            occurrence = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, container_id,
                item.item_id or item.object_id, item.object_id, item.source_kind)
            admission = request.mark_visibility_index.lookup_label(
                occurrence, projection=projection, as_of=request.surface_content.as_of)
        else:
            occurrence, admission = admission_for(item, container_id, folded=folded)
        return bool(normalize(placement_id, item,
            (("finishDelta", finish_delta_text(item)),), occurrence, admission,
            semantic_id="finishDelta"))
    if context.as_of_label is not None:
        x, content = context.as_of_label
        requests.append(LabelRequest("as-of-label", "actual-set", content,
            LabelRect(x, timeline_bounds[1], 0.0, 0.0),
            (("plot-below-center", "plot-below-end", "plot-below-start", "plot-bottom-center", "plot-bottom-end",
              "plot-bottom-start", "rule-hosted") if context.as_of_below_plot
             else ("plot-bottom-center", "plot-bottom-end", "plot-bottom-start", "rule-hosted")
             if request.surface_content.as_of_placement in {"foot", BELOW_PLOT}
             else ("plot-top-end", "plot-top-start", "rule-hosted")),
            as_of_label_typography_role(request.theme_tokens), "timeline-as-of",
            CollisionDomain("timeline", "overlay"), "suppress", rule_host_obstacle_id="as-of",
            semantic_id="asOfLabel"))
    attached_labels = dict(request.surface_content.attached_labels)
    if contract.labels.enabled or attached_labels:
        for review_row in context.review_rows:
            for item in review_row.items:
                if (not getattr(item, "temporal_paint", True)
                        or not getattr(item, "member_label_eligible", True)):
                    continue
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                lane = lane_owner(review_row, item) if projection.lane_membership is not None else None
                instance_id = layout_id if projection.rows else item.object_id
                planned = active_placement(item)
                start_at, end_at = planned.get("start", planned.get("at")), planned.get("end", planned.get("at"))
                if not isinstance(start_at, date) and not isinstance(end_at, date):
                    continue
                name_container = review_row.row_id if projection.rows else item.object_id
                attached = attached_labels.get(member_name_key(item, name_container)) if getattr(item, "attached_to", None) else None
                components = []
                if attached is not None:
                    components.append(("attached", attached))
                elif not contract.labels.enabled:
                    continue
                if attached is None and "title" in contract.labels.content:
                    components.append(("title", request.surface_content.member_name(item, review_row.row_id)))
                if (attached is None and getattr(item, "forecast", None) is None
                        and "finishDelta" in contract.labels.content and item.finish_delta is not None):
                    components.append(("finishDelta", signed_delta_text(item.finish_delta, item)))
                if not components:
                    continue
                occurrence, admission = admission_for(item, review_row.row_id)
                parts = normalize(f"member-label:{instance_id}", item, components, occurrence, admission, lane=lane)
                if not parts:
                    continue
                host_kind = "actual" if item.source_kind == "actual" else "planned"
                host_mark_id = f"{host_kind}:{instance_id}"
                mark = marks.get(host_mark_id)
                if item.source_kind == "actual" and mark is None:
                    raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:{instance_id}")
                track = tracks[layout_id]
                anchor = LabelRect(*bounds_from_rect(mark.bounds)) if mark is not None else LabelRect(
                    coordinate_for_date(end_at if isinstance(end_at, date) else start_at, context.scale),
                    track.block, max(1.0, track.block_size), track.block_size)
                lane_mode = projection.lane_membership is not None
                default_ladder = (request.surface_content.label_fallback or
                    (("above", "below", "start", "end") if contract.labels.side == "auto"
                     else (contract.labels.side,)))
                intent = getattr(item, "presentation", None) or {}
                preferred_side = (intent.get("label") or {}).get("side") if isinstance(intent, dict) else None
                wrap = (intent.get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid"
                key_row = getattr(review_row, "key_row", False)
                ladder = (key_row_label_ladder(contract.labels.side) if key_row else
                    _lane_label_candidates(contract.labels.side,
                    request.surface_content.label_fallback, preferred_side) if lane_mode else
                    ((preferred_side,) + tuple(side for side in default_ladder if side != preferred_side)
                     if preferred_side else default_ladder))
                if lane_mode:
                    lane_measure = measured.get(f"member-label:{instance_id}")
                    if lane_measure is None:
                        raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", f"/placement/member-label:{instance_id}")
                    if (lane_measure.content != " ".join(parts) or lane_measure.wrap != wrap
                            or lane_measure.candidates != ladder):
                        raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", f"/placement/member-label:{instance_id}")
                sides = tuple(side for side in ladder if side != "suppress")
                physical_row_id = (mark.physical_host.row_id
                                   if mark is not None and mark.physical_host is not None
                                   else review_row.row_id)
                label_bounds = row_bands.get(physical_row_id)
                if label_bounds is None:
                    raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID",
                                      f"/placement/member-label:{instance_id}")
                requests.append(LabelRequest(f"member-label:{instance_id}", item.object_id, " ".join(parts),
                    anchor, sides, request.surface_content.label_text_role or "text", "plot-label", CollisionDomain("timeline", "overlay"),
                    "visible-overflow" if attached is not None or key_row else "suppress" if lane_mode else
                    "suppress" if "suppress" in ladder else contract.labels.overflow,
                    wrap, bounds=label_bounds,
                    inside_host_obstacle_id=host_mark_id if mark is not None else None,
                    semantic_id="memberLabel", lane_row_id=lane[0] if lane else None,
                    lane_member_id=lane[1] if lane else None,
                    lane_source_kind=item.source_kind if lane else None,
                    required_before_routes=attached is not None or key_row,
                    style_occurrence_key=style_key(item, review_row.row_id, "memberLabel"),
                subjects=(DiagnosticSubject.project_object(item.object_id, item.title),)))
        for folded in getattr(projection, "folded_points", ()):
            if not getattr(folded.item, "member_label_eligible", True):
                continue
            instance_id = f"group-header:{folded.group_id}:{folded.item.item_id or folded.item.object_id}"
            host_kind = "actual" if folded.item.source_kind == "actual" else "planned"
            mark = marks.get(f"{host_kind}:{instance_id}")
            group = groups.get(folded.group_id)
            occurrence, admission = admission_for(folded.item, folded.group_id, folded=True)
            parts = normalize(f"member-label:{instance_id}", folded.item,
                (("title", request.surface_content.member_name(folded.item, folded.group_id)),), occurrence, admission)
            if not parts:
                continue
            if folded.item.source_kind == "actual" and mark is None:
                raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE",
                    f"/placement/member-label:group-header:{folded.group_id}:{folded.item.object_id}")
            if mark is None or group is None or group.header_bounds is None:
                continue
            ladder = (("end", "start") if contract.labels.side == "auto" else (contract.labels.side,))
            requests.append(LabelRequest(f"member-label:{instance_id}", folded.item.object_id,
                request.surface_content.member_name(folded.item, folded.group_id), LabelRect(*bounds_from_rect(mark.bounds)), ladder, "groupHeader",
                "group-header-point", CollisionDomain("group-header", folded.group_id),
                "visible-overflow", bounds=LabelRect(*bounds_from_rect(group.header_bounds)),
                inside_host_obstacle_id=mark.placement_id, semantic_id="memberLabel",
                style_occurrence_key=style_key(folded.item, folded.group_id, "memberLabel", folded=True),
                subjects=(DiagnosticSubject.project_object(folded.item.object_id, folded.item.title),)))
    for review_row in context.review_rows:
        for item in review_row.items:
            if not getattr(item, "temporal_paint", True):
                continue
            if getattr(item, "forecast", None) is not None:
                continue  # A forecast delta is a separate required request below.
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            if not projection.rows and item.source_kind != "combined":
                continue
            if (item.finish_delta is None or "finishDelta" in contract.labels.content
                    or projection.lane_membership is not None):
                continue
            occurrence, admission = admission_for(item, review_row.row_id)
            parts = normalize(f"variance:{instance_id}", item,
                (("finishDelta", signed_delta_text(item.finish_delta, item)),), occurrence, admission,
                semantic_id="finishDelta")
            if not parts:
                continue
            mark = marks.get(f"actual:{instance_id}") or marks.get(f"planned:{instance_id}")
            track = tracks[layout_id]
            actual = item.actual or {}
            anchor_date = actual.get("finish", item.planned.get("end", item.planned.get("at")))
            if isinstance(anchor_date, date):
                anchor = LabelRect(*bounds_from_rect(mark.bounds)) if mark is not None else LabelRect(
                    coordinate_for_date(anchor_date, context.scale), track.block,
                    max(1.0, track.block_size), track.block_size)
                requests.append(LabelRequest(f"variance:{instance_id}", item.object_id,
                    signed_delta_text(item.finish_delta, item), anchor, ("end", "start", "above", "below"),
                    "summary", f"variance:{instance_id}", CollisionDomain("timeline", "overlay"),
                    request.surface_content.label_overflow, semantic_id="finishDelta",
                    # Like a forecast delta, it is placed before routes (#1702): a dependency leaving the finish edge
                    # must not push it to the bar's start, where it reads as a start slip.
                    required_before_routes=True,
                    style_occurrence_key=style_key(item, review_row.row_id, finish_delta_semantic(item)),
                    subjects=(DiagnosticSubject.project_object(item.object_id, item.title),)))
    forecast_requests = []
    if contract.labels.enabled and "finishDelta" in contract.labels.content:
        for folded in projection.folded_points:
            group = groups.get(folded.group_id)
            for item in folded.all_items:
                if item.forecast is None or not item.temporal_paint:
                    continue
                instance_id = f"group-header:{folded.group_id}:{item.item_id or item.object_id}"
                placement_id = f"variance:{instance_id}"
                if not admit_forecast_delta(item, folded.group_id, placement_id, folded=True):
                    continue
                endpoint = active_placement(item).get("at")
                if (projection.window_mode.is_bounded
                        and not projection.window[0] <= endpoint < projection.window[1]):
                    raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{placement_id}")
                mark = marks.get(f"planned:{instance_id}")
                if mark is None or group is None or group.header_bounds is None:
                    raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{placement_id}")
                # Keep the independent required delta outside the folded title's
                # full measured inline reservation, whichever side fits.
                title_footprint = measure_label_footprint(
                    f"member-label:{instance_id}", request.surface_content.member_name(folded.item, folded.group_id),
                    "groupHeader", "memberLabel",
                    request, available_inline=timeline_bounds[2] * 0.4)
                title_reach = title_footprint.size[0] + title_footprint.gap
                anchor = LabelRect(*bounds_from_rect(mark.bounds))
                anchor = LabelRect(anchor.x - title_reach, anchor.y,
                                   anchor.width + 2 * title_reach, anchor.height)
                candidates = tuple(side for side in (request.surface_content.label_fallback or
                    ("end", "start", "above", "below")) if side not in {"suppress", "inside"})
                forecast_requests.append(LabelRequest(
                    placement_id, item.object_id, finish_delta_text(item), anchor, candidates,
                    request.surface_content.label_text_role or "text", "group-header-point",
                    CollisionDomain("group-header", folded.group_id), "diagnose",
                    bounds=LabelRect(*bounds_from_rect(group.header_bounds)),
                    semantic_id=finish_delta_semantic(item), required_before_routes=True,
                    estimated_delta=is_estimated_finish_delta(item),
                    style_occurrence_key=style_key(item, folded.group_id, finish_delta_semantic(item), folded=True),
                    subjects=(DiagnosticSubject.project_object(item.object_id, item.title),)))
        for row in projection.rows:
            for item in row.items:
                if getattr(item, "forecast", None) is None or not getattr(item, "temporal_paint", True):
                    continue
                endpoint = active_placement(item).get("end", active_placement(item).get("at"))
                stable_instance = f"{row.row_id}:{item.item_id or item.object_id}"
                placement_id = f"variance:{stable_instance}"
                if not admit_forecast_delta(item, row.row_id, placement_id):
                    continue
                if projection.window_mode.is_bounded:
                    inside = (projection.window[0] <= endpoint < projection.window[1] if item.source_type == "point"
                              else projection.window[0] < endpoint <= projection.window[1])
                    if not inside:
                        raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{placement_id}")
                physical_row = (projection.lane_membership.assignment_for(
                    row.items[0].item_id or row.items[0].object_id).lane_id
                    if projection.lane_membership is not None else row.row_id)
                mark = marks.get(f"planned:{physical_row}:{item.item_id or item.object_id}")
                if mark is None:
                    raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{placement_id}")
                candidates = tuple(side for side in (request.surface_content.label_fallback or
                    ("end", "start", "above", "below")) if side not in {"suppress", "inside"})
                if getattr(row, "key_row", False):
                    # Like its title, a key-row delta stays inside its own lane band (#1501, #1681).
                    candidates = key_row_label_ladder(contract.labels.side)
                forecast_requests.append(LabelRequest(
                    placement_id, item.object_id, finish_delta_text(item), LabelRect(*bounds_from_rect(mark.bounds)),
                    candidates, request.surface_content.label_text_role or "text", "plot-label", CollisionDomain("timeline", "overlay"),
                    "diagnose", bounds=row_bands.get(physical_row), semantic_id=finish_delta_semantic(item),
                    estimated_delta=is_estimated_finish_delta(item),
                    style_occurrence_key=style_key(item, physical_row, finish_delta_semantic(item)),
                    lane_row_id=physical_row if projection.lane_membership is not None else None,
                    lane_member_id=(row.items[0].item_id or row.items[0].object_id)
                        if projection.lane_membership is not None else None,
                    lane_source_kind=item.source_kind if projection.lane_membership is not None else None,
                    required_before_routes=True,
                    subjects=(DiagnosticSubject.project_object(item.object_id, item.title),)))
    requests = forecast_requests + requests
    pre_route = tuple(item for item in requests if item.rule_host_obstacle_id is not None or
        item.required_before_routes or
        (projection.lane_membership is not None and item.semantic_id == "memberLabel"))
    pre_ids = {id(item) for item in pre_route}
    post_route = tuple(item for item in requests if id(item) not in pre_ids)
    return SurfaceMemberLabelRequests(pre_route, post_route, tuple(window_absences))


def place_member_labels(context: SurfaceMemberLabelContext,
                        requests: tuple[LabelRequest, ...],
                        obstacles: SurfaceObstacleIndex) -> SurfaceMemberLabelsBatch:
    """Place member labels and related label requests against completed obstacles."""
    request, projection = context.request, context.projection
    layout_manifest = context.layout_manifest
    style_index = getattr(request.surface_content, "style_intents", None)
    timeline_rect = LabelRect(*context.timeline_bounds)
    rows = {row.row_id: row for row in context.rows}
    marks = {mark.placement_id: mark for mark in context.marks}
    paint_footprints = {mark.placement_id: span_mark_footprint(mark, request.theme_tokens)
                        for mark in context.marks if mark.mark_shape == "span" and obstacles.has(mark.placement_id)}
    measured_lane = {item.placement_id: item for item in
        (request.fixed_lane_preflight.measured_labels if request.fixed_lane_preflight else ())}
    row_requirements = (dict(request.fixed_lane_preflight.row_requirements)
                        if request.fixed_lane_preflight is not None else {})
    text: list[TextPlacement] = []
    shapes: list[ShapePlacement] = []
    icons: list[IconPlacement] = []
    overflows: list[tuple[TextPlacement, LabelRect]] = []
    decisions: list[PlacementDecision] = []
    diagnostics: list[str] = []
    diagnostic_provenance: list[DiagnosticProvenance] = []
    visible_overflow_subjects: list[tuple[str, tuple[DiagnosticSubject, ...]]] = []
    suppressions: list[LaneLabelSuppression] = []
    handled: set[str] = set()
    allocation_index = obstacles.copy()
    allocations: list[MemberLabelAllocation] = []

    def register_rect(placement_id: str, obstacle_class: str, region_id: str, bounds: Rect) -> None:
        inline, block, inline_size, block_size = bounds_from_rect(bounds)
        if inline_size > 0 and block_size > 0:
            obstacles.add(SurfaceObstacle(placement_id, obstacle_class, region_id,
                ObstacleRect(inline, block, inline + inline_size, block + block_size)))

    for label_request in requests:
        placement_obstacles = allocation_index.copy(geometry_overrides=paint_footprints,
            excluded_ids=("as-of",) if label_request.semantic_id == "memberLabel" else ())
        placement_obstacles.extend(context.intrinsic_endpoint_footprints)
        slot = context.by_source.get(label_request.collision_domain.slot)
        host = marks.get(label_request.inside_host_obstacle_id or "")
        associated_member = (label_request.semantic_id == "memberLabel" and
                             label_request.collision_region == "plot-label" and host is not None)
        own_marks = _own_marks(host, marks) if associated_member else ()
        own_mark_right = (max(bounds_from_rect(mark.bounds)[0] + bounds_from_rect(mark.bounds)[2]
                              for mark in own_marks) if own_marks else None)
        lane_measure = measured_lane.get(label_request.placement_id)

        styles = (resolve_label_candidate_styles(label_request.style_occurrence_key, label_request.candidates,
                    style_index, request.theme_tokens)
                  if label_request.style_occurrence_key is not None and style_index is not None else {})
        prepared = {}
        if any(intent is not None for intent in styles.values()):
            lane_candidates = dict(getattr(lane_measure, "candidate_measurements", ()))
            for side, intent in styles.items():
                prepared[side] = prepare_member_label_candidate(
                    label_request,
                    role=intent.role if intent is not None else label_request.typography_role,
                    measured_lane_label=lane_candidates.get(side, lane_measure),
                    request=request, timeline_rect=timeline_rect, slot=slot, host=host,
                    associated_member=associated_member, own_marks=own_marks,
                    member_names=layout_manifest.member_names,
                    as_of_chip_measurement=context.as_of_chip_measurement)
        selected = (next(iter(prepared.values())) if prepared else
                    prepare_member_label_candidate(
                        label_request, role=label_request.typography_role,
                        measured_lane_label=lane_measure, request=request,
                        timeline_rect=timeline_rect, slot=slot, host=host,
                        associated_member=associated_member, own_marks=own_marks,
                        member_names=layout_manifest.member_names,
                        as_of_chip_measurement=context.as_of_chip_measurement))
        measurement, provisional, geometry, slot_bounds = (
            selected.measurement, selected.provisional, selected.geometry, selected.slot_bounds)
        candidate_geometries = {side: value.geometry for side, value in prepared.items()} if prepared else None
        label_size, label_gap, placement_bounds = geometry.size, geometry.gap, geometry.bounds
        reach, association, final_association = geometry.maximum_end_gap, geometry.association, geometry.final_association
        anchor_with_delta, delta_extra = label_request.anchor, 0.0
        sibling = allocation_index.get(f"variance:{label_request.placement_id.split(':', 1)[-1]}")
        if associated_member and sibling is not None and sibling.obstacle_class == "text":
            # A finish delta is a member of its title's label packing (#1681): when it already holds a side of
            # the title's mark, the title is measured from the delta, so it keeps the label gap from the delta as
            # it does from the mark, and its end reach counts the delta.
            host_left, _, host_width, _ = bounds_from_rect(host.bounds)
            anchor = label_request.anchor
            # A title packs beyond an ordinary finish delta only while it stays within its reach of its nearest own
            # mark (#1702): past that it takes another side of its mark rather than floating away from it.
            forecast_ids = {f"variance:{row.row_id}:{item.item_id or item.object_id}"
                            for row in projection.rows for item in row.items
                            if getattr(item, "forecast", None) is not None}
            ordinary_delta = sibling.placement_id not in forecast_ids
            own_right = max(bounds_from_rect(mark.bounds)[0] + bounds_from_rect(mark.bounds)[2] for mark in own_marks)
            beyond_reach = ordinary_delta and sibling.geometry.right + label_gap - own_right > reach
            if sibling.geometry.left >= host_left + host_width - label_gap and not beyond_reach:
                delta_extra = sibling.geometry.right - (host_left + host_width)
                reach += delta_extra
                if association is not None:
                    association = replace(association, maximum_distance=association.maximum_distance + delta_extra)
                if final_association is not None:
                    final_association = replace(final_association,
                                                maximum_distance=final_association.maximum_distance + delta_extra)
                anchor_with_delta = LabelRect(anchor.x, anchor.y, max(anchor.width, sibling.geometry.right - anchor.x),
                                              anchor.height)
            elif sibling.geometry.right <= host_left + label_gap:
                anchor_with_delta = LabelRect(sibling.geometry.left, anchor.y,
                                              max(anchor.width, anchor.right - sibling.geometry.left), anchor.height)
        if label_request.rule_host_obstacle_id:
            label_classes = ("mark", "text", "label-visual", "rule")
        elif label_request.semantic_id == "memberLabel":
            label_classes = ("mark", "text", "label-visual", "dependency-route", ROUTE_RESERVE_CLASS, "rule")
        else:
            label_classes = ("mark", "text", "label-visual", "dependency-route", ROUTE_RESERVE_CLASS)
        effective_overflow = label_request.overflow
        effective_visible_fallback = label_request.visible_fallback_side
        full_band = _member_full_band(label_request, layout_manifest)
        search = None
        if label_request.semantic_id == "asOfLabel":
            from chrona.presentation.layout.asof_label import find_asof_label_candidate
            candidate = find_asof_label_candidate(timeline_rect, label_size, rule_x=label_request.anchor.x,
                gap=label_gap, rule_host_id="as-of", obstacles=placement_obstacles,
                obstacle_classes=("mark", "text", "label-visual", "rule"),
                placement=(BELOW_PLOT if "plot-below-center" in label_request.candidates
                           else "foot" if "plot-bottom-end" in label_request.candidates else "top"),
                rows_bottom=context.rows_bottom)
            if "plot-below-center" in label_request.candidates and (
                    candidate is None or not candidate.side.startswith("plot-below")):
                diagnostics.append(f"{BELOW_PLOT_FALLBACK}:{label_request.placement_id}")
        elif associated_member:
            search = start_member_name_search(anchor_with_delta, label_size, label_request.candidates,
                bounds=placement_bounds, obstacles=placement_obstacles, gap=label_gap, maximum_end_gap=reach,
                text_inline_inset=geometry.text_inline_inset, inside_host_obstacle_id=label_request.inside_host_obstacle_id,
                classes=label_classes,
                full_band=full_band,
                association=association,
                maximum_stagger=(label_size[1] + label_gap if label_request.lane_row_id is not None else None),
                overflow=effective_overflow, visible_fallback_side=effective_visible_fallback,
                own_mark_right=own_mark_right, final_association=final_association,
                candidate_geometries=candidate_geometries)
            normal = search.next_clear()
            candidate = normal.placement if normal is not None else None
        else:
            candidate = (place_label(label_request.anchor, label_size, label_request.candidates,
                bounds=placement_bounds, obstacles=placement_obstacles, gap=label_gap,
                inside_host_obstacle_id=label_request.inside_host_obstacle_id,
                required=label_request.overflow == "diagnose",
                overflow="suppress" if effective_overflow == "diagnose" else effective_overflow,
                visible_fallback_side=effective_visible_fallback,
                rule_host_obstacle_id=label_request.rule_host_obstacle_id,
                search_side_neighborhood=(label_request.rule_host_obstacle_id is None), classes=label_classes,
                candidate_geometries=candidate_geometries)
                if label_request.candidates else None)
        allocation = MemberLabelAllocation(label_request, selected, prepared, styles,
            host, own_marks, associated_member, delta_extra, candidate, search)
        ordinary_member = associated_member and not label_request.is_required_before_routes
        if allocation.candidate is None and search is not None and not ordinary_member:
            fallback = search.next_fallback()
            allocation.candidate = fallback.placement if fallback is not None else None
        if allocation.candidate is not None or not ordinary_member:
            _validate_member_allocation(allocation)
        allocations.append(allocation)
        allocation_index.extend(member_group_obstacles(allocation))

    repair_index = allocation_index.copy(geometry_overrides=paint_footprints, excluded_ids=("as-of",))
    repair_index.extend(context.intrinsic_endpoint_footprints)
    repair_index = repair_member_names(tuple(allocations), repair_index)
    for allocation in allocations:
        if allocation.candidate is None and allocation.search is not None:
            fallback = allocation.search.next_fallback(repair_index)
            allocation.candidate = fallback.placement if fallback is not None else None
            _validate_member_allocation(allocation)
            repair_index.extend(member_group_obstacles(allocation))

    # Allocation closes before any Text/chip/icon group is emitted. A local
    # exchange can therefore replace a whole group without stale children or
    # registrations leaking into the completed surface inventory.
    for allocation in allocations:
        label_request, candidate = allocation.request, allocation.candidate
        selected, styles = allocation.selected_preparation(), allocation.styles
        host, own_marks = allocation.host, allocation.own_marks
        associated_member = allocation.associated_member
        measurement, provisional, geometry, slot_bounds = (
            selected.measurement, selected.provisional, selected.geometry, selected.slot_bounds)
        final_association = geometry.final_association
        if allocation.delta_extra and final_association is not None:
            final_association = replace(final_association,
                maximum_distance=final_association.maximum_distance + allocation.delta_extra)
        font_size = measurement.treatment.font_size
        label_metrics, visuals = measurement.metrics, measurement.visuals
        handled.update(visual.source_ref for visual, _, _, _ in visuals)
        leading, trailing, text_width = measurement.leading, measurement.trailing, measurement.text_width
        chip_semantic, chip = measurement.chip_semantic, measurement.chip
        chip_measurement = measurement.chip_measurement
        ladder = label_request.candidates + ((label_request.visible_fallback_side,)
            if label_request.visible_fallback_side is not None and
            label_request.visible_fallback_side not in label_request.candidates else ())
        if candidate is None:
            suppression_ladder = ladder + (("suppress",) if label_request.overflow == "suppress" else ())
            if not suppression_ladder:
                raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{label_request.placement_id}")
            text.append(replace(provisional, overflow="suppressed", required=False,
                                fallback_ladder=suppression_ladder, selected_rung="suppress"))
            decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                               suppression_ladder, "suppress", "suppressed"))
            diagnostic = f"W_LAYOUT_LABEL_SUPPRESSED:{label_request.placement_id}"
            diagnostics.append(diagnostic)
            if label_request.subjects:
                diagnostic_provenance.append(DiagnosticProvenance(diagnostic, label_request.subjects))
            if label_request.lane_row_id is not None and label_request.lane_member_id is not None:
                lane_row = rows[label_request.lane_row_id]
                remaining = max(Decimal(0), lane_row.bounds.block_size - Decimal(str(
                    row_requirements[label_request.lane_row_id])))
                short_sources = tuple(item for item in request.capacity_short_sources if item.source_id == "timeline")
                capacity = not associated_member and remaining == 0 and bool(short_sources)
                suppressions.append(LaneLabelSuppression(label_request.placement_id,
                    label_request.lane_row_id, label_request.lane_member_id, lane_row.bounds,
                    Decimal(0) if capacity else remaining, "capacity" if capacity else "obstruction",
                    short_sources if capacity else ()))
            continue
        anchor_diagnostic = _finish_delta_anchor_diagnostic(label_request, candidate)
        if anchor_diagnostic is not None:
            diagnostics.append(anchor_diagnostic)
            if label_request.subjects:
                diagnostic_provenance.append(DiagnosticProvenance(anchor_diagnostic, label_request.subjects))
        chip_box = candidate.bounds
        candidate = member_text_candidate(selected, candidate)
        crosses_slot = (candidate.bounds.x < slot_bounds.x or candidate.bounds.y < slot_bounds.y or
                        candidate.bounds.right > slot_bounds.right or candidate.bounds.bottom > slot_bounds.bottom)
        visible_overflow = candidate.visible_overflow or crosses_slot
        hosting_mark = host
        if final_association is not None and candidate.final_rung:
            # Only a name placed on the final own-mark rung is hosted by the own mark nearest its Text.
            hosting_mark = own_marks[final_association.nearest_mark_index(chip_box)]
        placed_text = replace(project_prepared_member_text(selected,
            inline=candidate.bounds.x + leading,
            baseline_block=candidate.bounds.y + float(font_size),
            overflow="visible-overflow" if visible_overflow else "fit"),
            fallback_ladder=ladder, selected_rung=candidate.side,
            host_placement_id=(hosting_mark.placement_id if hosting_mark is not None and
                (associated_member or candidate.side == "inside") else None),
            paint_order=max(HOSTED_TEXT_PAINT_ORDER, host.paint_order + 1)
                if candidate.side == "inside" and host is not None else 300)
        selected_style = styles.get(candidate.side)
        if selected_style is not None:
            placed_text = replace(placed_text, theme_role=selected_style.role,
                                  style_occurrence_key=selected_style.key)
        text.append(placed_text)
        register_rect(placed_text.placement_id, "text", placed_text.collision_domain.slot, placed_text.bounds)
        obstacles.add(SurfaceObstacle(f"label-footprint:{placed_text.placement_id}", "label-visual",
            placed_text.collision_domain.slot, ObstacleRect(chip_box.x, chip_box.y, chip_box.right, chip_box.bottom)))
        if chip is not None:
            paint_bounds = Rect(Decimal(str(chip_box.x)), Decimal(str(chip_box.y)), Decimal(str(chip_box.width)),
                                Decimal(str(chip_box.height)))
            symbol_parts = ()
            if chip_measurement is not None:
                geometry, footprint = chip_measurement.geometry, chip_measurement.footprint
                origin_x, origin_y = chip_box.x - float(footprint.inline), chip_box.y - float(footprint.block)
                try:
                    paint_bounds, symbol_parts = complete_label_chip_placement(
                        chip_measurement, origin_x=origin_x, origin_y=origin_y)
                except ChipGeometryError as error:
                    role = semantic_binding(chip_semantic).theme_role
                    raise LayoutError("E_LAYOUT_CHIP_TEXT_GROUND_INVALID", f"/body/roles/{role}/chipShape",
                                      detail=f"reason={error.reason}; increase Render Context environment.scenePrecision") from error
            shapes.append(ShapePlacement(f"chip:{placed_text.placement_id}", placed_text.source_ref,
                "Symbol" if chip_measurement is not None else "Rect", paint_bounds,
                required=False, slot_id=context.text_slot(placed_text),
                paint_order=placed_text.paint_order - 1, semantic_id=chip_semantic,
                corner_radius=0.0 if chip_measurement is not None else resolve_corner_radius(request.theme_tokens.optional_token(
                    semantic_binding(chip_semantic).theme_role, "cornerRadius", "radius"),
                    width=chip_box.width, height=chip_box.height, legacy_radius=float(chip[1]) * chip_box.height),
                lane_row_id=placed_text.lane_row_id, lane_member_id=placed_text.lane_member_id,
                subjects=label_request.subjects, symbol_parts=symbol_parts,
                collision_bounds=(Rect(Decimal(str(chip_box.x)), Decimal(str(chip_box.y)),
                    Decimal(str(chip_box.width)), Decimal(str(chip_box.height)))
                    if chip_measurement is not None else None)))
        if visible_overflow:
            overflows.append((placed_text, slot_bounds))
            if label_request.subjects:
                visible_overflow_subjects.append((placed_text.placement_id, label_request.subjects))
        if visuals:
            if not hasattr(label_metrics, "cap_height_at"):
                raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(v.source_ref for v, _, _, _ in visuals))
            cap_height = float(label_metrics.cap_height_at(float(font_size)))
            for visual, icon, width, gap in visuals:
                inline = (candidate.bounds.x if visual.side == "leading" else
                    candidate.bounds.x + leading + text_width + trailing - gap - width)
                icon_bounds = Rect(Decimal(str(inline)), Decimal(str(placed_text.baseline[1] - cap_height +
                    (cap_height - float(font_size)) / 2)), Decimal(str(width)), Decimal(str(float(font_size))))
                icons.append(IconPlacement(f"visual:{placed_text.placement_id}:{visual.side}",
                    placed_text.source_ref, visual.source_ref, icon.icon_id, icon.kind, icon.content_identity,
                    icon.viewport, icon.payload, icon.alternative, visual.decorative, icon_bounds, "labelVisual",
                    width / icon.viewport[0], context.text_slot(placed_text), paint_order=placed_text.paint_order,
                    lane_row_id=placed_text.lane_row_id, lane_member_id=placed_text.lane_member_id,
                    host_placement_id=placed_text.placement_id))
        decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                           ladder, candidate.side, "placed", candidate.search_count))
    return SurfaceMemberLabelsBatch(tuple(text), tuple(shapes), tuple(icons),
        tuple(overflows), tuple(decisions), tuple(diagnostics), tuple(suppressions), frozenset(handled),
        tuple(diagnostic_provenance), tuple(visible_overflow_subjects))
