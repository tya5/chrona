"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.pattern_placement import PatternedPlacement, complete_pattern_placement
from chrona.presentation.layout.surface_lanes import lane_owner as _lane_owner, review_rows as _review_rows
from chrona.presentation.layout.surface_marks import (
    MARK_PAINT_ORDER_BASE, folded_instance_id as _folded_instance_id,
    compose_surface_marks,
)
from chrona.presentation.layout.surface_visuals import (
    measure_candidate_visuals, place_axis_band_visuals, place_mark_visuals,
    place_text_visuals,
)
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, build_member_label_requests, place_member_labels,
)
from chrona.presentation.layout.surface_routes import (
    SurfaceRoutesContext, compose_surface_routes, place_relation_labels,
)
from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.layout.surface_content import (
    complete_footer_band, compose_detail_panel_blocks, place_notes, place_summary,
    validate_detail_panel_placement,
)
from chrona.presentation.layout.surface_legend import SurfaceLegendContext, place_legend
from chrona.presentation.layout.surface_table import compose_table
from chrona.presentation.layout.surface_groups import (
    compose_group_presentation,
)
from chrona.presentation.layout.surface_backgrounds import (
    BACKGROUND_SEMANTIC_IDS, compose_calendar_backgrounds,
    compose_row_group_backgrounds, replace_group_header_band,
    validate_background_shapes,
)
from chrona.presentation.layout.surface_axis import compose_axis
from chrona.presentation.model.semantic_registry import (
    axis_band_semantic_ids, semantic_binding)
from chrona.presentation.layout.presentation import (
    MarkGeometry, TrackPlacement, required_row_block_extents,
)
from chrona.presentation.layout.text import measure_text_width, metric_for_role, place_text, wrap_text
from chrona.presentation.layout.annotations import (
    AnnotationBox, annotation_rail_candidates, nearest_box_port, place_annotation_rail, project_annotation_box,
    resolve_annotation_anchor,
)
from chrona.presentation.layout.annotation_search import (
    nearest_free_box, nearest_free_tail_box, nearest_free_routed_tail_box,
)
from chrona.presentation.layout.balloon_geometry import balloon_outline
from chrona.presentation.layout.labels import LabelPlacement
from chrona.presentation.layout.annotation_topology import (
    AnnotationRouteTrial, local_route_bounds, route_annotation_candidate, visible_segments,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import (
    LabelRect, LabelRequest, place_label,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import ConnectorEgress, coincident_endpoint_port_ids, connector_egress_candidates
from chrona.presentation.model.placement_candidates import candidate_order
from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.routing import (
    relation_route_quality,
)
from chrona.presentation.layout.mark_geometry import MarkFacetAbsence
from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.lane_mark_facets import (
    _mark_facets, _overlay_compound_facets, _with_mark_visuals,
)
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, FitWarning, MarkPlacement, PathCommand, PlacementDecision, RelationPlacement, RowPlacement, ScalePlacement,
    IconPlacement, LayoutImageFill, ShapePlacement, SurfacePlacement, SurfaceLayoutRequest,
    TextPlacement, LaneEmissionFacet, LaneEmissionPlacement, LaneLabelSuppression,
    annotation_presentation,
)
from chrona.presentation.layout.image_slice_geometry import image_slice_tiles
from chrona.presentation.layout.surface_geometry import (
    GEOMETRY_TOLERANCE, HOSTED_TEXT_PAINT_ORDER,
    bounds_from_rect as _bounds, coordinate_for_date as _coordinate,
)


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]
    mark_absences: tuple[MarkFacetAbsence, ...] = ()


def _lane_emissions(projection: Any, review_rows: tuple[Any, ...], marks: list[MarkPlacement],
                    text: list[Any], shapes: list[ShapePlacement], icons: tuple[IconPlacement, ...],
                    theme_tokens: Any) -> tuple[LaneEmissionPlacement, ...]:
    """Close the typed Layout-to-Scene member inventory after all geometry is final."""
    if projection.lane_membership is None:
        return ()
    items: dict[tuple[str, str, str, str], Any] = {}
    for row in review_rows:
        for item, member_id in zip(row.items, row.member_item_ids, strict=True):
            key = (row.row_id, member_id, item.source_kind, item.object_id)
            if key in items:
                raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", f"/projection/laneRows/{row.row_id}")
            items[key] = item
    icons_by_host: dict[str, list[IconPlacement]] = {}
    for icon in icons:
        if icon.host_placement_id is not None:
            icons_by_host.setdefault(icon.host_placement_id, []).append(icon)
    progress_by_host: dict[str, list[ShapePlacement]] = {}
    for shape in shapes:
        if shape.clip_host_id is not None and shape.semantic_id == "progressFill":
            progress_by_host.setdefault(shape.clip_host_id, []).append(shape)

    grouped: dict[tuple[str, str, str, str, str], list[LaneEmissionFacet]] = {}

    def add(placement_type: str, placement_id: str, row_id: str, member_id: str,
            purpose: str, facet: LaneEmissionFacet) -> None:
        grouped.setdefault((placement_type, placement_id, row_id, member_id, purpose), []).append(facet)

    for mark in marks:
        if mark.lane_row_id is None:
            continue
        if mark.lane_member_id is None or mark.lane_source_kind is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", mark.placement_id)
        item = items.get((mark.lane_row_id, mark.lane_member_id,
                          mark.lane_source_kind, mark.source_ref))
        if item is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", mark.placement_id)
        instance = LaneProjectionInstance(mark.lane_row_id, item.item_id or item.object_id,
                                          item.object_id, item.source_kind)
        facets = _overlay_compound_facets(_mark_facets(item, instance, mark, theme_tokens))
        facets = _with_mark_visuals(item, instance, mark, facets,
                                    icons_by_host.get(mark.placement_id, ()),
                                    progress_by_host.get(mark.placement_id, ()), theme_tokens)
        for facet in facets:
            if facet.icon_projection is not None:
                placement_type = "icon"
                placement_id = facet.icon_projection.placement_id
            elif facet.progress_projection is not None:
                placement_type = "shape"
                placement_id = facet.primitive_id
            else:
                placement_type = "mark"
                placement_id = mark.placement_id
            add(placement_type, placement_id, mark.lane_row_id, mark.lane_member_id,
                facet.purpose,
                LaneEmissionFacet(facet.facet_id, placement_type, placement_id,
                                  facet.primitive_id, facet.visible_footprint, "mark",
                                  (facet.glyph_part_projection.part_index
                                   if facet.glyph_part_projection is not None else
                                   facet.icon_projection.path_index
                                   if facet.icon_projection is not None else None)))

    for placed in text:
        if (placed.lane_row_id is None or placed.overflow == "suppressed"
                or placed.semantic_id not in {"memberLabel", "finishDelta"}):
            continue
        if placed.lane_member_id is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", placed.placement_id)
        left, top, width, height = _bounds(placed.bounds)
        if width <= 0 or height <= 0:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", placed.placement_id)
        obstacle = ObstacleRect(left, top, left + width, top + height)
        purpose = semantic_binding(placed.semantic_id).purpose
        add("text", placed.placement_id, placed.lane_row_id, placed.lane_member_id,
            purpose, LaneEmissionFacet(f"label:{placed.placement_id}", "text", placed.placement_id,
                                       placed.placement_id, obstacle, "required-label"))

    # Text-associated icons and chips are independent Scene primitives but
    # retain the same typed owner and Layout-completed viewport/box footprint.
    for icon in icons:
        if icon.lane_row_id is None or icon.semantic_id == "iconMark":
            continue
        if icon.lane_member_id is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", icon.placement_id)
        left, top, width, height = _bounds(icon.bounds)
        obstacle = ObstacleRect(left, top, left + width, top + height)
        purpose = semantic_binding(icon.semantic_id).purpose
        add("icon", icon.placement_id, icon.lane_row_id, icon.lane_member_id,
            purpose, LaneEmissionFacet(f"icon:{icon.placement_id}", "icon", icon.placement_id,
                                       icon.placement_id, obstacle, "required-label"))
    for shape in shapes:
        if shape.lane_row_id is None or shape.clip_host_id is not None:
            continue
        if shape.lane_member_id is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", shape.placement_id)
        left, top, width, height = _bounds(shape.bounds)
        if width <= 0 or height <= 0:
            continue
        purpose = semantic_binding(shape.semantic_id).purpose
        add("shape", shape.placement_id, shape.lane_row_id, shape.lane_member_id,
            purpose, LaneEmissionFacet(f"shape:{shape.placement_id}", "shape", shape.placement_id,
                                       shape.placement_id,
                                       ObstacleRect(left, top, left + width, top + height),
                                       "required-label"))
    return tuple(LaneEmissionPlacement(kind, placement_id, row_id, member_id, purpose,
                                       tuple(facets))
                 for (kind, placement_id, row_id, member_id, purpose), facets in grouped.items())


def _complete_hosted_text_identity(
        text: tuple[TextPlacement, ...], marks: tuple[MarkPlacement, ...],
        lane_emissions: tuple[LaneEmissionPlacement, ...]) -> tuple[TextPlacement, ...]:
    """Resolve abstract lane-mark hosts to their first emitted glyph part."""
    emitted_mark_hosts: dict[str, str] = {}
    for emission in lane_emissions:
        if emission.placement_type != "mark":
            continue
        ordered = sorted(emission.facets, key=lambda facet: (
            -1 if facet.part_index is None else facet.part_index, facet.primitive_id))
        host_id = ordered[0].primitive_id
        previous = emitted_mark_hosts.setdefault(emission.placement_id, host_id)
        if previous != host_id:
            raise LayoutError("E_LAYOUT_HOST_EMISSION_INVALID", emission.placement_id)
    lane_marks_by_id = {mark.placement_id: mark for mark in marks if mark.lane_row_id is not None}
    completed = []
    for placed in text:
        host_id = placed.host_placement_id
        if host_id not in lane_marks_by_id:
            completed.append(placed)
            continue
        mark = lane_marks_by_id[host_id]
        emitted_id = emitted_mark_hosts.get(host_id)
        if (emitted_id is None or placed.slot_id != mark.slot_id
                or placed.paint_order <= mark.paint_order):
            raise LayoutError("E_LAYOUT_HOST_EMISSION_INVALID", placed.placement_id)
        completed.append(replace(placed, host_placement_id=emitted_id)
                         if emitted_id != host_id else placed)
    return tuple(completed)


FOREGROUND_TEXT_PAINT_ORDER = 300
ANNOTATION_PAINT_ORDER = 400
# Layout emits coordinates at micro-point precision.  Intermediate measurement
# APIs are float-based, so containment must not turn a sub-micro-point binary
# conversion residue into a user-visible overflow diagnostic.


def _contains_block_interval(*, container_start: Decimal, container_end: Decimal,
                             item_start: Decimal, item_end: Decimal) -> bool:
    """Apply the Layout coordinate tolerance to a physical containment test."""
    return item_start >= container_start - GEOMETRY_TOLERANCE and item_end <= container_end + GEOMETRY_TOLERANCE


def _completed_canvas(*, requested: Rect, rectangles: tuple[Rect, ...],
                      paths: tuple[tuple[tuple[float, float], ...], ...]) -> Rect:
    """Expand the requested canvas to contain Layout's completed geometry.

    A requested viewport is a minimum allocation.  This deliberately lives in
    the composition layer rather than in Scene or a renderer: every target
    receives the identical, already-completed extent.
    """
    inline_start, block_start = requested.inline, requested.block
    inline_end = requested.inline + requested.inline_size
    block_end = requested.block + requested.block_size
    for bounds in rectangles:
        inline_start = min(inline_start, bounds.inline)
        block_start = min(block_start, bounds.block)
        inline_end = max(inline_end, bounds.inline + bounds.inline_size)
        block_end = max(block_end, bounds.block + bounds.block_size)
    for points in paths:
        for inline, block in points:
            inline_start = min(inline_start, Decimal(str(inline)))
            block_start = min(block_start, Decimal(str(block)))
            inline_end = max(inline_end, Decimal(str(inline)))
            block_end = max(block_end, Decimal(str(block)))
    return Rect(inline_start, block_start,
                inline_end - inline_start, block_end - block_start)


def timeline_content_block_requirement(*, projection: Any, group_presentation: str,
                                       metric_values: dict[str, Decimal], role_geometries: dict[str, MarkGeometry] | None = None,
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
        text_line_block=text_line_block,
    )
    headers = 0
    previous = object()
    for row in rows:
        if row.group_id != previous:
            headers += 1 if row.group_id and group_presentation == "header" else 0
            previous = row.group_id
    return Decimal(str(geometry_sum(requirements))) + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0)


def compose_surface_layout(request: SurfaceLayoutRequest) -> SurfaceLayoutComposition:
    """Resolve slots, rows, groups, temporal scale, and mark tracks in Layout."""
    base = prepare_surface_base(request)
    request = base.request
    projection = request.projection
    layout_manifest = base.layout_manifest
    measured_sources = base.measured_sources
    metric_values = base.metric_values
    start, end = projection.window
    slots, by_source, table, timeline = base.slots, base.by_source, base.table, base.timeline
    review_rows, timeline_bounds = base.review_rows, base.timeline_bounds
    slot_ids = base.slot_ids
    text_slot = base.text_slot
    scale, rows, raw_rows = base.scale, base.rows, base.raw_rows
    groups, tracks = base.groups, base.tracks
    role_geometries, mark_block_size = base.role_geometries, base.mark_block_size
    table_bounds = base.table_bounds
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    def metric_for(typography_role: str) -> Any:
        return metric_for_role(request.theme_tokens, typography_role, request.font_metrics)
    body_size = float(request.theme_tokens.text_treatment("text").font_size)
    title_input = measured_sources.inputs.get("title")
    title_measurement = measured_sources.measurements.get("title")
    if title_measurement is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")
    title = title_input.lines[0] if title_input and title_input.lines else ""
    text = [place_text(placement_id="title", source_ref="title", content=title,
                       inline=float(by_source["title"].bounds.inline),
                       baseline_block=float(by_source["title"].bounds.block) + float(title_measurement.first_baseline or 0),
                       typography_role="heading", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                       collision_region="title", collision_domain=CollisionDomain("title", "content"),
                       source_content=title, available_inline_start=float(by_source["title"].bounds.inline),
                       available_inline_size=float(by_source["title"].bounds.inline_size))]
    footer_provisional_slots = slots
    slots, detail_panel_text, detail_panel_warnings, detail_visual_reservations = compose_detail_panel_blocks(
        slots=slots, request=request, requested_canvas=request.layout_manifest.viewport,
    )
    by_source = {slot.source_ref: slot for slot in slots}
    text.extend(detail_panel_text)
    table_batch = compose_table(base)
    column_placements = table_batch.columns
    text.extend(table_batch.text)
    group_batch = compose_group_presentation(
        request=request, rows=rows, review_rows=review_rows, groups=groups, body_size=body_size)
    text.extend(group_batch.text)
    shapes: list[ShapePlacement] = []
    shapes.extend(compose_row_group_backgrounds(
        base=base, rows=rows, groups=groups, theme_tokens=request.theme_tokens,
        row_decoration=request.surface_content.row_decoration,
        group_decoration=request.surface_content.group_decoration))
    axis_batch = compose_axis(request, base)
    axis = by_source["timeline-axis"]
    shapes.extend(axis_batch.shapes)
    text.extend(axis_batch.text)
    axis_tier_outcomes = list(axis_batch.tier_outcomes)
    axis_decisions = list(axis_batch.decisions)
    axis_label_targets = axis_batch.label_targets
    axis_band_targets = axis_batch.band_targets
    diagnostics = list(axis_batch.diagnostics)
    visible_label_overflows = list(axis_batch.visible_label_overflows)
    calendar_intervals = axis_batch.calendar_intervals
    contract = request.presentation_contract
    shapes.extend(compose_calendar_backgrounds(
        base=base, theme_tokens=request.theme_tokens, intervals=calendar_intervals))
    as_of_label: tuple[float, str] | None = None
    if contract.time.as_of is not None and start <= contract.time.as_of < end:
        x = _coordinate(contract.time.as_of, scale)
        shapes.append(ShapePlacement("as-of", "actual-set", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size))),
                                     paint_order=MARK_PAINT_ORDER_BASE))
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
    shapes.extend(mark_batch.progress_shapes)
    shapes.extend(mark_batch.summary_shapes)
    placement_decisions: list[PlacementDecision] = list(axis_decisions)
    member_label_context = SurfaceMemberLabelContext(
        request, projection, layout_manifest, by_source, text_slot, review_rows, tuple(rows), tuple(tracks),
        tuple(groups), scale, tuple(marks), timeline_bounds, as_of_label,
    )
    member_label_requests = build_member_label_requests(member_label_context)
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

    timeline_rect = LabelRect(*timeline_bounds)

    def place_label_phase(requests: tuple[LabelRequest, ...]) -> None:
        batch = place_member_labels(member_label_context, requests, surface_obstacles)
        text.extend(batch.text)
        shapes.extend(batch.shapes)
        candidate_icons.extend(batch.icons)
        visible_label_overflows.extend(batch.visible_overflows)
        placement_decisions.extend(batch.decisions)
        diagnostics.extend(batch.diagnostics)
        lane_label_suppressions.extend(batch.lane_label_suppressions)
        handled_candidate_visuals.update(batch.handled_visual_sources)

    place_label_phase(member_label_requests.pre_route)

    routes_context = SurfaceRoutesContext(request, projection, review_rows, tuple(rows), tuple(groups),
        tuple(marks), timeline_bounds, layout_manifest, metric_values, tuple(text), surface_obstacles)
    routes_batch = compose_surface_routes(routes_context)
    relations = list(routes_batch.relations)
    visible_route_fallbacks = list(routes_batch.visible_route_fallbacks)
    instance_anchors = dict(routes_batch.instance_anchors)
    instance_rows = dict(routes_batch.instance_rows)
    comparison_clusters = dict(routes_batch.comparison_clusters)
    diagnostics.extend(routes_batch.diagnostics)

    place_label_phase(member_label_requests.post_route)
    relation_labels = place_relation_labels(routes_context, routes_batch)
    text.extend(relation_labels.text)
    diagnostics.extend(relation_labels.diagnostics)
    visible_label_overflows.extend(relation_labels.visible_label_overflows)

    side_content_warnings: list[FitWarning] = []
    legend = by_source.get("legend")
    if legend:
        legend_batch = place_legend(SurfaceLegendContext(request, legend, metric_values, metric_for))
        marks.extend(legend_batch.marks)
        shapes.extend(legend_batch.shapes)
        relations.extend(legend_batch.relations)
        text.extend(legend_batch.text)
        side_content_warnings.extend(legend_batch.warnings)
        slots = tuple(legend_batch.slot if slot.source_ref == "legend" else slot for slot in slots)
    notes = by_source.get("notes")
    if notes:
        notes_slot, notes_text = place_notes(request, notes, body_size)
        text.extend(notes_text)
        slots = tuple(notes_slot if slot.source_ref == "notes" else slot for slot in slots)
    slots = complete_footer_band(provisional_slots=footer_provisional_slots, completed_slots=slots)
    by_source = {slot.source_ref: slot for slot in slots}
    summary_slot = by_source.get("summary")
    if summary_slot:
        text.extend(place_summary(request, summary_slot))

    annotation_slot = by_source.get("annotations")
    annotation_slot_id = annotation_slot.slot_id if annotation_slot is not None else ""
    if annotation_slot or request.surface_content.annotations:
        annotation_marks = _comparison_marks(projection)
        for index, annotation in enumerate(request.surface_content.annotations):
            presentation = annotation_presentation(annotation.purpose)
            annotation_id, content = annotation.annotation_id, annotation.content
            content = f"{annotation.number}. {content}" if annotation.number is not None else content
            annotation_visuals = measure_candidate_visuals(
                f"annotation-text:{annotation_id}", "annotation", request).visuals
            handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in annotation_visuals)
            annotation_leading = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "leading")
            annotation_trailing = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "trailing")
            resolved = resolve_annotation_anchor(annotation, annotation_marks)
            matching = [(review_row, row) for review_row, row in zip(review_rows, rows, strict=True)
                        if any(item.object_id == resolved.object_id for item in review_row.items)]
            anchor = annotation.anchor
            row_id, item_id = anchor.get("rowId"), anchor.get("itemId")
            if row_id is not None or item_id is not None:
                matching = [(review_row, row) for review_row, row in matching
                            if (row_id is None or review_row.row_id == row_id)
                            and (item_id is None or any(item.item_id == item_id and item.object_id == resolved.object_id for item in review_row.items))]
            folded_matches = [(folded, mark_by_id.get(f"{resolved.facet}:{_folded_instance_id(folded, folded.item)}"))
                              for folded in getattr(projection, "folded_points", ())
                              if folded.item.object_id == resolved.object_id]
            if row_id is not None or item_id is not None:
                folded_matches = [(folded, mark) for folded, mark in folded_matches
                                  if (row_id is None or row_id == f"group-header:{folded.group_id}:{folded.item.object_id}")
                                  and (item_id is None or item_id == folded.item.item_id)]
            if len(matching) + len(folded_matches) > 1:
                raise LayoutError("E_PRESENTATION_ROW_ANCHOR_AMBIGUOUS", f"/annotations/{index}/anchor")
            if matching:
                anchor_bounds = _annotation_anchor_bounds(resolved.mark, resolved.endpoint, matching[0][1], scale)
                selected_items = tuple(item for item in matching[0][0].items
                                       if item.object_id == resolved.object_id and (item_id is None or item.item_id == item_id))
                anchor_item = selected_items[0] if selected_items else None
                anchor_instance_id = ((f"{matching[0][0].row_id}:{anchor_item.item_id or anchor_item.object_id}"
                                       if projection.rows else anchor_item.object_id)
                                      if anchor_item is not None else "")
                anchor_host = mark_by_id.get(f"{resolved.facet}:{anchor_instance_id}")
            elif folded_matches and folded_matches[0][1] is not None:
                folded, mark = folded_matches[0]
                anchor_bounds = LabelRect(*_bounds(mark.bounds))
                selected_items = (folded.item,)
                anchor_host = mark
            else:
                raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
            as_of_side_constraint: tuple[float, str] | None = None
            if contract.time.as_of is not None and start <= contract.time.as_of < end:
                as_of_x = _coordinate(contract.time.as_of, scale)
                as_of_side_constraint = (as_of_x, "start" if anchor_bounds.x < as_of_x else "end")
            annotation_text_role = semantic_binding(presentation.text_semantic_id).theme_role
            annotation_treatment = request.theme_tokens.text_treatment(annotation_text_role)
            annotation_metrics = metric_for(annotation_text_role)
            size, line_height = float(annotation_treatment.font_size), float(annotation_treatment.line_height)
            if annotation_slot is not None:
                text_available = max(1.0, float(annotation_slot.bounds.inline_size) - annotation_leading - annotation_trailing)
            else:
                # A plot/content-only candidate list declares its own text
                # width bound (#466); an annotation with no annotations slot
                # must declare at least one bounded nearest-free/adjacent
                # candidate.
                declared_max_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                                       if candidate.search.max_inline_em is not None), default=None)
                if declared_max_em is None:
                    raise LayoutError("E_LAYOUT_ANNOTATION_WIDTH_UNBOUNDED", f"/annotations/{index}")
                text_available = max(1.0, declared_max_em * size - annotation_leading - annotation_trailing)
            text_width = min(text_available, max(size * 4, measure_text_width(
                content, font_size=size, font_metrics=annotation_metrics,
                letter_spacing=float(annotation_treatment.letter_spacing), text_transform=annotation_treatment.transform)))
            width = annotation_leading + text_width + annotation_trailing
            annotation_lines = (content,)
            annotation_search_count = 0
            tail_box_position_limit = tail_box_positions_examined = 0
            tail_route_state_limit = tail_route_states_examined = 0
            tail_route_search_exhausted = False
            tail_topology: str | None = None
            routed_tail_tip: tuple[float, float] | None = None
            selected_leader: tuple[ConnectorEgress, AnnotationRouteTrial,
                                   tuple[tuple[float, float], ...],
                                   tuple[tuple[float, float], ...]] | None = None

            def trial_leader(candidate_box: Any, rung: str
                             ) -> tuple[ConnectorEgress, AnnotationRouteTrial,
                                        tuple[tuple[float, float], ...],
                                        tuple[tuple[float, float], ...]] | None:
                nonlocal annotation_search_count
                if not candidate_box.leader_required or presentation.leader_semantic_id is None:
                    return None
                if anchor_host is None:
                    raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
                candidate_bounds = candidate_box.placement.bounds
                target = nearest_box_port(candidate_bounds,
                                          (anchor_bounds.x + anchor_bounds.width / 2,
                                           anchor_bounds.y + anchor_bounds.height / 2))
                anchor_instance = anchor_host.placement_id.split(":", 1)[1]
                anchor_row = instance_rows.get(anchor_instance)
                source_candidates = connector_egress_candidates(
                    anchor_host, resolved.endpoint, target,
                    comparison_clusters.get((anchor_host.source_ref, anchor_row), (anchor_host,)))
                viewport = request.layout_manifest.viewport
                content_extent = (float(viewport.inline), float(viewport.block),
                                  max(float(viewport.inline + viewport.inline_size), candidate_bounds.right),
                                  max(float(viewport.block + viewport.block_size), candidate_bounds.bottom))
                route_bounds = local_route_bounds(
                    _bounds(anchor_host.bounds),
                    (candidate_bounds.x, candidate_bounds.y, candidate_bounds.width, candidate_bounds.height),
                    target, content_extent)
                connector_stroke_width = float(request.theme_tokens.number(
                    semantic_binding(presentation.leader_semantic_id).theme_role, "strokeWidth"))
                route_specs: list[tuple[ConnectorEgress, tuple[tuple[float, float], ...], tuple[str, ...]]] = []
                for source_egress in source_candidates:
                    source_port_id = f"port:{anchor_host.placement_id}:{source_egress.side}"
                    known_ports = coincident_endpoint_port_ids(
                        surface_obstacles, source_egress.exposed_port, source_egress.host_ids)
                    known_ports = tuple(dict.fromkeys((*known_ports, *coincident_endpoint_port_ids(
                        surface_obstacles, source_egress.semantic_port, source_egress.host_ids))))
                    if surface_obstacles.has(source_port_id) and source_port_id not in known_ports:
                        known_ports = (*known_ports, source_port_id)
                    if source_egress.corridor and surface_obstacles.egress_collisions(
                            ObstacleSegment(*source_egress.corridor), host_ids=source_egress.host_ids,
                            port_ids=known_ports):
                        continue
                    base_prefix = (source_egress.corridor if source_egress.corridor
                                   else (source_egress.semantic_port,))
                    # Clear the entire possible bridge gap before turning
                    # back across a dependency from the same endpoint.
                    fanout_deltas = ((6.0, 0.0), (-6.0, 0.0), (0.0, 6.0), (0.0, -6.0))
                    prefixes = (base_prefix, *(tuple((*base_prefix,
                                                      (source_egress.exposed_port[0] + dx,
                                                       source_egress.exposed_port[1] + dy)))
                                                for dx, dy in fanout_deltas))
                    for prefix in prefixes:
                        if len(prefix) > len(base_prefix):
                            stub = ObstacleSegment(source_egress.exposed_port, prefix[-1])
                            if (surface_obstacles.egress_collisions(
                                    stub, host_ids=source_egress.host_ids, port_ids=known_ports)
                                    or any(item.placement_id in source_egress.host_ids
                                           for item in surface_obstacles.collisions(stub, classes=("mark",)))):
                                continue
                        route_specs.append((source_egress, tuple(prefix), known_ports))
                # Probe every finite sparse endpoint before spending the
                # dense-grid budget on any one poor endpoint.
                for dense_search, candidates in ((False, route_specs), (True, route_specs[:2])):
                    for source_egress, prefix, known_ports in candidates:
                        annotation_search_count += 1
                        trial = route_annotation_candidate(
                            prefix[-1], target, surface_obstacles,
                            bounds=route_bounds, port_ids=known_ports,
                            max_bends=layout_manifest.annotation_max_bends,
                            max_detour_ratio=layout_manifest.annotation_max_detour_ratio,
                            allow_bridge=rung == "rail", dense=dense_search,
                            connector_stroke_width=connector_stroke_width)
                        if trial is None:
                            continue
                        full_points = (*prefix[:-1], *trial.points)
                        if relation_route_quality(full_points, max_bends=layout_manifest.annotation_max_bends,
                                                  max_detour_ratio=layout_manifest.annotation_max_detour_ratio):
                            return source_egress, trial, tuple(full_points), tuple(prefix)
                return None

            tail_tip: tuple[float, float] | None = None
            container = None
            content_top = content_right = content_bottom = content_left = 0.0
            try:
                if annotation.purpose in {"callout", "highlight", "note", "explanatory-arrow"}:
                    intent = selected_items[0].presentation if selected_items else None
                    preferred = ((intent or {}).get("callout") or {}).get("placement") if isinstance(intent, dict) else None
                    wrap = ((intent or {}).get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid"
                    # A declared candidate's maxInlineEm is a text-width bound
                    # for a plot/content search (#466): it forces wrapping so
                    # a long note becomes a narrow, tall box rather than one
                    # too wide to fit any free lattice position.
                    plot_wrap_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                                        if candidate.search.max_inline_em is not None), default=None)
                    wrap_available = float(plot_wrap_em) * size if plot_wrap_em is not None else text_available
                    if plot_wrap_em is not None:
                        wrap = "allow"
                    annotation_lines = (wrap_text(content, available_inline=wrap_available, font_size=size, font_metrics=annotation_metrics,
                                                  letter_spacing=float(annotation_treatment.letter_spacing),
                                                  text_transform=annotation_treatment.transform)
                                        if wrap == "allow" else (content,))
                    text_width = max(measure_text_width(line, font_size=size, font_metrics=annotation_metrics,
                                                        letter_spacing=float(annotation_treatment.letter_spacing),
                                                        text_transform=annotation_treatment.transform)
                                     for line in annotation_lines)
                    annotation_box_role = semantic_binding(presentation.box_semantic_id).theme_role
                    container = request.theme_tokens.annotation_container(annotation_box_role)
                    # An image-backed container (#465) declares a content
                    # inset: Layout measures text into that smaller box, then
                    # expands it by the inset to the paint box the search and
                    # collision below actually use -- the box a rectangle or
                    # balloon container already uses today, unchanged.
                    content_top = content_right = content_bottom = content_left = 0.0
                    if container is not None and container.outline == "image":
                        content_top, content_right, content_bottom, content_left = (
                            float(value) * size for value in container.content_insets_em)
                    annotation_size = (annotation_leading + text_width + annotation_trailing + content_left + content_right,
                                       size * line_height * len(annotation_lines) + content_top + content_bottom)
                    candidates, ladder = candidate_order(annotation.candidates, annotation.purpose,
                                                          annotation.fallback_ladder, preferred)
                    box, selected_rung, tail_tip = None, None, None
                    for candidate in candidates:
                        rung = candidate.candidate_id
                        if candidate.search.kind == "row-aligned":
                            candidate_boxes = annotation_rail_candidates(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles)
                            for candidate_box in candidate_boxes:
                                annotation_search_count += 1
                                leader_trial = trial_leader(candidate_box, rung)
                                if candidate_box.leader_required and presentation.leader_semantic_id is not None and leader_trial is None:
                                    continue
                                box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                                break
                        elif candidate.search.kind == "nearest-free":
                            region_bounds = LabelRect(*_bounds(timeline.bounds))
                            host_id = anchor_host.placement_id if anchor_host is not None else None
                            if candidate.connector.kind == "tail":
                                if container is None or container.outline != "balloon":
                                    raise LayoutError("E_LAYOUT_ANNOTATION_TAIL_REQUIRES_BALLOON", f"/annotations/{index}")
                                corner_radius, tail_base = float(container.corner_radius) * size, float(container.tail_base) * size
                                free_box, trial_tip, trials = nearest_free_tail_box(
                                    region=region_bounds, anchor=anchor_bounds, box_size=annotation_size,
                                    max_positions=candidate.search.max_positions, obstacles=surface_obstacles,
                                    obstacle_classes=candidate.obstacles.classes, corner_radius=corner_radius,
                                    tail_base=tail_base, host_id=host_id, side_of_as_of=as_of_side_constraint)
                                annotation_search_count += trials
                                tail_box_position_limit = candidate.search.max_positions
                                tail_box_positions_examined = trials
                                if free_box is not None:
                                    box = AnnotationBox(resolved, LabelPlacement(rung, free_box, False), False)
                                    selected_rung, tail_tip = rung, trial_tip
                                    tail_topology = "direct-tail"
                                elif anchor_host is not None:
                                    anchor_instance = anchor_host.placement_id.split(":", 1)[1]
                                    anchor_row = instance_rows.get(anchor_instance)
                                    viewport = request.layout_manifest.viewport
                                    routed = nearest_free_routed_tail_box(
                                        region=region_bounds, anchor=anchor_host,
                                        endpoint=resolved.endpoint,
                                        siblings=comparison_clusters.get(
                                            (anchor_host.source_ref, anchor_row), (anchor_host,)),
                                        box_size=annotation_size,
                                        max_positions=candidate.search.max_positions,
                                        obstacles=surface_obstacles,
                                        obstacle_classes=candidate.obstacles.classes,
                                        corner_radius=corner_radius, tail_base=tail_base,
                                        content_bounds=(
                                            float(viewport.inline), float(viewport.block),
                                            float(viewport.inline + viewport.inline_size),
                                            float(viewport.block + viewport.block_size)),
                                        host_id=host_id, side_of_as_of=as_of_side_constraint,
                                        max_bends=layout_manifest.annotation_max_bends,
                                        max_detour_ratio=layout_manifest.annotation_max_detour_ratio)
                                    annotation_search_count += routed.box_trials + routed.route_states
                                    tail_box_positions_examined = max(trials, routed.box_trials)
                                    tail_route_state_limit = 1024
                                    tail_route_states_examined = routed.route_states
                                    tail_route_search_exhausted = routed.exhausted and routed.box is None
                                    if routed.exhausted and routed.box is None:
                                        diagnostics.append(
                                            f"W_LAYOUT_ANNOTATION_ROUTE_SEARCH_EXHAUSTED:{annotation_id}:{rung}")
                                    if routed.box is not None and routed.egress is not None and routed.route is not None:
                                        box = AnnotationBox(resolved, LabelPlacement(rung, routed.box, False), False)
                                        selected_rung, tail_tip = rung, routed.tip
                                        routed_tail_tip = routed.tip
                                        tail_topology = "routed-tail"
                                        prefix = (routed.egress.corridor if routed.egress.corridor
                                                  else (routed.egress.exposed_port,))
                                        selected_leader = (routed.egress, routed.route,
                                                           routed.full_points, prefix)
                            else:
                                anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                                 anchor_bounds.y + anchor_bounds.height / 2)
                                free_box, trials = nearest_free_box(
                                    region=region_bounds, anchor_center=anchor_center, box_size=annotation_size,
                                    max_positions=candidate.search.max_positions, obstacles=surface_obstacles,
                                    obstacle_classes=candidate.obstacles.classes, host_id=host_id,
                                    side_of_as_of=as_of_side_constraint)
                                annotation_search_count += trials
                                if free_box is not None:
                                    leader_required = candidate.connector.kind == "leader"
                                    candidate_box = AnnotationBox(resolved, LabelPlacement(rung, free_box, False), leader_required)
                                    leader_trial = trial_leader(candidate_box, rung) if leader_required else None
                                    if not (leader_required and presentation.leader_semantic_id is not None and leader_trial is None):
                                        box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                        else:
                            candidate_box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="clip-optional", required=False)
                            candidate_boxes = (candidate_box,) if candidate_box is not None else ()
                            for candidate_box in candidate_boxes:
                                annotation_search_count += 1
                                leader_trial = trial_leader(candidate_box, rung)
                                if candidate_box.leader_required and presentation.leader_semantic_id is not None and leader_trial is None:
                                    continue
                                box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                                break
                        if box is not None:
                            break
                    if (box is not None and annotation.candidates
                            and selected_rung != candidates[0].candidate_id):
                        diagnostics.append(
                            f"W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:{annotation_id}:{selected_rung}")
                    if box is None:
                        if "suppress" in ladder:
                            placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                         tuple(ladder), "suppress", "suppressed",
                                                                         search_count=annotation_search_count))
                            diagnostics.append(f"W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:{annotation_id}")
                            continue
                        # A normal annotation is never silently suppressed or
                        # rejected.  Complete its first declared placement in
                        # visible-overflow mode after the explicit fit ladder
                        # has been exhausted.
                        selected_rung = next(rung for rung in ladder if rung != "suppress")
                        first_candidate = next((item for item in candidates if item.candidate_id == selected_rung), None)
                        if selected_rung == "rail":
                            box = place_annotation_rail(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="visible-overflow", required=True)
                        elif first_candidate is not None and first_candidate.search.kind == "nearest-free":
                            # #449 never refuses: complete the first declared
                            # candidate's own region at its nearest lattice
                            # position, visibly overflowing any obstacle.
                            region_bounds = LabelRect(*_bounds(timeline.bounds))
                            anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                             anchor_bounds.y + anchor_bounds.height / 2)
                            width, height = annotation_size
                            forced = LabelRect(min(max(anchor_center[0] - width / 2, region_bounds.x),
                                                   region_bounds.right - width),
                                               min(max(anchor_center[1] - height / 2, region_bounds.y),
                                                   region_bounds.bottom - height), width, height)
                            box = AnnotationBox(resolved, LabelPlacement(selected_rung, forced, True), False)
                        else:
                            box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(selected_rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="visible-overflow", required=True)
                        if box is None:  # Defensive: visible-overflow is a total Layout policy.
                            raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/annotations/{index}")
                    placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                 tuple(ladder), selected_rung, "placed",
                                                                 search_count=annotation_search_count,
                                                                 selected_topology=(tail_topology or
                                                                                    (selected_leader[1].topology
                                                                                     if selected_leader else None)),
                                                                 crossing_ids=(selected_leader[1].crossing_ids
                                                                               if selected_leader else ()),
                                                                 box_position_limit=tail_box_position_limit,
                                                                 box_positions_examined=tail_box_positions_examined,
                                                                 route_state_limit=tail_route_state_limit,
                                                                 route_states_examined=tail_route_states_examined,
                                                                 route_search_exhausted=tail_route_search_exhausted))
                else:
                    box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=(width, size * line_height),
                                                 candidate_sides=(annotation.side,),
                                                 viewport=LabelRect(*_bounds(annotation_slot.bounds)), obstacles=surface_obstacles,
                                                 overflow=annotation_slot.overflow, required=annotation_slot.priority == "required")
            except ValueError as error:
                raise LayoutError(str(error), f"/annotations/{index}") from error
            if box is None:
                continue
            bounds = box.placement.bounds
            annotation_bounds = Rect(Decimal(str(bounds.x)), Decimal(str(bounds.y)),
                                     Decimal(str(bounds.width)), Decimal(str(bounds.height)))
            if tail_tip is not None:
                container = request.theme_tokens.annotation_container(
                    semantic_binding(presentation.box_semantic_id).theme_role)
                corner_radius, tail_base = float(container.corner_radius) * size, float(container.tail_base) * size
                outline = balloon_outline(bounds, tail_tip, corner_radius=corner_radius, tail_base=tail_base)
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Balloon",
                                             annotation_bounds, path_commands=outline,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER))
            elif container is not None and container.outline == "image":
                icon = request.icon_assets.get(container.image_ref)
                if icon is None or icon.kind != "raster":
                    raise LayoutError("E_LAYOUT_ANNOTATION_IMAGE_UNRESOLVED", f"/annotations/{index}")
                slice_insets_px = tuple(float(value) * size for value in container.slice_insets_em)
                tiles = image_slice_tiles((bounds.x, bounds.y, bounds.width, bounds.height),
                                          viewport=icon.viewport, slice_insets=slice_insets_px)
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                             annotation_bounds,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER,
                                             image_fill=LayoutImageFill(icon.content_identity, icon.viewport,
                                                                        icon.payload, tiles)))
            else:
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                             annotation_bounds,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER))
            register_rect(f"annotation-box:{annotation_id}", "annotation-box", "annotations", annotation_bounds)
            annotation_text_slot = "annotations" if annotation_slot is not None else timeline.slot_id
            placed_annotation = place_text(placement_id=f"annotation-text:{annotation_id}", source_ref=annotation_id, content=content,
                                           inline=bounds.x + annotation_leading + content_left,
                                           baseline_block=bounds.y + content_top + size, typography_role=annotation_text_role,
                                           theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                           collision_region="annotations", collision_domain=CollisionDomain(annotation_text_slot, "content"),
                                           lines=annotation_lines, semantic_id=presentation.text_semantic_id,
                                           annotation=presentation)
            placed_annotation = replace(placed_annotation, paint_order=ANNOTATION_PAINT_ORDER + 1)
            text.append(placed_annotation)
            register_rect(placed_annotation.placement_id, "text", "annotations", placed_annotation.bounds)
            if box.placement.visible_overflow:
                overflow_viewport = (LabelRect(*_bounds(annotation_slot.bounds)) if annotation_slot is not None
                                     else LabelRect(*_bounds(timeline.bounds)))
                visible_label_overflows.append((placed_annotation, overflow_viewport))
            if annotation_visuals:
                if not hasattr(annotation_metrics, "cap_height_at"):
                    raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in annotation_visuals))
                cap_height = float(annotation_metrics.cap_height_at(size))
                for visual, icon, icon_width, gap in annotation_visuals:
                    inline = (bounds.x if visual.side == "leading"
                              else bounds.x + annotation_leading + text_width + annotation_trailing - gap - icon_width)
                    icon_bounds = Rect(Decimal(str(inline)), Decimal(str(placed_annotation.baseline[1] - cap_height
                                                                          + (cap_height - size) / 2)),
                                       Decimal(str(icon_width)), Decimal(str(size)))
                    candidate_icons.append(IconPlacement(f"visual:{placed_annotation.placement_id}:{visual.side}",
                                                         annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                         icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                         visual.decorative, icon_bounds, "labelVisual",
                                                         icon_width / icon.viewport[0], annotation_slot_id,
                                                         paint_order=placed_annotation.paint_order))
            if annotation.number is not None:
                note_index_visuals = measure_candidate_visuals(
                    f"note-index:{annotation_id}", "annotation", request).visuals
                handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in note_index_visuals)
                note_index_leading = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                  if visual.side == "leading")
                note_index_trailing = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                   if visual.side == "trailing")
                note_index_content = str(annotation.number)
                note_index_width = measure_text_width(note_index_content, font_size=size, font_metrics=annotation_metrics,
                                                      letter_spacing=float(annotation_treatment.letter_spacing),
                                                      text_transform=annotation_treatment.transform)
                note_index_size = (note_index_leading + note_index_width + note_index_trailing, size * line_height)
                note_index = place_label(
                    anchor_bounds, note_index_size, ("end", "start", "above", "below"),
                    bounds=LabelRect(*timeline_bounds), obstacles=surface_obstacles,
                    gap=max(1.0, size * 0.25), required=False, overflow="suppress",
                )
                if note_index is None:
                    diagnostics.append(f"W_LAYOUT_NOTE_INDEX_SUPPRESSED:{annotation_id}")
                else:
                    note_index_inline = note_index.bounds.x
                    note_index_text = place_text(placement_id=f"note-index:{annotation_id}", source_ref=annotation_id,
                                                 content=note_index_content, inline=note_index_inline + note_index_leading,
                                                 baseline_block=note_index.bounds.y + size, typography_role="annotation",
                                                 theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                                 collision_region="annotations",
                                                 collision_domain=CollisionDomain("timeline", "overlay"),
                                                 semantic_id="noteIndex")
                    if anchor_host is not None:
                        note_index_text = replace(note_index_text, host_placement_id=anchor_host.placement_id,
                                                  paint_order=max(HOSTED_TEXT_PAINT_ORDER, anchor_host.paint_order + 1))
                    text.append(note_index_text)
                    register_rect(note_index_text.placement_id, "text", "timeline", note_index_text.bounds)
                    if note_index_visuals:
                        if not hasattr(annotation_metrics, "cap_height_at"):
                            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in note_index_visuals))
                        cap_height = float(annotation_metrics.cap_height_at(size))
                        for visual, icon, icon_width, gap in note_index_visuals:
                            inline = (note_index.bounds.x if visual.side == "leading"
                                      else note_index.bounds.x + note_index_leading + note_index_width + note_index_trailing - gap - icon_width)
                            icon_bounds = Rect(Decimal(str(inline)), Decimal(str(note_index_text.baseline[1] - cap_height
                                                                                  + (cap_height - size) / 2)),
                                               Decimal(str(icon_width)), Decimal(str(size)))
                            candidate_icons.append(IconPlacement(f"visual:note-index:{annotation_id}:{visual.side}",
                                                                 annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                                 icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                                 visual.decorative, icon_bounds, "labelVisual",
                                                                 icon_width / icon.viewport[0], annotation_slot_id,
                                                                 paint_order=note_index_text.paint_order))
            if (box.leader_required or routed_tail_tip is not None) and presentation.leader_semantic_id is not None:
                target = (routed_tail_tip if routed_tail_tip is not None else nearest_box_port(
                    bounds, (anchor_bounds.x + anchor_bounds.width / 2,
                             anchor_bounds.y + anchor_bounds.height / 2)))
                if anchor_host is None:
                    raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
                target_port_obstacle_id = f"port:annotation:{annotation_id}:target"
                leader_fallback = selected_leader is None
                if leader_fallback:
                    anchor_instance_id = anchor_host.placement_id.split(":", 1)[1]
                    anchor_row_id = instance_rows.get(anchor_instance_id)
                    selected_source = connector_egress_candidates(
                        anchor_host, resolved.endpoint, target,
                        comparison_clusters.get((anchor_host.source_ref, anchor_row_id), (anchor_host,)))[0]
                    points = (selected_source.semantic_port, target)
                    path_commands = ()
                    visible_route_segments = tuple(zip(points, points[1:]))
                else:
                    selected_source, route_trial, points, prefix = selected_leader
                    path_commands = ((PathCommand("move", (prefix[0],)),
                                      *(PathCommand("line", (point,)) for point in prefix[1:]),
                                      *route_trial.commands[1:])
                                     if route_trial.commands else ())
                    visible_route_segments = tuple(zip(prefix, prefix[1:])) + visible_segments(route_trial)
                source_side = selected_source.side
                source_port_obstacle_id = f"port:{anchor_host.placement_id}:{source_side}"
                if not surface_obstacles.has(source_port_obstacle_id):
                    register_port(source_port_obstacle_id, selected_source.exposed_port, "timeline")
                if not surface_obstacles.has(target_port_obstacle_id):
                    register_port(target_port_obstacle_id, target, "annotations")
                leader_semantic_id = presentation.leader_semantic_id
                leader_stroke_width = float(request.theme_tokens.number(
                    semantic_binding(leader_semantic_id).theme_role, "strokeWidth"))
                marker_end = (marker_geometry(request.theme_tokens.marker(semantic_binding(leader_semantic_id).theme_role))
                              if presentation.purpose == "explanatory-arrow" else None)
                placed_leader = RelationPlacement(f"annotation-leader:{annotation_id}",
                                                  f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}:{source_side}",
                                                  f"annotation-box:{annotation_id}", tuple(points),
                                                  semantic_id=leader_semantic_id, marker_end=marker_end,
                                                  path_commands=path_commands,
                                                  annotation=presentation, source_ref=annotation_id)
                relations.append(placed_leader)
                for segment_index, (segment_start, segment_end) in enumerate(visible_route_segments):
                    if segment_start != segment_end:
                        surface_obstacles.add(SurfaceObstacle(
                            f"{placed_leader.relation_id}:segment:{segment_index}", "leader-route", "annotations",
                            ObstacleSegment(segment_start, segment_end, leader_stroke_width)))
                if leader_fallback:
                    visible_route_fallbacks.append(placed_leader)
    text = [replace(item, slot_id=text_slot(item)) for item in text]
    text_visuals = place_text_visuals(tuple(text), request,
        handled_sources=handled_candidate_visuals, axis_label_targets=axis_label_targets,
        pre_reserved_placements=detail_visual_reservations)
    text, icons = list(text_visuals.text), list(text_visuals.icons)
    text_visual_warnings = list(text_visuals.warnings)
    validate_detail_panel_placement(text, slots)
    icons.extend(candidate_icons)
    icons.extend(place_mark_visuals(tuple(marks), request).icons)

    # Slot ownership is completed here with the rest of Layout geometry.  Scene
    # projection receives the relation verbatim and must never reconstruct it
    # from primitive purpose, identity, or containment.
    def shape_slot(item: Any) -> str:
        if item.semantic_id in axis_band_semantic_ids():
            return axis.slot_id
        if item.semantic_id in BACKGROUND_SEMANTIC_IDS:
            return item.slot_id
        if item.placement_id.startswith("legend-swatch:"):
            return by_source["legend"].slot_id
        if item.placement_id.startswith("summary-bar:"):
            return by_source.get("summary", timeline).slot_id
        if item.placement_id.startswith("annotation-box:"):
            return by_source.get("annotations", timeline).slot_id
        if item.source_ref == "timeline-axis":
            return axis.slot_id
        return timeline.slot_id
    shapes = [replace(item, slot_id=shape_slot(item)) for item in shapes]
    icons.extend(place_axis_band_visuals(tuple(shapes), request, targets=axis_band_targets).icons)
    relations = [replace(item, slot_id=(by_source.get("annotations", timeline).slot_id
                                        if item.relation_id.startswith("annotation-leader:")
                                        else by_source["legend"].slot_id
                                        if item.relation_id.startswith("legend-swatch:")
                                        else timeline.slot_id)) for item in relations]
    validate_background_shapes(shapes, request.theme_tokens)

    # Complete the observable fallback records at the same point as completed
    # geometry.  Neither Scene nor an adapter gets a policy question to answer.
    fit_warnings: list[FitWarning] = [*layout_manifest.fit_warnings, *detail_panel_warnings,
                                      *side_content_warnings, *text_visual_warnings]
    warned_placement_ids: set[str] = set()
    timeline_end = timeline.bounds.block + timeline.bounds.block_size
    header_start = Decimal(str(table_bounds[1]))
    header_end = Decimal(str(timeline_bounds[1]))
    row_by_id = {row.row_id: row for row in rows}
    table_end = table.bounds.inline + table.bounds.inline_size
    for column in column_placements:
        if column.bounds.inline + column.bounds.inline_size > table_end + GEOMETRY_TOLERANCE:
            placement_id = f"column:{column.column_id}"
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", placement_id, "view:tableColumns",
                "table-text", "visible-overflow", float(column.bounds.inline_size),
                float(column.bounds.block_size), max(0.0, float(table_end - column.bounds.inline)),
                float(column.bounds.block_size),
            ))
            warned_placement_ids.add(placement_id)
    for item in text:
        if (not item.placement_id.startswith(("column:", "cell:")) or item.overflow != "fit"
                or item.placement_id in warned_placement_ids):
            continue
        inline_overflow = (item.available_inline_size is not None
                           and item.bounds.inline_size > Decimal(str(item.available_inline_size)) + GEOMETRY_TOLERANCE)
        if item.placement_id.startswith("column:"):
            block_available = max(0.0, float(header_end - header_start))
            block_overflow = not _contains_block_interval(
                container_start=header_start, container_end=header_end,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        else:
            object_id = item.placement_id.split(":", 2)[1]
            row = row_by_id.get(object_id) or next((candidate for candidate in rows if candidate.object_id == object_id), None)
            block_available = float(row.bounds.block_size) if row is not None else 0.0
            block_overflow = row is not None and not _contains_block_interval(
                container_start=row.bounds.block, container_end=row.bounds.block + row.bounds.block_size,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        if inline_overflow or block_overflow:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id, item.source_ref,
                "table-text", "visible-overflow", float(item.bounds.inline_size),
                float(item.bounds.block_size), float(item.available_inline_size or 0), block_available,
            ))
    for row in rows:
        if row.bounds.block + row.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_ROW_DENSITY", f"row:{row.row_id}", row.object_id,
                "review-row-density", "visible-overflow", float(row.bounds.inline_size),
                float(row.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - row.bounds.block)),
            ))
    for mark in marks:
        # A legend swatch drawn as the real point-shaped primitive (#427) lives in
        # the legend slot below the plot by construction, not in the timeline; it
        # is never meant to fit inside `timeline_end` and checking it here always
        # reports a spurious overflow with `available` clamped to 0. The legend's
        # own row-height accounting is the swatch's actual containment check.
        if mark.placement_id.startswith("legend-swatch:"):
            continue
        if mark.bounds.block + mark.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_MARK_OVERFLOW", mark.placement_id, mark.source_ref,
                "mark-containment", "visible-overflow", float(mark.bounds.inline_size),
                float(mark.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - mark.bounds.block)),
            ))
    for item, available in visible_label_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_LABEL_OVERFLOW", item.placement_id, item.source_ref,
            "label-collision", "visible-overflow", float(item.bounds.inline_size),
            float(item.bounds.block_size), available.width, available.height,
        ))
    for relation in visible_route_fallbacks:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_ROUTE_FALLBACK", relation.relation_id, relation.source_ref,
            "relation-route", "direct-path", 0.0, 0.0,
            float(timeline.bounds.inline_size), float(timeline.bounds.block_size),
        ))
    for group_id, header, available_block in visible_group_header_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_GROUP_HEADER_OVERFLOW", f"group-header:{group_id}", group_id,
            "group-header-density", "visible-overflow", float(header.inline_size),
            float(header.block_size), float(header.inline_size), available_block,
        ))
    canvas = _completed_canvas(
        requested=request.layout_manifest.viewport,
        rectangles=(tuple(slot.bounds for slot in slots) + tuple(row.bounds for row in rows)
                    + tuple(column.bounds for column in column_placements)
                    + tuple(group.content_bounds for group in groups)
                    + tuple(group.header_bounds for group in groups if group.header_bounds is not None)
                    + tuple(item.bounds for item in text) + tuple(item.bounds for item in marks)
                    + tuple(item.bounds for item in shapes) + tuple(item.bounds for item in icons)),
        paths=tuple(item.points for item in relations),
    )
    suppressed_plot_labels = sum(item.semantic_id == "memberLabel" and item.overflow == "suppressed" for item in text)
    completed_icons = tuple(replace(icon, completed_paths=complete_icon_paths(
        icon.payload, (float(icon.bounds.inline), float(icon.bounds.block),
                       float(icon.bounds.inline_size), float(icon.bounds.block_size)), icon.stroke_scale))
        if icon.kind == "vector" else icon for icon in icons)
    if projection.lane_membership is not None:
        lane_mark_blocks: dict[str, Decimal] = {}
        for mark in marks:
            if mark.lane_row_id is not None:
                lane_mark_blocks[mark.lane_row_id] = min(
                    lane_mark_blocks.get(mark.lane_row_id, mark.bounds.block), mark.bounds.block)
        if any(row.row_id not in lane_mark_blocks for row in rows):
            raise LayoutError("E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "/layout/rows")
        try:
            rows = tuple(replace(row, lane_mark_band_block=lane_mark_blocks[row.row_id]) for row in rows)
        except ValueError as error:
            raise LayoutError("E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "/layout/rows",
                              "completed lane mark band falls outside its row bounds") from error
    lane_emissions = _lane_emissions(projection, tuple(review_rows), marks, text,
                                     shapes, completed_icons, request.theme_tokens)
    # Abstract mark IDs remain Layout anchors; hosted text needs the actual
    # Scene primitive ID completed by this typed lane-emission closure.
    completed_text = _complete_hosted_text_identity(tuple(text), tuple(marks), lane_emissions)
    patterns = _complete_catalog_patterns(tuple(marks), tuple(shapes), request.theme_tokens)
    placement = SurfacePlacement(text=completed_text, slots=slots, rows=rows, columns=column_placements,
                                 groups=tuple(groups), scale=scale,
                                 marks=tuple(marks), shapes=tuple(shapes), relations=tuple(relations),
                                 decisions=tuple(placement_decisions),
                                 axis_tier_outcomes=tuple(axis_tier_outcomes),
                                 diagnostics=tuple(diagnostics), icons=completed_icons,
                                 canvas_bounds=canvas, fit_warnings=tuple(fit_warnings),
                                 info_diagnostics=((SuppressedPlotLabels("table-timeline", suppressed_plot_labels),)
                                                   if suppressed_plot_labels else ()),
                                 lane_emissions=lane_emissions, patterns=patterns,
                                 lane_label_suppressions=tuple(lane_label_suppressions))
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks, tuple(mark_absences))


_RECT_PATTERN_THEME_ROLES = {
    "missing-actual": "missing-actual",
    "progressFill": "progress-fill",
    "summaryBar": "summary-bar",
    "annotationHighlightBox": "annotation-highlight-box",
    "axisBandDecoration": "axis-band-decoration",
    "axisBandDecoration2": "axis-band-decoration2",
    "asOfLabelChip": "as-of-label-chip",
    "memberLabelChip": "member-label-chip",
    "finishDeltaChip": "finish-delta-chip",
}


def _complete_catalog_patterns(marks: tuple[MarkPlacement, ...],
                               shapes: tuple[ShapePlacement, ...],
                               theme_tokens: Any) -> tuple[PatternedPlacement, ...]:
    """Attach only allowlisted catalogue patterns to completed Rect placements."""
    optional_pattern = getattr(theme_tokens, "optional_pattern", None)
    if not callable(optional_pattern):
        return ()
    result: list[PatternedPlacement] = []
    for shape in shapes:
        role = _RECT_PATTERN_THEME_ROLES.get(shape.semantic_id)
        if shape.kind != "Rect" or role is None:
            continue
        pattern = optional_pattern(role)
        if isinstance(pattern, Mapping) and pattern.get("kind") == "catalog":
            result.append(PatternedPlacement(
                shape.placement_id,
                complete_pattern_placement(pattern, shape.bounds, shape.corner_radius),
            ))
    for mark in marks:
        role = _RECT_PATTERN_THEME_ROLES.get(mark.semantic_id)
        if role is None or mark.mark_shape != "span":
            continue
        pattern = optional_pattern(role)
        if isinstance(pattern, Mapping) and pattern.get("kind") == "catalog":
            result.append(PatternedPlacement(
                mark.placement_id,
                complete_pattern_placement(pattern, mark.bounds, mark.corner_radius),
            ))
    return tuple(result)


def _comparison_marks(projection: Any) -> tuple[ComparisonMark, ...]:
    marks: list[ComparisonMark] = []
    for item in projection.items:
        for facet, value in (("planned", item.planned), ("actual", item.actual)):
            if not value:
                continue
            if item.source_type == "point" and isinstance(value.get("at"), date):
                marks.append(ComparisonMark(item.object_id, facet, "point", at=value["at"]))
            elif item.source_type == "span" and isinstance(value.get("start"), date) and isinstance(value.get("end", value.get("finish")), date):
                marks.append(ComparisonMark(item.object_id, facet, "span", start=value["start"], end=value.get("end", value.get("finish"))))
    return tuple(marks)


def _annotation_anchor_bounds(mark: ComparisonMark, endpoint: str, row: RowPlacement,
                              scale: ScalePlacement) -> LabelRect:
    if endpoint == "start":
        at = mark.start
    elif endpoint == "finish":
        at = mark.end
    elif endpoint == "at":
        at = mark.at
    elif endpoint == "body":
        at = mark.at or (mark.start + (mark.end - mark.start) / 2 if mark.start and mark.end else None)
    else:
        at = None
    if not isinstance(at, date):
        raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", "/annotations/anchor")
    return LabelRect(_coordinate(at, scale), float(row.bounds.block + row.bounds.block_size * Decimal("0.35")),
                     1.0, max(2.0, float(row.bounds.block_size) * 0.2))
