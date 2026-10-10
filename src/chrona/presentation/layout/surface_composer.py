"""Coordinates the surface phases in order and assembles the final Layout; reads the request and each phase's typed batch."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_lanes import lane_owner as _lane_owner
from chrona.presentation.layout.surface_marks import (MARK_PAINT_ORDER_BASE, compose_surface_marks)
from chrona.presentation.layout.surface_visuals import (place_mark_visuals, place_text_visuals)
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, SurfaceMemberLabelsBatch, build_member_label_requests, place_member_labels,
)
from chrona.presentation.layout.surface_routes import (
    SurfaceRoutesContext,
)
from chrona.presentation.layout.surface_route_label_plan import (
    RouteLabelPlanContext, compose_routes_and_member_labels,
)
from chrona.presentation.layout.surface_lane_route_plan import LaneRoutePlanContext, plan_lane_route_reservations
from chrona.presentation.layout.surface_base import (
    prepare_surface_base,
)
from chrona.presentation.layout.surface_content import (
    complete_footer_band, compose_detail_panel_blocks, place_notes, place_summary,
    validate_detail_panel_placement,
)
from chrona.presentation.layout.surface_legend import SurfaceLegendContext, place_legend
from chrona.presentation.layout.slot_heading import (SlotHeadings, content_slot, full_slot, inline_content_slot,
                                                    inline_full_slot)
from chrona.presentation.layout.surface_completion import (
    SurfaceCompletionContext, SurfaceLayoutComposition, complete_surface_layout,
)
from chrona.presentation.layout.surface_annotations import SurfaceAnnotationContext, place_annotations
from chrona.presentation.layout.surface_table import (
    compose_table,
)
from chrona.presentation.layout.surface_heading import place_surface_headings
from chrona.presentation.layout.surface_groups import (compose_group_presentation, translate_group_header_text)
from chrona.presentation.layout.surface_backgrounds import (
    compose_calendar_backgrounds, compose_group_tabs, compose_row_group_backgrounds, replace_group_header_band,
)
from chrona.presentation.layout.surface_axis import (
    complete_axis_plot,
)
from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT_FALLBACK
from chrona.presentation.layout.as_of_cone import complete_as_of_cone
from chrona.presentation.layout.surface_deadlines import compose_deadline_marks
from chrona.presentation.layout.surface_periods import compose_period_bands, period_label_requests
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance
from chrona.presentation.layout.text import metric_for_role
from chrona.presentation.layout.labels import (LabelRect, LabelRequest)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, FitWarning, PlacementDecision, IconPlacement, ShapePlacement, SurfaceLayoutRequest,
    LaneLabelSuppression,
)
from chrona.presentation.layout.surface_geometry import (
    bounds_from_rect as _bounds, coordinate_for_date as _coordinate,
)
from chrona.presentation.layout.surface_preparation import (
    SurfaceNaturalGeometry, SurfacePreRowGeometry, prepare_surface_candidate,
    prepare_surface_content, prepare_surface_natural_candidate, prepare_surface_natural_geometry,
    timeline_content_block_requirement,
)


def compose_surface_layout(request: SurfaceLayoutRequest, *,
                           prepared: SurfacePreRowGeometry | None = None) -> SurfaceLayoutComposition:
    """Resolve rows/tracks from native pre-row geometry, then complete one surface."""
    prepared = prepared if prepared is not None else prepare_surface_content(request)
    inline, prepared_axis, headings, table_seed = prepared.inline, prepared.axis, prepared.headings, prepared.table
    axis_slot, timeline_content, row_viewport = prepared.axis_content, prepared.timeline_content, prepared.row_viewport
    table_content = table_seed.table_slot
    request = inline.request
    base = prepare_surface_base(request, inline=inline, row_viewport=row_viewport)
    request = base.request
    projection = request.projection
    layout_manifest = base.layout_manifest
    measured_sources = base.measured_sources
    metric_values = base.metric_values
    start, end = projection.window
    slots, by_source, table, timeline = base.slots, base.by_source, base.table, base.timeline
    review_rows, timeline_bounds = base.review_rows, _bounds(row_viewport)
    slot_ids = base.slot_ids
    text_slot = base.text_slot
    scale, rows, raw_rows = base.scale, base.rows, base.raw_rows
    groups, tracks = base.groups, base.tracks
    role_geometries, mark_block_size = base.role_geometries, base.mark_block_size
    table_bounds = table_seed.table_bounds
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    def metric_for(typography_role: str) -> Any:
        return metric_for_role(request.theme_tokens, typography_role, request.font_metrics)
    body_size = float(request.theme_tokens.text_treatment("text").font_size)
    # Caption reservations precede native content, while primitive order remains title/detail/captions.
    axis_batch = complete_axis_plot(prepared_axis, base.plot)
    heading_slot_blocks = {source: by_source[source].bounds.block for source in headings.reserve or {}}
    heading_batch = place_surface_headings(
        request, {source: content_slot(slot, headings.reserved(source))
                  for source, slot in by_source.items()}, measured_sources)
    text = list(heading_batch.text)
    footer_provisional_slots = slots
    detail_sources = {"group-details", "milestones", "observations"}
    detail_content_slots = tuple(content_slot(slot, headings.reserved(slot.source_ref))
                                if slot.source_ref in detail_sources else slot for slot in slots)
    slots, detail_panel_text, detail_panel_warnings, detail_visual_reservations = compose_detail_panel_blocks(
        slots=detail_content_slots, request=request, requested_canvas=request.layout_manifest.viewport,
        caption_reserves=headings.reserve,
    )
    slots = tuple(full_slot(by_source[slot.source_ref], slot, headings.reserved(slot.source_ref))
                  if slot.source_ref in detail_sources else slot for slot in slots)
    by_source = {slot.source_ref: slot for slot in slots}
    text.extend(detail_panel_text)
    text.extend(headings.text)
    table_batch = compose_table(base, seed=table_seed)
    column_placements = table_batch.columns
    text.extend(table_batch.text)
    group_batch = compose_group_presentation(
        request=request, rows=rows, review_rows=review_rows, groups=groups, body_size=body_size,
        tag_column=(base.table_bounds[0], base.group_tag_inline_size) if base.group_tag_inline_size else None)
    text.extend(group_batch.text)
    shapes: list[ShapePlacement] = []
    shapes.extend(compose_row_group_backgrounds(
        base=base, rows=rows, groups=groups, theme_tokens=request.theme_tokens,
        group_presentation=group_batch,
        row_decoration=request.surface_content.row_decoration,
        group_decoration=request.surface_content.group_decoration))
    axis = by_source["timeline-axis"]
    shapes.extend(axis_batch.shapes)
    text.extend(axis_batch.text)
    axis_tier_outcomes = list(axis_batch.tier_outcomes)
    axis_decisions = list(axis_batch.decisions)
    axis_label_targets = axis_batch.label_targets
    axis_band_targets = axis_batch.band_targets
    diagnostics = list(axis_batch.diagnostics)
    diagnostic_provenance: list[DiagnosticProvenance] = []
    diagnostics.extend(headings.diagnostics)
    diagnostics.extend(heading_batch.diagnostics)
    visible_label_overflows = list(axis_batch.visible_label_overflows)
    visible_label_subjects: dict[str, tuple[Any, ...]] = {}
    calendar_intervals = axis_batch.calendar_intervals
    contract = request.presentation_contract
    period_batch = compose_period_bands(
        base=base, theme_tokens=request.theme_tokens, periods=projection.periods, window=projection.window)
    shapes.extend(period_batch.shapes)
    diagnostics.extend(period_batch.diagnostics)
    shapes.extend(compose_calendar_backgrounds(
        base=base, theme_tokens=request.theme_tokens, intervals=calendar_intervals))
    as_of_label: tuple[float, str] | None = None
    if contract.time.as_of is not None and start <= contract.time.as_of < end:
        x = _coordinate(contract.time.as_of, scale)
        shapes.append(ShapePlacement("as-of", "actual-set", "Path",
                                     Rect(Decimal(str(x)), base.plot.block, Decimal(0), base.plot.block_size),
                                     ((x, float(base.plot.block)), (x, float(base.plot.block + base.plot.block_size))),
                                     paint_order=MARK_PAINT_ORDER_BASE))
        as_of_cone = complete_as_of_cone(request.theme_tokens, base.plot, x)  # #890: the light the marker casts
        if as_of_cone is not None:
            shapes.append(as_of_cone)
        as_of_label = (x, contract.time.as_of_label) if contract.time.as_of_label else None
    mark_batch = compose_surface_marks(base, lane_owner=_lane_owner)
    marks = list(mark_batch.marks)
    mark_by_id = {item.placement_id: item for item in marks}
    mark_absences = list(mark_batch.absences)
    diagnostics.extend(mark_batch.diagnostics)
    diagnostic_provenance.extend(mark_batch.diagnostic_provenance)
    visible_group_header_overflows = list(mark_batch.visible_group_header_overflows)
    groups = list(mark_batch.groups)
    for update in mark_batch.group_header_updates:
        old_bounds, final_bounds = update.source.header_bounds, update.header_bounds
        if old_bounds is not None:
            block_delta = (float(final_bounds.block - old_bounds.block)
                           + (float(final_bounds.block_size - old_bounds.block_size) / 2))
            text = list(translate_group_header_text(tuple(text), group_id=update.source.group_id,
                                                   block_delta=block_delta))
        shapes = list(replace_group_header_band(
            tuple(shapes), update, extent=base.layout_manifest.background_extents.get("groupHeaderBand", "")))
    shapes.extend(compose_group_tabs(
        groups=tuple(groups), theme_tokens=request.theme_tokens,
        tag_column=(base.table_bounds[0], base.group_tag_inline_size) if base.group_tag_inline_size else None))
    shapes.extend(mark_batch.progress_shapes)
    shapes.extend(mark_batch.summary_shapes)
    deadline_batch = compose_deadline_marks(
        base=base, theme_tokens=request.theme_tokens, deadlines=projection.deadlines, marks=mark_batch.marks,
        window=projection.window, paint_order_base=MARK_PAINT_ORDER_BASE)
    shapes.extend(deadline_batch.shapes)
    diagnostics.extend(deadline_batch.diagnostics)
    placement_decisions: list[PlacementDecision] = list(axis_decisions)
    member_label_context = SurfaceMemberLabelContext(
        request, projection, layout_manifest, by_source, text_slot, review_rows, tuple(rows), tuple(tracks),
        tuple(groups), scale, tuple(marks), timeline_bounds, as_of_label,
        as_of_below_plot=base.as_of_foot_reserve > 0 and as_of_label is not None,
        rows_bottom=float(base.plot.block + base.plot.block_size),
    )
    if base.as_of_foot_fallback and as_of_label is not None:
        diagnostics.append(f"{BELOW_PLOT_FALLBACK}:as-of-label")
    member_label_requests = build_member_label_requests(member_label_context)
    member_label_subjects = {
        item.placement_id: item.subjects
        for item in (*member_label_requests.pre_route, *member_label_requests.post_route)
        if item.subjects
    }
    period_requests = period_label_requests(period_batch.extents, _bounds(base.plot))
    if period_requests:  # placed first of the pre-route labels, so routes and later labels avoid them
        member_label_requests = replace(member_label_requests,
                                        pre_route=(*period_requests, *member_label_requests.pre_route))
    candidate_icons: list[IconPlacement] = []
    handled_candidate_visuals: set[str] = set()
    lane_label_suppressions: list[LaneLabelSuppression] = []
    # One monotonically growing Layout inventory is shared by labels, semantic
    # routes and annotations. Background bands deliberately do not enter it.
    surface_obstacles = SurfaceObstacleIndex()

    def register_rect(placement_id: str, obstacle_class: str, region_id: str, bounds: Rect) -> None:
        inline, block, inline_size, block_size = _bounds(bounds)
        if inline_size > 0 and block_size > 0:
            surface_obstacles.add(SurfaceObstacle(placement_id, obstacle_class, region_id,
                                                  ObstacleRect(inline, block, inline + inline_size, block + block_size)))

    def register_path(placement_id: str, obstacle_class: str, region_id: str,
                      points: tuple[tuple[float, float], ...], *, stroke_width: float = 0.0) -> None:
        for index, (source, target) in enumerate(zip(points, points[1:])):
            if source != target:
                surface_obstacles.add(SurfaceObstacle(f"{placement_id}:segment:{index}", obstacle_class,
                                                      region_id, ObstacleSegment(source, target, stroke_width)))

    def register_port(placement_id: str, point: tuple[float, float], region_id: str) -> None:
        surface_obstacles.add(SurfaceObstacle(placement_id, "port", region_id,
                                              ObstacleRect(point[0] - 0.01, point[1] - 0.01,
                                                           point[0] + 0.01, point[1] + 0.01)))

    for mark in marks:
        register_rect(mark.placement_id, "mark", "timeline", mark.bounds)
    for placed_text in text:
        if placed_text.required and placed_text.overflow != "suppressed":
            register_rect(placed_text.placement_id, "text", placed_text.collision_domain.slot, placed_text.bounds)
    for shape in shapes:
        if shape.placement_id == "as-of" and len(shape.points) >= 2:
            surface_obstacles.add(SurfaceObstacle(shape.placement_id, "rule", "timeline",
                                                  ObstacleSegment(shape.points[0], shape.points[1])))
        elif shape.semantic_id == "deadlineMark":  # a thin rule an annotation candidate must not cover, as for the as-of rule
            register_path(shape.placement_id, "rule", "timeline", shape.points)

    timeline_rect = LabelRect(*timeline_bounds)

    def accept_member_label_batch(batch: SurfaceMemberLabelsBatch) -> None:
        text.extend(batch.text)
        shapes.extend(batch.shapes)
        candidate_icons.extend(batch.icons)
        visible_label_overflows.extend(batch.visible_overflows)
        placement_decisions.extend(batch.decisions)
        diagnostics.extend(batch.diagnostics)
        diagnostic_provenance.extend(batch.diagnostic_provenance)
        visible_label_subjects.update(batch.visible_overflow_subjects)
        lane_label_suppressions.extend(batch.lane_label_suppressions)
        handled_candidate_visuals.update(batch.handled_visual_sources)

    def place_label_phase(requests: tuple[LabelRequest, ...]) -> None:
        accept_member_label_batch(place_member_labels(member_label_context, requests, surface_obstacles))

    lane_route_plan = plan_lane_route_reservations(LaneRoutePlanContext(
        member_label_context, member_label_requests.pre_route, tuple(text), surface_obstacles,
        lambda index, texts: SurfaceRoutesContext(request, projection, review_rows, tuple(rows), tuple(groups),
            tuple(marks), timeline_bounds, layout_manifest, metric_values, texts, index)))
    surface_obstacles.extend(lane_route_plan.reservations)
    place_label_phase(member_label_requests.pre_route)

    route_label_plan = compose_routes_and_member_labels(RouteLabelPlanContext(
        member_label_context, member_label_requests.post_route, tuple(text), surface_obstacles,
        lambda index, texts: SurfaceRoutesContext(request, projection, review_rows, tuple(rows), tuple(groups),
            tuple(marks), timeline_bounds, layout_manifest, metric_values, texts, index)))
    surface_obstacles = route_label_plan.obstacles
    routes_batch = route_label_plan.routes
    relations = list(routes_batch.relations)
    visible_route_fallbacks = list(routes_batch.visible_route_fallbacks)
    instance_anchors = dict(routes_batch.instance_anchors)
    instance_rows = dict(routes_batch.instance_rows)
    comparison_clusters = dict(routes_batch.comparison_clusters)
    diagnostics.extend(routes_batch.diagnostics)

    accept_member_label_batch(route_label_plan.members)
    relation_labels = route_label_plan.relation_labels
    text.extend(relation_labels.text)
    diagnostics.extend(relation_labels.diagnostics)
    visible_label_overflows.extend(relation_labels.visible_label_overflows)

    side_content_warnings: list[FitWarning] = list(group_batch.warnings)
    side_content_warnings.extend(headings.warnings)
    legend = by_source.get("legend")
    if legend:
        legend_batch = place_legend(SurfaceLegendContext(
            request, inline_content_slot(content_slot(legend, headings.reserved("legend")),
                                         headings.reserved_inline("legend")), metric_values, metric_for))
        marks.extend(legend_batch.marks)
        shapes.extend(legend_batch.shapes)
        relations.extend(legend_batch.relations)
        text.extend(legend_batch.text)
        side_content_warnings.extend(legend_batch.warnings)
        legend_slot = inline_full_slot(legend, full_slot(legend, legend_batch.slot, headings.reserved("legend")),
                                       headings.reserved_inline("legend"))
        slots = tuple(legend_slot if slot.source_ref == "legend" else slot for slot in slots)
    notes = by_source.get("notes")
    if notes:
        notes_slot, notes_text = place_notes(request, content_slot(notes, headings.reserved("notes")), body_size)
        notes_slot = full_slot(notes, notes_slot, headings.reserved("notes"))
        text.extend(notes_text)
        slots = tuple(notes_slot if slot.source_ref == "notes" else slot for slot in slots)
    slots = complete_footer_band(provisional_slots=footer_provisional_slots, completed_slots=slots)
    by_source = {slot.source_ref: slot for slot in slots}
    for source, block in heading_slot_blocks.items():
        moved = by_source[source].bounds.block - block
        if moved:  # the footer band carried the slot down: its caption goes with it
            text = [replace(item, bounds=Rect(item.bounds.inline, item.bounds.block + moved,
                                              item.bounds.inline_size, item.bounds.block_size),
                            baseline=(item.baseline[0], item.baseline[1] + float(moved)))
                    if item.collision_domain.slot == "slot-heading" and item.source_ref == source else item
                    for item in text]
    summary_slot = by_source.get("summary")
    if summary_slot:
        text.extend(place_summary(request, content_slot(summary_slot, headings.reserved("summary"))))

    annotation_slot = by_source.get("annotations")
    timeline_content = replace(timeline_content, bounds=row_viewport)
    annotation_by_source = {**by_source, "table": table_content, "timeline": timeline_content,
                            "timeline-axis": axis_slot}
    if annotation_slot is not None:
        annotation_by_source["annotations"] = content_slot(annotation_slot, headings.reserved("annotations"))
    annotation_batch = place_annotations(SurfaceAnnotationContext(
        request, projection, layout_manifest, contract, review_rows, rows, annotation_by_source, scale, start, end,
        timeline_content, timeline_bounds, mark_by_id, comparison_clusters, instance_rows, metric_for,
        surface_obstacles, register_rect, register_port))
    text.extend(annotation_batch.text)
    shapes.extend(annotation_batch.shapes)
    relations.extend(annotation_batch.relations)
    candidate_icons.extend(annotation_batch.icons)
    placement_decisions.extend(annotation_batch.decisions)
    diagnostics.extend(annotation_batch.diagnostics)
    diagnostic_provenance.extend(annotation_batch.diagnostic_provenance)
    visible_label_overflows.extend(annotation_batch.visible_label_overflows)
    visible_route_fallbacks.extend(annotation_batch.visible_route_fallbacks)
    handled_candidate_visuals.update(annotation_batch.handled_visual_sources)
    text = [replace(item, slot_id=text_slot(item)) for item in text]
    text_visuals = place_text_visuals(tuple(text), request,
        handled_sources=handled_candidate_visuals, axis_label_targets=axis_label_targets,
        pre_reserved_placements=detail_visual_reservations)
    text, icons = list(text_visuals.text), list(text_visuals.icons)
    icons = [replace(icon, subjects=member_label_subjects.get(icon.host_placement_id, icon.subjects))
             for icon in icons]
    text_visual_warnings = [replace(warning, subjects=member_label_subjects.get(warning.placement_id, warning.subjects))
                            for warning in text_visuals.warnings]
    validate_detail_panel_placement(text, slots)
    icons.extend(candidate_icons)
    icons.extend(place_mark_visuals(tuple(marks), request).icons)

    return complete_surface_layout(SurfaceCompletionContext(
        request=request, projection=projection,
        layout_manifest=layout_manifest, review_rows=review_rows,
        rows=rows, tracks=tracks,
        groups=groups, scale=scale,
        slots=slots, by_source=by_source,
        timeline=timeline, axis=axis,
        table=table, table_bounds=table_bounds,
        timeline_bounds=timeline_bounds, column_placements=column_placements,
        text=text, marks=marks,
        shapes=shapes, relations=relations,
        icons=icons, placement_decisions=placement_decisions,
        axis_tier_outcomes=axis_tier_outcomes, diagnostics=diagnostics,
        mark_absences=mark_absences, axis_band_targets=axis_band_targets,
        detail_panel_warnings=detail_panel_warnings, side_content_warnings=side_content_warnings,
        text_visual_warnings=text_visual_warnings, visible_label_overflows=visible_label_overflows,
        visible_route_fallbacks=visible_route_fallbacks, visible_group_header_overflows=visible_group_header_overflows,
        lane_label_suppressions=lane_label_suppressions,
        diagnostic_provenance=tuple(diagnostic_provenance),
        visible_label_subjects=visible_label_subjects))
