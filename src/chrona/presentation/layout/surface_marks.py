"""Owns row/folded marks and progress/summary shapes; reads base geometry, projection and Theme tokens."""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.point_hosting import resolve_point_host_plan
from chrona.presentation.layout.point_host_geometry import (
    complete_hosted_point_geometry, translate_point_block, validate_hosted_point_collisions,
)
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.mark_role_geometry import (
    MARK_GEOMETRY_ROLES as MARK_GEOMETRY_ROLES,
    _default_actual_symbol as _default_actual_symbol,
    resolve_mark_geometries as resolve_mark_geometries,
    resolve_mark_band as resolve_mark_band,
)
from chrona.presentation.layout.surface_groups import (
    GroupHeaderExtentUpdate, replace_group_header_extent,
)
from chrona.presentation.layout.surface_quality import GroupPlacement, MarkPlacement, ShapePlacement, TemporalEndpointPlacement
from chrona.presentation.layout.mark_geometry import (
    CompletedWindowMark, MarkFacetAbsence, complete_mark_window_geometry, compose_item_marks,
)
from chrona.presentation.layout.mark_facet_visibility import admitted_source_selection
from chrona.presentation.layout.filled_contour import (
    ContourUnionError, intersect_visible_host_contour, union_filled_contours,
)
from chrona.presentation.layout.rounded_outline import rounded_rect_commands
from chrona.presentation.model.projection import WindowMode, shared_track_member_key, active_placement, finish_delta_text, finish_delta_semantic
from chrona.presentation.layout.label_footprint_measurement import measure_label_footprint
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.surface_deadlines import complete_deadline_host, deadline_boundary_in_window
from chrona.presentation.layout.text import metric_for_role, measure_text_width
from chrona.presentation.layout.lane_projection import (
    folded_instance_id, lane_missing_actual_visible,
)
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.layout.style_text import (
    resolve_label_candidate_styles, resolve_text_style_intent,
)
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrence, MarkOccurrenceKind, outside_window_provenance,
)
from chrona.presentation.layout.window_row_admission import geometry_folded_points
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_base import SurfaceBaseGeometry

MARK_PAINT_ORDER_BASE = 100


def pack_extent_lanes(extents: list[tuple[float, float]]) -> list[int]:
    """Greedy interval packing (#440): lowest lane whose last end is at or before each start.

    ``extents`` are ``(start, end)`` in the caller's sort order; the result is one lane per extent.
    Packing in start order is optimal for interval graphs, so the lane count is the clique number.
    """
    lane_ends: list[float] = []
    lanes: list[int] = []
    for start, end in extents:
        for lane, last_end in enumerate(lane_ends):
            if last_end <= start:
                lane_ends[lane] = end
                lanes.append(lane)
                break
        else:
            lane_ends.append(end)
            lanes.append(len(lane_ends) - 1)
    return lanes


@dataclass(frozen=True)
class SurfaceMarksBatch:
    """Completed source marks, progress shapes and folded-host updates."""
    marks: tuple[MarkPlacement, ...]
    progress_shapes: tuple[ShapePlacement, ...]
    groups: tuple[GroupPlacement, ...]
    group_header_updates: tuple[GroupHeaderExtentUpdate, ...]
    diagnostics: tuple[str, ...]
    absences: tuple[MarkFacetAbsence, ...]
    visible_group_header_overflows: tuple[tuple[str, Rect, float], ...]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()
    window_marks: tuple[CompletedWindowMark, ...] = ()
    temporal_endpoints: tuple[TemporalEndpointPlacement, ...] = ()


def progress_fill_bounds(host: Rect, fraction: float,
                         inset_ratio: Decimal = Decimal(0)) -> Rect | None:
    """Complete the optional progress submark inside its already-placed host."""
    if not 0 <= fraction <= 1:
        raise LayoutError("E_PRESENTATION_PROGRESS_INVALID", "/progressFill")
    if fraction == 0:
        return None
    if inset_ratio == 0:
        return Rect(host.inline, host.block, host.inline_size * Decimal(str(fraction)), host.block_size)
    block_inset = host.block_size * inset_ratio
    inline_inset = min(block_inset, host.inline_size / 4)
    return Rect(host.inline + inline_inset, host.block + block_inset,
                (host.inline_size - 2 * inline_inset) * Decimal(str(fraction)),
                host.block_size - 2 * block_inset)


def actual_progress_fraction(fraction: float, actual: Mapping[str, Any] | None, host: MarkPlacement,
                             planned: MarkPlacement | None) -> float | None:
    """The fraction of the Actual host an `actual` progress fill covers (#1869, Spec 61 section 1).

    Progress is the share of the planned span, drawn from the observed start: the fill is ``progress`` times the
    planned mark's extent, clipped to the Actual mark. An Actual with a finish is complete by observation and draws
    none. With no span to compare (a point Actual, an unmatched Actual, a planned mark with no extent) the fraction
    of the host itself is kept.
    """
    actual = actual or {}
    if isinstance(actual.get("finish"), date):
        return None
    if planned is None or actual.get("at") is not None:
        return fraction
    host_size, planned_size = float(host.bounds.inline_size), float(planned.bounds.inline_size)
    if planned_size <= 0:
        return fraction
    if host_size <= 0:
        return None
    return min(1.0, fraction * planned_size / host_size)


def complete_progress_shape(host: MarkPlacement, *, original_host: MarkPlacement,
                            fraction: float, inset_ratio: Decimal,
                            radius_ratio: Decimal) -> ShapePlacement | None:
    """The same original-host progress geometry for preflight and final paint."""
    bounds = progress_fill_bounds(original_host.bounds, fraction, inset_ratio)
    if bounds is None or bounds.inline_size <= 0:
        return None
    radius = float(radius_ratio) * float(min(bounds.inline_size, bounds.block_size))
    pattern_origin = (float(bounds.inline), float(bounds.block)) if host.paint_clip is not None else None
    fraction_origin = (float(bounds.inline), float(bounds.block))
    paint_clip = host.paint_clip
    commands, kind = (), "Rect"
    glyph_parts = tuple(part for part in original_host.symbol_parts if part.paint_mode is not None)
    if glyph_parts:
        # Painted glyph parts are emitted under part identities, so there is no
        # Scene primitive at the mark's base identity to use as a clip host.
        # Complete the fraction against the union of visible filled glyph ink.
        visible_fills = tuple(part.commands for part in host.symbol_parts
                              if part.paint_mode == "fill")
        if not visible_fills:
            return None
        try:
            filled_host = union_filled_contours(visible_fills)
        except ContourUnionError as error:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/body/progressFill",
                              node_id=host.source_ref,
                              detail=f"stage=progress-union; reason={error.reason}") from error
        points = tuple(point for command in filled_host for point in command.points)
        left, right = min(point[0] for point in points), max(point[0] for point in points)
        top, bottom = min(point[1] for point in points), max(point[1] for point in points)
        # The union backend may round source coordinates by a few ulps. Use its
        # exact completed contour bounds as the clipping coordinate frame; the
        # contour itself remains the physical boundary, not this Rect.
        contour_frame = Rect(Decimal(str(left)), Decimal(str(top)),
                             Decimal(str(right - left)), Decimal(str(bottom - top)))
        original = rounded_rect_commands(tuple(map(float, (
            bounds.inline, bounds.block, bounds.inline_size, bounds.block_size))), radius)
        commands = intersect_visible_host_contour(
            original, filled_host, contour_frame,
            source_ref=host.source_ref, facet="progress")
        if not commands:
            return None
        points = tuple(point for command in commands for point in command.points)
        left, right = min(point[0] for point in points), max(point[0] for point in points)
        top, bottom = min(point[1] for point in points), max(point[1] for point in points)
        if left == right or top == bottom:
            return None
        bounds = Rect(Decimal(str(left)), Decimal(str(top)),
                      Decimal(str(right - left)), Decimal(str(bottom - top)))
        kind, radius, pattern_origin, paint_clip = "Symbol", 0.0, fraction_origin, None
    elif host.paint_clip is not None:
        original = rounded_rect_commands(tuple(map(float, (
            bounds.inline, bounds.block, bounds.inline_size, bounds.block_size))), radius)
        commands = intersect_visible_host_contour(original, host.path_commands, host.bounds,
                                                  source_ref=host.source_ref, facet="progress")
        if not commands:
            return None
        bounds, kind, radius = host.bounds, "Symbol", 0.0
    return ShapePlacement(
        f"progress-fill:{host.placement_id}", host.source_ref, kind, bounds,
        required=False, slot_id=host.slot_id, clip_host_id=(None if glyph_parts else host.placement_id),
        host_placement_id=host.placement_id,
        paint_order=host.paint_order + 1, corner_radius=radius,
        semantic_id="progressFill", path_commands=commands, paint_clip=paint_clip,
        pattern_origin=pattern_origin)


def compose_surface_marks(base: SurfaceBaseGeometry, *,
                          lane_owner: Callable[[Any, Any], tuple[str, str] | None]) -> SurfaceMarksBatch:
    """Place row and folded marks, then progress fills and summary span bars."""
    request = base.request
    projection = request.projection
    review_rows = base.review_rows
    rows, tracks = base.rows, base.tracks
    scale, timeline = base.scale, base.timeline
    role_geometries = base.role_geometries
    mark_block_size = base.mark_block_size
    contract = request.presentation_contract
    visibility_index = getattr(request, "mark_visibility_index", None)
    style_index = getattr(request.surface_content, "style_intents", None)
    style_sources = StyleSourceOccurrences.from_projection(projection, as_of=contract.time.as_of)

    def prepared_style(item: Any, *, kind: MarkOccurrenceKind,
                       container_id: str, source_kind: str, member_id: str | None = None):
        if style_index is None or not style_index.intents:
            return None
        member = member_id or item.item_id or item.object_id
        occurrence = style_sources.occurrence(kind, container_id, member, item.object_id, source_kind)
        return occurrence.style_intents(style_index)
    if getattr(projection, "window_mode", WindowMode.SELECTED_PLANNED).is_bounded and visibility_index is None:
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window",
                          detail="stage=composition; reason=missing-visibility-index")

    def prepared_visibility(item: Any, *, kind: MarkOccurrenceKind,
                           container_id: str, source_kind: str, as_of: date | None):
        if visibility_index is None:
            return None
        occurrence = MarkOccurrence(kind, container_id, item.item_id or item.object_id,
                                    item.object_id, source_kind)
        return visibility_index.lookup(occurrence, projection=projection,
                                       as_of=as_of)

    window_marks: list[CompletedWindowMark] = []

    def completed_marks(composition, visibility, instance_id, source_occurrence):
        from chrona.presentation.model.mark_semantics import canonical_mark_semantic
        completed_marks = tuple(replace(mark,
            source_occurrence_key=source_occurrence.style_key(canonical_mark_semantic(
                mark.semantic_id, mark.mark_shape, gate_declared=request.theme_tokens.has_role("gate"))))
            for mark in composition.marks)
        if visibility is None:
            return completed_marks
        facets = {facet.source.placement_id(instance_id): facet for facet in visibility.facets}
        result = []
        for mark in completed_marks:
            facet = facets.get(mark.placement_id)
            if facet is None:
                raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                                  detail="stage=composition; reason=unaccounted-mark")
            completed = complete_mark_window_geometry(mark, facet, scale, base.plot)
            window_marks.append(completed)
            if completed.visible is not None:
                result.append(completed.visible)
        return tuple(result)

    diagnostics: list[str] = []
    diagnostic_provenance: list[DiagnosticProvenance] = []
    if visibility_index is not None:
        outside = outside_window_provenance(visibility_index)
        if outside is not None:
            diagnostics.append(outside.diagnostic)
            diagnostic_provenance.append(outside)
    absences: list[MarkFacetAbsence] = []
    marks: list[MarkPlacement] = []
    temporal_endpoints: list[TemporalEndpointPlacement] = []
    track_by_id = {item.instance_id: item for item in tracks}
    allocation = getattr(base, "mark_band_allocation", None)
    if allocation is not None:
        diagnostics.extend(allocation.diagnostics)
    for review_row in review_rows:
        members = sorted(enumerate(review_row.items),
                         key=lambda pair: shared_track_member_key(pair[1], pair[0]))
        for _, item in members:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            owner = lane_owner(review_row, item) if projection.lane_membership is not None else None
            instance_id = layout_id if projection.rows else item.object_id
            track = track_by_id[layout_id]
            frame = MarkBandFrame.from_track(track, scale, role_geometries, allocation)
            source_kind = item.source_kind if projection.rows else "combined"
            occurrence_kind = (MarkOccurrenceKind.LANE_FINAL if owner is not None else
                               MarkOccurrenceKind.ROW if projection.rows else MarkOccurrenceKind.AUTO)
            occurrence_container = owner[0] if owner is not None else (
                review_row.row_id if projection.rows else item.object_id)
            visibility = prepared_visibility(
                item, kind=occurrence_kind, container_id=occurrence_container,
                source_kind=source_kind, as_of=contract.time.as_of)
            if not getattr(item, "temporal_paint", True):
                if source_kind in {"primary", "combined"}:
                    start = active_placement(item).get("start")
                    end = active_placement(item).get("end")
                    if not isinstance(start, date) or not isinstance(end, date):
                        raise LayoutError("E_PRESENTATION_PLACEMENT_REQUIRED", "/projection/items")
                    facet = (next((facet for facet in visibility.facets
                                   if facet.source.facet in {"planned", "forecast"}), None)
                             if visibility is not None else None)
                    if visibility is not None and facet is None:
                        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                                          detail="stage=unpainted-port; reason=unaccounted-facet")
                    block, size = frame.role_bounds("planned")
                    centre = block + size / 2
                    temporal_endpoints.append(TemporalEndpointPlacement(
                        instance_id, item.object_id,
                        (coordinate_for_date(start, scale), centre)
                        if facet is None or facet.start_port_visible else None,
                        (coordinate_for_date(end, scale), centre)
                        if facet is None or facet.end_port_visible else None))
                continue
            composition = compose_item_marks(
                item=item, instance_id=instance_id, source_kind=source_kind, frame=frame,
                as_of=contract.time.as_of, theme_tokens=request.theme_tokens,
                slot_id=timeline.slot_id, paint_order_base=MARK_PAINT_ORDER_BASE,
                emit_missing_actual=(lane_missing_actual_visible(projection)
                    if owner is not None else True),
                selection=admitted_source_selection(visibility) if visibility is not None else None,
                style_intents=prepared_style(item, kind=occurrence_kind,
                                             container_id=occurrence_container, source_kind=source_kind),
            )
            marks.extend(replace(mark, lane_row_id=owner[0], lane_member_id=owner[1],
                                 lane_source_kind=source_kind) if owner is not None else mark
                         for mark in completed_marks(composition, visibility, instance_id,
                             style_sources.occurrence(occurrence_kind, occurrence_container,
                                 item.item_id or item.object_id,
                                 item.object_id, source_kind)))
            diagnostics.extend(composition.diagnostics)
            diagnostic_provenance.extend(composition.diagnostic_provenance)
            absences.extend(composition.absences)

    preflight = request.fixed_lane_preflight
    host_plan = (preflight.point_host_plan if preflight is not None else None)
    if host_plan is None:
        host_plan = resolve_point_host_plan(
            projection, as_of=contract.time.as_of,
            mode=request.layout_manifest.point_host_mode, visibility_index=visibility_index)
    if host_plan.relations:
        previous_marks = {mark.placement_id: mark for mark in marks}
        marks = list(complete_hosted_point_geometry(host_plan, tuple(marks)))
        validate_hosted_point_collisions(host_plan, tuple(marks), request.theme_tokens)
        final_marks = {mark.placement_id: mark for mark in marks}
        moved_records = []
        for record in window_marks:
            original = previous_marks.get(record.original.placement_id)
            completed = final_marks.get(record.original.placement_id)
            if original is not None and completed is not None and completed.physical_host is not None:
                offset = float(completed.bounds.block - original.bounds.block)
                record = replace(record, original=translate_point_block(record.original, offset),
                                 visible=completed)
            moved_records.append(record)
        window_marks = moved_records

    groups = tuple(base.groups)
    group_by_id = {group.group_id: group for group in groups}
    updates: list[GroupHeaderExtentUpdate] = []
    visible_header_overflows: list[tuple[str, Rect, float]] = []
    folded_by_group: dict[str, list[Any]] = {}
    for folded in geometry_folded_points(projection, request.row_admission):
        folded_by_group.setdefault(folded.group_id, []).append(folded)
    shown_deadlines = tuple(
        deadline for deadline in getattr(projection, "deadlines", ())
        if deadline_boundary_in_window(deadline, projection.window)
    )
    def folded_label_candidates():
        return (("end", "start") if contract.labels.side == "auto" else (contract.labels.side,))

    def folded_title_measures(folded):
        instance_id = folded_instance_id(folded, folded.item)
        key = (style_sources.label_key(folded.item, folded.group_id, "memberLabel", folded=True)
               if style_sources is not None else None)
        candidates = folded_label_candidates()
        selected = (resolve_label_candidate_styles(key, candidates, style_index, request.theme_tokens)
                    if key is not None else {})
        base_role = "groupHeader"
        return tuple((side, measure_label_footprint(
            f"member-label:{instance_id}", request.surface_content.member_name(folded.item, folded.group_id),
            (selected.get(side).role if selected.get(side) and selected[side].role else base_role),
            "memberLabel", request)) for side in candidates)

    def forecast_label_measures(folded):
        instance_id = folded_instance_id(folded, folded.item)
        title_measures = tuple(measure for _, measure in folded_title_measures(folded))
        title = replace(title_measures[0], size=(
            max(measure.size[0] for measure in title_measures),
            max(measure.size[1] for measure in title_measures)))
        delta_role = request.surface_content.label_text_role or "text"
        if style_sources is not None:
            delta_key = style_sources.label_key(
                folded.item, folded.group_id, finish_delta_semantic(folded.item), folded=True)
            delta_intent = resolve_text_style_intent(delta_key, style_index, request.theme_tokens)
            if delta_intent is not None and delta_intent.role:
                delta_role = delta_intent.role
        delta = measure_label_footprint(f"variance:{instance_id}", finish_delta_text(folded.item),
            delta_role, finish_delta_semantic(folded.item), request)
        return title, delta

    def folded_extent(folded: Any) -> tuple[float, float, float, float]:
        """Full inline/block footprint of a folded occurrence and its displayed deadlines."""
        label_treatment = request.theme_tokens.text_treatment("groupHeader")
        label_gap = max(1.0, float(label_treatment.font_size) * 0.25)
        label_side = contract.labels.side
        lefts, rights, deadline_lefts, deadline_rights = [], [], [], []
        track_top = float(allocation.outer_bounds[0]) if allocation is not None else 0.0
        track_bottom = (float(allocation.outer_bounds[1]) if allocation is not None
                        else float(mark_block_size))
        probe = MarkBandFrame(scale, 0.0, mark_block_size, role_geometries, allocation)
        for item in folded.all_items:
            visibility = prepared_visibility(
                item, kind=MarkOccurrenceKind.FOLDED, container_id=folded.group_id,
                source_kind=item.source_kind, as_of=contract.time.as_of)
            composition = compose_item_marks(
                item=item, instance_id=folded_instance_id(folded, item), source_kind=item.source_kind,
                frame=probe, as_of=contract.time.as_of, theme_tokens=request.theme_tokens,
                slot_id=timeline.slot_id, paint_order_base=MARK_PAINT_ORDER_BASE,
                emit_missing_actual=False, emit_diagnostics=False,
                selection=admitted_source_selection(visibility) if visibility is not None else None,
                style_intents=prepared_style(item, kind=MarkOccurrenceKind.FOLDED,
                                             container_id=folded.group_id, source_kind=item.source_kind))
            for mark in composition.marks:
                lefts.append(float(mark.bounds.inline))
                rights.append(float(mark.bounds.inline) + float(mark.bounds.inline_size))
                if mark.semantic_id not in {"planned", "forecast"}:
                    continue
                for deadline in shown_deadlines:
                    if deadline.object_id != mark.source_ref:
                        continue
                    geometry = complete_deadline_host(
                        base=base, theme_tokens=request.theme_tokens, deadline=deadline, host=mark,
                        paint_order_base=MARK_PAINT_ORDER_BASE)
                    bounds = geometry.painted_bounds
                    if bounds is None:
                        continue
                    deadline_lefts.append(float(bounds.inline))
                    deadline_rights.append(float(bounds.inline + bounds.inline_size))
                    track_top = min(track_top, float(bounds.block))
                    track_bottom = max(track_bottom, float(bounds.block + bounds.block_size))
        if not lefts:
            return (0.0, 0.0, track_top, track_bottom)
        if folded.item.forecast is not None:
            title, delta = forecast_label_measures(folded)
            reach = geometry_sum((title.size[0], title.gap, delta.size[0], delta.gap))
            left, right = min(lefts) - reach, max(rights) + reach
        else:
            styled_title = False
            if style_sources is not None:
                key = style_sources.label_key(folded.item, folded.group_id, "memberLabel", folded=True)
                selected = resolve_label_candidate_styles(
                    key, folded_label_candidates(), style_index, request.theme_tokens)
                styled_title = any(intent is not None and intent.role not in (None, "groupHeader")
                                   for intent in selected.values())
            if styled_title:
                title_measures = tuple(measure for _, measure in folded_title_measures(folded))
                width = max((measure.size[0] for measure in title_measures), default=0.0)
            else:
                width = measure_text_width(
                    request.surface_content.member_name(folded.item, folded.group_id), font_size=float(label_treatment.font_size),
                    font_metrics=metric_for_role(request.theme_tokens, "groupHeader", request.font_metrics),
                    letter_spacing=float(label_treatment.letter_spacing),
                    text_transform=label_treatment.transform, numeric_spacing="proportional")
            span = (width + label_gap) if width > 0 else 0.0
            left, right = ((min(lefts) - span, max(rights)) if label_side == "start"
                           else (min(lefts), max(rights) + span))
        if deadline_lefts:
            left, right = min(left, min(deadline_lefts)), max(right, max(deadline_rights))
        return (left, right, track_top, track_bottom)

    for group_id, folded_points in folded_by_group.items():
        group = group_by_id.get(group_id)
        if group is None or group.header_bounds is None:
            folded = folded_points[0]
            raise LayoutError("E_REVIEW_POINT_GROUP_HEADER_UNAVAILABLE",
                              f"/projection/foldedPoints/{folded.item.object_id}")
        base_pitch = allocation.outer_extent if allocation is not None else mark_block_size
        track_extents = {id(point): folded_extent(point) for point in folded_points}
        pitch = max(base_pitch, *(bottom - top for _, _, top, bottom in track_extents.values()))
        if any(point.item.forecast is not None for point in folded_points):
            pitch = max(pitch, *(measure.size[1] for point in folded_points
                if point.item.forecast is not None for measure in forecast_label_measures(point)))
        ordered_points = sorted(
            folded_points, key=lambda point: (active_placement(point.item).get("at"), point.item.object_id))
        lane_of = dict(zip((id(point) for point in ordered_points),
                           pack_extent_lanes([(track_extents[id(point)][0], track_extents[id(point)][1])
                                              for point in ordered_points])))
        occupied = (max(lane_of.values()) + 1) * pitch
        if occupied > float(group.header_bounds.block_size):
            expanded = Rect(group.header_bounds.inline, group.header_bounds.block,
                            group.header_bounds.inline_size, Decimal(str(occupied)))
            update = GroupHeaderExtentUpdate(group, expanded)
            updates.append(update)
            groups = replace_group_header_extent(groups, update)
            group = next(item for item in groups if item.group_id == group_id)
            group_by_id[group_id] = group
            visible_header_overflows.append((group_id, expanded,
                                             float(update.source.header_bounds.block_size)))
        first_block = float(group.header_bounds.block) + max(
            0.0, (float(group.header_bounds.block_size) - occupied) / 2)
        for folded in ordered_points:
            _, _, footprint_top, footprint_bottom = track_extents[id(folded)]
            footprint_height = footprint_bottom - footprint_top
            block = (first_block + lane_of[id(folded)] * pitch
                     + (pitch - footprint_height) / 2 - footprint_top)
            members = sorted(enumerate(folded.all_items),
                             key=lambda pair: shared_track_member_key(pair[1], pair[0]))
            for _, item in members:
                instance_id = folded_instance_id(folded, item)
                frame = MarkBandFrame(scale, block, mark_block_size, role_geometries, allocation)
                visibility = prepared_visibility(
                    item, kind=MarkOccurrenceKind.FOLDED, container_id=folded.group_id,
                    source_kind=item.source_kind, as_of=contract.time.as_of)
                composition = compose_item_marks(
                    item=item, instance_id=instance_id, source_kind=item.source_kind, frame=frame,
                    as_of=contract.time.as_of, theme_tokens=request.theme_tokens,
                    slot_id=timeline.slot_id, paint_order_base=MARK_PAINT_ORDER_BASE,
                    emit_missing_actual=False, emit_diagnostics=False,
                    selection=admitted_source_selection(visibility) if visibility is not None else None,
                    style_intents=prepared_style(item, kind=MarkOccurrenceKind.FOLDED,
                                                 container_id=folded.group_id, source_kind=item.source_kind),
                )
                marks.extend(completed_marks(composition, visibility, instance_id,
                    style_sources.occurrence(MarkOccurrenceKind.FOLDED, folded.group_id,
                        item.item_id or item.object_id, item.object_id, item.source_kind)))
                diagnostics.extend(composition.diagnostics)
                diagnostic_provenance.extend(composition.diagnostic_provenance)
                absences.extend(composition.absences)

    mark_by_id = {item.placement_id: item for item in marks}
    original_mark_by_id = {item.original.placement_id: item.original for item in window_marks}
    progress_shapes: list[ShapePlacement] = []
    progress_source = request.surface_content.progress_fill_source
    if progress_source is not None:
        progress_inset, progress_radius = request.theme_tokens.progress_track("progress-fill")
        for review_row in review_rows:
            for item in review_row.items:
                if progress_source == "actual":
                    fraction, host_prefix = (item.actual or {}).get("progress"), "actual"
                else:
                    fraction, host_prefix = getattr(item, "planned_progress", None), "planned"
                if (not isinstance(fraction, (int, float)) or isinstance(fraction, bool)
                        or not 0 <= fraction <= 1):
                    continue
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                owner = lane_owner(review_row, item) if projection.lane_membership is not None else None
                instance_id = layout_id if projection.rows else item.object_id
                host = mark_by_id.get(f"{host_prefix}:{instance_id}")
                if host is None or fraction == 0:
                    continue
                original_host = original_mark_by_id.get(host.placement_id, host)
                if progress_source == "actual":
                    planned_mark = mark_by_id.get(f"planned:{instance_id}")
                    fraction = actual_progress_fraction(
                        float(fraction), item.actual, original_host,
                        original_mark_by_id.get(planned_mark.placement_id, planned_mark) if planned_mark else None)
                    if not fraction:
                        continue
                shape = complete_progress_shape(host, original_host=original_host,
                    fraction=float(fraction), inset_ratio=progress_inset, radius_ratio=progress_radius)
                if shape is not None:
                    progress_shapes.append(replace(shape,
                        lane_row_id=owner[0] if owner else None,
                        lane_member_id=owner[1] if owner else None,
                        subjects=(DiagnosticSubject.project_object(item.object_id, item.title),)))

    return SurfaceMarksBatch(tuple(marks), tuple(progress_shapes), groups,
                             tuple(updates), tuple(diagnostics), tuple(absences),
                             tuple(visible_header_overflows), tuple(diagnostic_provenance),
                             tuple(window_marks), tuple(temporal_endpoints))
