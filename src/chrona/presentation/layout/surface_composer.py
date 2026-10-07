"""Coordinates the surface phases in order and assembles the final Layout; reads the request and each phase's typed batch."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_lanes import (
    lane_owner as _lane_owner, review_rows as _review_rows, preflight_fixed_lane_layout,
)
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
    SurfaceInlineGeometry, prepare_surface_base, prepare_surface_inline,
)
from chrona.presentation.layout.surface_content import (
    complete_footer_band, compose_detail_panel_blocks, place_notes, place_summary,
    validate_detail_panel_placement,
)
from chrona.presentation.layout.surface_legend import SurfaceLegendContext, place_legend
from chrona.presentation.layout.slot_heading import SlotHeadings, complete_slot_headings, content_slot, full_slot
from chrona.presentation.layout.surface_completion import (
    SurfaceCompletionContext, SurfaceLayoutComposition, complete_surface_layout,
)
from chrona.presentation.layout.surface_annotations import SurfaceAnnotationContext, place_annotations
from chrona.presentation.layout.surface_table import (
    SurfaceTableHeaderSeed, compose_table, prepare_table_header_seed, table_row_indent_intents,
)
from chrona.presentation.layout.surface_heading import place_heading
from chrona.presentation.layout.surface_groups import (compose_group_presentation)
from chrona.presentation.layout.surface_backgrounds import (
    compose_calendar_backgrounds, compose_group_tabs, compose_row_group_backgrounds, replace_group_header_band,
)
from chrona.presentation.layout.surface_axis import (
    AxisVerticalSummary, SurfaceAxisFrame, SurfaceAxisMeasurement, SurfaceAxisPreparation,
    complete_axis_plot, measure_surface_axis, prepare_surface_axis, summarize_surface_axis_vertical,
)
from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT_FALLBACK
from chrona.presentation.layout.as_of_cone import complete_as_of_cone
from chrona.presentation.layout.surface_deadlines import compose_deadline_marks
from chrona.presentation.layout.surface_periods import compose_period_bands, period_label_requests
from chrona.presentation.layout.presentation import (MarkGeometry, required_row_block_extents)
from chrona.presentation.layout.text import metric_for_role
from chrona.presentation.layout.labels import (LabelRect, LabelRequest)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, FitWarning, PlacementDecision, IconPlacement, ShapePlacement, SlotPlacement, SurfaceLayoutRequest,
    LaneLabelSuppression,
)
from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation
from chrona.presentation.layout.surface_geometry import (
    bounds_from_rect as _bounds, coordinate_for_date as _coordinate,
)


def timeline_content_block_requirement(*, projection: Any, group_presentation: str,
                                       metric_values: dict[str, Decimal], role_geometries: dict[str, MarkGeometry] | None = None,
                                       mark_band_allocation: MarkBandAllocation | None = None,
                                       text_line_block: float = 0.0) -> Decimal:
    """Return the minimum timeline block extent for explicit review rows."""
    rows = _review_rows(projection) or tuple(
        type("_Row", (), {"group_id": item.group_id, "items": (item,)})()
        for item in projection.items
    )
    if getattr(projection, "lane_membership", None) is not None:
        # The View fixes lane count before measurement. Its full mark-facet
        # subtrack extent is closed after the inline scale exists; one mark
        # band per lane is the profile's minimum, not a second membership solve.
        rows = tuple(replace(row, items=row.items[:1]) for row in rows)
    requirements = required_row_block_extents(
        review_rows=tuple(rows), row_minimum=float(metric_values["timeline.row.minBlockSize"]),
        row_padding=float(metric_values["timeline.row.paddingBlock"]),
        mark_block_size=float(metric_values["timeline.mark.blockSize"]), role_geometries=role_geometries,
        mark_band_allocation=mark_band_allocation,
        text_line_block=text_line_block,
    )
    headers = 0
    previous = object()
    for row in rows:
        if row.group_id != previous:
            headers += 1 if row.group_id and group_presentation == "header" else 0
            previous = row.group_id
    return Decimal(str(geometry_sum(requirements))) + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0)


@dataclass(frozen=True)
class SurfacePreRowGeometry:
    """Closed native geometry reusable for natural demand and final row placement."""

    inline: SurfaceInlineGeometry
    axis: SurfaceAxisPreparation
    headings: SlotHeadings
    table: SurfaceTableHeaderSeed
    axis_content: SlotPlacement
    timeline_content: SlotPlacement
    row_viewport: Rect

    def required_timeline_block(self, *, foot_reserve: Decimal = Decimal(0)) -> Decimal:
        """Natural host demand from this candidate's native prefix, before row fill."""
        return _required_timeline_block(self.inline, self.row_viewport, foot_reserve)


def _required_timeline_block(inline: SurfaceInlineGeometry, row_viewport: Rect,
                             foot_reserve: Decimal) -> Decimal:
    prefix = max(Decimal(0), row_viewport.block - inline.timeline.bounds.block)
    return prefix + inline.natural_block_requirement + foot_reserve


@dataclass(frozen=True)
class _SurfaceNaturalPrefix:
    inline: SurfaceInlineGeometry
    axis_frame: SurfaceAxisFrame
    axis_measurement: SurfaceAxisMeasurement
    axis_summary: AxisVerticalSummary
    axis_slot: SlotPlacement
    prepared_headings: dict[str, SlotHeadings]


@dataclass(frozen=True)
class SurfaceNaturalGeometry:
    """Candidate-specific completed prefix demand, independent of placed/fill-expanded rows."""

    inline: SurfaceInlineGeometry
    axis_frame: SurfaceAxisFrame
    axis_measurement: SurfaceAxisMeasurement
    axis_summary: AxisVerticalSummary
    headings: SlotHeadings
    table: SurfaceTableHeaderSeed
    axis_content: SlotPlacement
    timeline_content: SlotPlacement
    row_viewport: Rect

    def required_timeline_block(self, *, foot_reserve: Decimal = Decimal(0)) -> Decimal:
        return _required_timeline_block(self.inline, self.row_viewport, foot_reserve)


def _request_with_candidate_lane_preflight(request: SurfaceLayoutRequest) -> SurfaceLayoutRequest:
    """Recompute fixed-lane inputs from this candidate's exact content and manifest."""
    if request.projection.lane_membership is not None:
        preflight = preflight_fixed_lane_layout(
            projection=request.projection, layout_manifest=request.layout_manifest,
            surface_content=request.surface_content, theme_tokens=request.theme_tokens,
            metric_values=request.measured_sources.metric_values,
            icon_assets=request.icon_assets, visual_requests=request.visual_requests,
            font_metrics=request.font_metrics,
        )
        return replace(request, fixed_lane_preflight=preflight)
    return request


def prepare_surface_candidate(request: SurfaceLayoutRequest) -> SurfacePreRowGeometry:
    """Close completed geometry using this candidate's exact lane preflight."""
    return prepare_surface_content(_request_with_candidate_lane_preflight(request))


def prepare_surface_natural_candidate(request: SurfaceLayoutRequest) -> SurfaceNaturalGeometry:
    """Close natural prefix demand using this candidate's exact lane preflight."""
    return prepare_surface_natural_geometry(_request_with_candidate_lane_preflight(request))


def _prepare_surface_natural_prefix(request: SurfaceLayoutRequest) -> _SurfaceNaturalPrefix:
    inline = prepare_surface_inline(request)
    request = inline.request
    axis_slot = inline.by_source["timeline-axis"]
    axis_decision = inline.decisions["timeline-axis"]
    prepared_headings = {}
    if axis_decision.heading is not None:
        own_heading = complete_slot_headings(
            request=request, slots=inline.by_source, decisions={"timeline-axis": axis_decision})
        prepared_headings["timeline-axis"] = own_heading
        axis_slot = content_slot(axis_slot, own_heading.reserved("timeline-axis"))
    axis_frame = SurfaceAxisFrame(inline.scale, inline.timeline, axis_slot, inline.metric_values)
    axis_measurement = measure_surface_axis(request, inline.scale)
    axis_summary = summarize_surface_axis_vertical(request, axis_frame, axis_measurement)
    return _SurfaceNaturalPrefix(inline, axis_frame, axis_measurement, axis_summary,
                                 axis_slot, prepared_headings)


def _complete_surface_natural_geometry(prefix: _SurfaceNaturalPrefix) -> SurfaceNaturalGeometry:
    inline, axis_summary, prepared_headings = prefix.inline, prefix.axis_summary, prefix.prepared_headings
    request = inline.request
    headings = complete_slot_headings(request=request, slots=inline.by_source, decisions=inline.decisions,
                                      axis_label_tiers=axis_summary.label_tiers,
                                      prepared=prepared_headings)
    table_content = content_slot(inline.table, headings.reserved("table"))
    timeline_content = content_slot(inline.timeline, headings.reserved("timeline"))
    table_seed = prepare_table_header_seed(
        request=request, table=table_content, review_rows=table_row_indent_intents(inline.review_rows),
        metric_values=inline.metric_values, group_tag_inline_size=inline.group_tag_inline_size)
    row_start = timeline_content.bounds.block
    if any(headings.reserved(source) for source in ("table", "timeline", "timeline-axis")):
        native_ends = [row_start]
        if table_seed.header_end_block is not None:
            native_ends.append(table_seed.header_end_block)
        if axis_summary.max_rect_block_end is not None:
            native_ends.append(axis_summary.max_rect_block_end)
        row_start = max(native_ends)
    row_viewport = Rect(timeline_content.bounds.inline, row_start, timeline_content.bounds.inline_size,
                        max(Decimal(0), timeline_content.bounds.block + timeline_content.bounds.block_size - row_start))
    return SurfaceNaturalGeometry(inline, prefix.axis_frame, prefix.axis_measurement, axis_summary,
                                  headings, table_seed, prefix.axis_slot, timeline_content, row_viewport)


def prepare_surface_natural_geometry(request: SurfaceLayoutRequest) -> SurfaceNaturalGeometry:
    """Close native prefix demand without axis host admission or row placement."""
    return _complete_surface_natural_geometry(_prepare_surface_natural_prefix(request))


def prepare_surface_content(request: SurfaceLayoutRequest, *,
                            natural: SurfaceNaturalGeometry | None = None) -> SurfacePreRowGeometry:
    """Complete native headers/captions without placing or fill-expanding any row."""
    if natural is None:
        prefix = _prepare_surface_natural_prefix(request)
        axis = prepare_surface_axis(prefix.inline.request, prefix.axis_frame,
                                    measured=prefix.axis_measurement)
        natural = _complete_surface_natural_geometry(prefix)
    else:
        # Candidate facts are reused, but final placement still performs native host admission.
        axis = prepare_surface_axis(natural.inline.request, natural.axis_frame,
                                    measured=natural.axis_measurement)
    return SurfacePreRowGeometry(natural.inline, axis, natural.headings, natural.table,
                                 natural.axis_content, natural.timeline_content, natural.row_viewport)


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
    text = list(place_heading(request, content_slot(by_source["title"], headings.reserved("title")),
                              measured_sources))
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
    diagnostics.extend(headings.diagnostics)
    visible_label_overflows = list(axis_batch.visible_label_overflows)
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
    visible_group_header_overflows = list(mark_batch.visible_group_header_overflows)
    groups = list(mark_batch.groups)
    for update in mark_batch.group_header_updates:
        shapes = list(replace_group_header_band(tuple(shapes), update))
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
            request, content_slot(legend, headings.reserved("legend")), metric_values, metric_for))
        marks.extend(legend_batch.marks)
        shapes.extend(legend_batch.shapes)
        relations.extend(legend_batch.relations)
        text.extend(legend_batch.text)
        side_content_warnings.extend(legend_batch.warnings)
        legend_slot = full_slot(legend, legend_batch.slot, headings.reserved("legend"))
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
    visible_label_overflows.extend(annotation_batch.visible_label_overflows)
    visible_route_fallbacks.extend(annotation_batch.visible_route_fallbacks)
    handled_candidate_visuals.update(annotation_batch.handled_visual_sources)
    text = [replace(item, slot_id=text_slot(item)) for item in text]
    text_visuals = place_text_visuals(tuple(text), request,
        handled_sources=handled_candidate_visuals, axis_label_targets=axis_label_targets,
        pre_reserved_placements=detail_visual_reservations)
    text, icons = list(text_visuals.text), list(text_visuals.icons)
    text_visual_warnings = list(text_visuals.warnings)
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
        lane_label_suppressions=lane_label_suppressions))
