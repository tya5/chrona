"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from collections.abc import Mapping
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.pattern_placement import PatternedPlacement, complete_pattern_placement
from chrona.presentation.layout.surface_lanes import lane_owner as _lane_owner, review_rows as _review_rows
from chrona.presentation.layout.surface_marks import (
    MARK_PAINT_ORDER_BASE, compose_surface_marks,
)
from chrona.presentation.layout.surface_visuals import (
    place_axis_band_visuals, place_mark_visuals,
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
from chrona.presentation.layout.surface_annotations import SurfaceAnnotationContext, place_annotations
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
from chrona.presentation.layout.text import metric_for_role, place_text
from chrona.presentation.layout.labels import (
    LabelRect, LabelRequest,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
from chrona.presentation.layout.mark_geometry import MarkFacetAbsence
from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.lane_mark_facets import (
    _mark_facets, _overlay_compound_facets, _with_mark_visuals,
)
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, FitWarning, MarkPlacement, PlacementDecision, IconPlacement, ShapePlacement, SurfacePlacement, SurfaceLayoutRequest,
    TextPlacement, LaneEmissionFacet, LaneEmissionPlacement, LaneLabelSuppression,
)
from chrona.presentation.layout.surface_geometry import (
    GEOMETRY_TOLERANCE, bounds_from_rect as _bounds, coordinate_for_date as _coordinate,
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

    annotation_batch = place_annotations(SurfaceAnnotationContext(
        request, projection, layout_manifest, contract, review_rows, rows, by_source, scale, start, end,
        timeline, timeline_bounds, mark_by_id, comparison_clusters, instance_rows, metric_for,
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
