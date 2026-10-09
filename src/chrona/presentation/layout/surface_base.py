"""Owns validated surface slots and row inputs; reads the completed request and Layout manifest."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
from typing import Any

from chrona.presentation.layout.group_tags import (
    group_tag_column_size, vertical_group_tags)
from chrona.presentation.layout.model import LayoutDecision, LayoutError, LayoutManifest, Rect, geometry_sum
from chrona.presentation.layout.lane_preflight import lane_inline_frame_for_manifest
from chrona.presentation.layout.lane_projection import LaneProjectionInstance, lane_missing_actual_visible
from chrona.presentation.layout.lane_subtracks import LaneSubtrackPlan
from chrona.presentation.layout.mark_aware_scale import PointMarkFootprint, inset_scale_for_point_facets
from chrona.presentation.layout.obstacles import obstacle_envelope
from chrona.presentation.layout.presentation import (
    MarkBandFrame, MarkGeometry, TrackPlacement, place_mark_tracks,
    place_rows, required_row_block_extents, row_block_slack, table_text_line_block,
)
from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT, below_plot_reserve, measure_as_of_chip
from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip
from chrona.presentation.layout.surface_lanes import place_lane_mark_tracks
from chrona.presentation.layout.surface_marks import folded_instance_id, resolve_mark_geometries, resolve_mark_band
from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation
from chrona.presentation.layout.surface_lanes import review_rows
from chrona.presentation.layout.surface_geometry import bounds_from_rect, plot_rect, rect_from_bounds
from chrona.presentation.layout.surface_quality import (
    GroupPlacement, RowPlacement, ScalePlacement, SlotPlacement, SurfaceLayoutRequest,
)
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.lane_mark_facets import _mark_facets
from chrona.presentation.model.semantic_registry import REQUIRED_SLOTS


@dataclass(frozen=True)
class SurfaceSlotAllocation:
    """Full immutable allocations, before captions or shared rows consume their viewports."""
    decisions: tuple[LayoutDecision, ...]
    slots: tuple[SlotPlacement, ...]


@dataclass(frozen=True)
class SurfaceInlineGeometry:
    """Validated pre-row facts used to close the shared inline geometry."""
    request: SurfaceLayoutRequest
    projection: Any
    layout_manifest: LayoutManifest
    measured_sources: Any
    metric_values: dict[str, Any]
    allocation: SurfaceSlotAllocation
    decisions: dict[str, Any]
    slots: tuple[SlotPlacement, ...]
    by_source: dict[str, SlotPlacement]
    table: SlotPlacement
    timeline: SlotPlacement
    review_rows: tuple[Any, ...]
    timeline_bounds: tuple[float, float, float, float]
    slot_ids: frozenset[str]
    scale: ScalePlacement
    role_geometries: Mapping[str, MarkGeometry]
    mark_block_size: float
    mark_band_allocation: MarkBandAllocation | None
    group_header_size: float
    group_tag_inline_size: float
    row_requirements: tuple[float, ...]
    row_padding: float
    text_line_block: float
    natural_block_requirement: Decimal


def _layout_manifest(request: SurfaceLayoutRequest) -> LayoutManifest:
    manifest = request.layout_manifest
    if not isinstance(manifest, LayoutManifest):
        raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    return manifest


def prepare_surface_slots(request: SurfaceLayoutRequest) -> SurfaceSlotAllocation:
    """Validate source allocations without closing any row, scale, track or axis geometry."""
    manifest = _layout_manifest(request)
    decisions = {item.source: item for item in manifest.decisions if item.source}
    missing = next((slot.value for slot in REQUIRED_SLOTS if slot.value not in decisions), None)
    if missing is not None:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", f"/layoutManifest/sources/{missing}")
    ordered = tuple(decisions[source] for source in sorted(decisions))
    slots = tuple(
        SlotPlacement(source, source, item.bounds, item.priority or "required",
                      item.overflow or "visible-overflow",
                      "primary" if source in {"timeline", "timeline-axis"} else None,
                      item.direction or "block", item.gap, item.item_min_inline_size)
        for source, item in sorted(decisions.items())
    )
    by_source = {slot.source_ref: slot for slot in slots}
    table, timeline = by_source["table"], by_source["timeline"]
    review_surface = SlotPlacement(
        "review-surface", "review-surface",
        Rect(table.bounds.inline, min(table.bounds.block, timeline.bounds.block),
             timeline.bounds.inline + timeline.bounds.inline_size - table.bounds.inline,
             max(table.bounds.block + table.bounds.block_size,
                 timeline.bounds.block + timeline.bounds.block_size)
             - min(table.bounds.block, timeline.bounds.block)),
    )
    return SurfaceSlotAllocation(ordered, (*slots, review_surface))


@dataclass(frozen=True)
class SurfaceBaseGeometry:
    """Private validated base facts reused by fixed-geometry composition phases."""
    request: SurfaceLayoutRequest
    projection: Any
    layout_manifest: LayoutManifest
    measured_sources: Any
    metric_values: dict[str, Any]
    decisions: dict[str, Any]
    slots: tuple[SlotPlacement, ...]
    by_source: dict[str, SlotPlacement]
    table: SlotPlacement
    timeline: SlotPlacement
    review_rows: tuple[Any, ...]
    timeline_bounds: tuple[float, float, float, float]
    slot_ids: frozenset[str]
    scale: ScalePlacement
    rows: tuple[RowPlacement, ...]
    raw_rows: tuple[Any, ...]
    groups: tuple[GroupPlacement, ...]
    tracks: tuple[TrackPlacement, ...]
    role_geometries: Mapping[str, MarkGeometry]
    mark_block_size: float
    lane_subtracks: LaneSubtrackPlan | None
    group_header_size: float
    row_padding: float
    text_line_block: float
    table_bounds: tuple[float, float, float, float]
    plot: Rect
    # Inline size of the vertical group tag column carved from the table's start; 0 when labels are horizontal (#585).
    group_tag_inline_size: float = 0.0
    # An as-of chip placed `below-plot` (#1063): the block extent reserved under the last row (0 when not reserved)
    # and whether the placement was declared but had no room, so the chip falls back inside the plot.
    as_of_foot_reserve: float = 0.0
    as_of_foot_fallback: bool = False
    mark_band_allocation: MarkBandAllocation | None = None
    as_of_chip_measurement: MeasuredLabelChip | None = None

    def text_slot(self, item: Any) -> str:
        """Resolve a text host against the prepared base slot identities."""
        if item.slot_id in self.slot_ids:
            return item.slot_id
        if item.collision_domain.slot == "group-header":
            return self.table.slot_id
        raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)


def _provisional_point_facets(*, projection: Any, rows: tuple[Any, ...], scale: ScalePlacement,
                              as_of: date | None, theme_tokens: Any, slot_id: str,
                              mark_block_size: float,
                              role_geometries: Mapping[str, MarkGeometry],
                              mark_band_allocation: MarkBandAllocation | None = None) -> tuple[PointMarkFootprint, ...]:
    """Measure visible point-mark horizontal footprints for completed base scale."""
    frame = MarkBandFrame.zero_origin(scale, mark_block_size, role_geometries, mark_band_allocation)
    result: list[PointMarkFootprint] = []

    def include(item: Any, instance_id: str, source_kind: str, row_id: str,
                *, emit_missing_actual: bool = True) -> None:
        composition = compose_item_marks(
            item=item, instance_id=instance_id, source_kind=source_kind, frame=frame,
            as_of=as_of, theme_tokens=theme_tokens, slot_id=slot_id,
            emit_missing_actual=emit_missing_actual, emit_diagnostics=False,
        )
        instance = LaneProjectionInstance(row_id, item.item_id or item.object_id,
                                          item.object_id, item.source_kind)
        for mark in composition.marks:
            if mark.mark_shape != "point":
                continue
            anchor = ((item.actual or {}).get("at") if mark.semantic_id == "actual"
                      else item.planned.get("at"))
            if isinstance(anchor, date):
                for facet in _mark_facets(item, instance, mark, theme_tokens):
                    left, _, right, _ = obstacle_envelope(facet.visible_footprint)
                    result.append(PointMarkFootprint(anchor, left, right))

    for row in rows:
        for item in row.items:
            layout_id = f"{row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            source_kind = item.source_kind if projection.rows else "combined"
            include(item, instance_id, source_kind, row.row_id,
                    emit_missing_actual=(lane_missing_actual_visible(projection)
                                         if projection.lane_membership is not None else True))
    for folded in getattr(projection, "folded_points", ()):
        for item in folded.all_items:
            include(item, folded_instance_id(folded, item), item.source_kind,
                    f"folded:{folded.group_id}", emit_missing_actual=False)
    return tuple(result)


def prepare_surface_inline(request: SurfaceLayoutRequest, *,
                           allocation: SurfaceSlotAllocation | None = None) -> SurfaceInlineGeometry:
    """Close validated slots and exact mark-aware scale before rows are placed."""
    projection = request.projection
    layout_manifest = _layout_manifest(request)
    measured_sources = request.measured_sources
    metric_values = getattr(measured_sources, "metric_values", None)
    if not isinstance(metric_values, dict):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    allocation = allocation if allocation is not None else prepare_surface_slots(request)
    decisions = {item.source: item for item in allocation.decisions}
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    if projection.lane_membership is not None:
        preflight = request.fixed_lane_preflight
        if (preflight is None or preflight.as_of != request.surface_content.as_of
                or preflight.seed_inline_frame != lane_inline_frame_for_manifest(
                    layout_manifest, window=(start, end))):
            raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/layoutManifest")
        request = replace(request, visual_requests=preflight.resolved_visual_requests)
    if ("timeline.row.minBlockSize" not in metric_values
            or "timeline.row.paddingBlock" not in metric_values
            or "timeline.mark.blockSize" not in metric_values):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    slots = allocation.slots
    by_source = {slot.source_ref: slot for slot in slots}
    table, timeline = by_source["table"], by_source["timeline"]
    review_row_values = review_rows(projection) or tuple(
        type("_Row", (), {"row_id": item.object_id, "label": item.title,
                          "group_id": item.group_id, "table_subject_id": item.object_id,
                          "items": (item,)})() for item in projection.items)
    timeline_bounds = bounds_from_rect(timeline.bounds)
    provisional_scale = ScalePlacement(
        "table-timeline", "primary", start, end, timeline_bounds[0],
        timeline_bounds[0] + timeline_bounds[2], timeline_bounds[0],
        timeline_bounds[2] / max(1, (end - start).days),
    )
    group_tags = vertical_group_tags(request)
    # A vertical group label replaces the header row: no row is reserved for it (#585).
    group_header_size = (float(metric_values["timeline.groupHeader.blockSize"])
                         if request.surface_content.group_presentation == "header" and not group_tags else 0.0)
    role_geometries = resolve_mark_geometries(request.theme_tokens)
    mark_block_size = float(metric_values["timeline.mark.blockSize"])
    mark_band_allocation = (request.fixed_lane_preflight.mark_band_allocation
                            if projection.lane_membership is not None and request.fixed_lane_preflight is not None
                            else resolve_mark_band(request.theme_tokens, mark_block_size,
                                                   role_geometries=role_geometries))
    if projection.lane_membership is not None:
        assert request.fixed_lane_preflight is not None
        scale = request.fixed_lane_preflight.scale
    else:
        point_facets = _provisional_point_facets(
            projection=projection, rows=review_row_values, scale=provisional_scale,
            as_of=request.surface_content.as_of, theme_tokens=request.theme_tokens,
            slot_id=timeline.slot_id, mark_block_size=mark_block_size,
            role_geometries=role_geometries,
            mark_band_allocation=mark_band_allocation,
        )
        scale = inset_scale_for_point_facets(provisional_scale, point_facets)
    row_padding = float(metric_values["timeline.row.paddingBlock"])
    text_line_block = table_text_line_block(
        request.theme_tokens, (cell.typography_role for cell in request.surface_content.table_cells))
    if projection.lane_membership is not None:
        assert request.fixed_lane_preflight is not None
        requirement_by_row = dict(request.fixed_lane_preflight.row_requirements)
        requirements = tuple(requirement_by_row[row.row_id] for row in review_row_values)
        natural_block = request.fixed_lane_preflight.natural_block_requirement
    else:
        requirements = required_row_block_extents(
            review_rows=review_row_values, row_minimum=float(metric_values["timeline.row.minBlockSize"]),
            row_padding=row_padding, mark_block_size=mark_block_size,
            role_geometries=role_geometries, text_line_block=text_line_block,
            mark_band_allocation=mark_band_allocation,
        )
        headers = sum(bool(row.group_id) and bool(group_header_size)
                      and (index == 0 or review_row_values[index - 1].group_id != row.group_id)
                      for index, row in enumerate(review_row_values))
        natural_block = (Decimal(str(geometry_sum(requirements)))
                         + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0))
    return SurfaceInlineGeometry(
        request, projection, layout_manifest, measured_sources, metric_values, allocation,
        decisions, slots, by_source, table, timeline, review_row_values, timeline_bounds,
        frozenset(slot.slot_id for slot in slots), scale, role_geometries, mark_block_size,
        mark_band_allocation, group_header_size,
        group_tag_column_size(request.theme_tokens) if group_tags else 0.0,
        tuple(requirements), row_padding, text_line_block, natural_block,
    )


def prepare_surface_base(request: SurfaceLayoutRequest, *,
                         allocation: SurfaceSlotAllocation | None = None,
                         inline: SurfaceInlineGeometry | None = None,
                         row_viewport: Rect | None = None) -> SurfaceBaseGeometry:
    """Validate inputs and close slots, rows, groups, scale and mark tracks."""
    inline = inline if inline is not None else prepare_surface_inline(request, allocation=allocation)
    request = inline.request
    projection = inline.projection
    start, end = projection.window
    layout_manifest = inline.layout_manifest
    measured_sources = inline.measured_sources
    metric_values = inline.metric_values
    decisions = inline.decisions
    slots = inline.slots
    by_source = inline.by_source
    table, timeline = inline.table, inline.timeline
    review_row_values = inline.review_rows
    timeline_bounds = inline.timeline_bounds
    scale = inline.scale
    role_geometries = inline.role_geometries
    mark_block_size = inline.mark_block_size
    mark_band_allocation = inline.mark_band_allocation
    group_header_size = inline.group_header_size
    group_tag_inline_size = inline.group_tag_inline_size
    # Full slots remain ownership/allocation evidence. Only shared row capacity
    # and plot geometry consume the completed native content viewport.
    row_viewport = row_viewport if row_viewport is not None else timeline.bounds
    row_content_bounds = bounds_from_rect(row_viewport)
    row_padding, text_line_block = inline.row_padding, inline.text_line_block
    requirements = inline.row_requirements
    lane_subtracks = request.fixed_lane_preflight.subtracks if projection.lane_membership is not None else None
    foot_reserve = 0.0
    foot_fallback = False
    content = request.surface_content
    as_of_chip_measurement = request.as_of_chip_measurement
    if as_of_chip_measurement is None:
        as_of_chip_measurement = measure_as_of_chip(content, window=projection.window,
            theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
            visual_requests=request.visual_requests, icon_assets=request.icon_assets)
    if (content.as_of_placement == BELOW_PLOT and content.as_of is not None and content.as_of_label
            and start <= content.as_of < end):
        wanted = (below_plot_reserve(request.theme_tokens, chip_measurement=as_of_chip_measurement)
                  if as_of_chip_measurement is not None else below_plot_reserve(request.theme_tokens))
        slack = row_block_slack(review_rows=review_row_values, timeline_block_size=row_content_bounds[3],
                                group_header_size=group_header_size, required_block_sizes=requirements)
        if slack >= wanted:
            foot_reserve = wanted
        else:
            foot_fallback = True
    row_bounds = (*row_content_bounds[:3], row_content_bounds[3] - foot_reserve)
    raw_rows = place_rows(review_rows=review_row_values, timeline_bounds=row_bounds,
                          group_header_size=group_header_size, required_block_sizes=requirements,
                          distribution=layout_manifest.row_distribution)
    rows = tuple(
        RowPlacement(item.row_id, item.table_subject_id, placement.group_id or "",
                     rect_from_bounds(placement.bounds), depth=int(getattr(item, "depth", 0)))
        for item, placement in zip(review_row_values, raw_rows, strict=True)
    )
    table_bounds = bounds_from_rect(table.bounds)
    groups: list[GroupPlacement] = []
    for row in rows:
        if groups and groups[-1].group_id == row.group_id:
            previous = groups[-1]
            content = Rect(previous.content_bounds.inline, previous.content_bounds.block,
                           previous.content_bounds.inline_size,
                           previous.content_bounds.block_size + row.bounds.block_size)
            groups[-1] = GroupPlacement(previous.group_id, content, previous.header_bounds)
        else:
            header = None
            content = row.bounds
            if row.group_id and group_header_size:
                header = Rect(Decimal(str(table_bounds[0])), row.bounds.block - Decimal(str(group_header_size)),
                              Decimal(str(timeline_bounds[0] + timeline_bounds[2] - table_bounds[0])),
                              Decimal(str(group_header_size)))
                content = Rect(row.bounds.inline, header.block, row.bounds.inline_size,
                               row.bounds.block_size + Decimal(str(group_header_size)))
            groups.append(GroupPlacement(row.group_id, content, header))
    groups = tuple(groups)
    tracks = (place_lane_mark_tracks(review_rows=review_row_values, row_placements=raw_rows,
                                     plan=lane_subtracks, mark_block_size=mark_block_size)
              if lane_subtracks is not None else
              place_mark_tracks(review_rows=review_row_values, row_placements=raw_rows,
                                mark_block_size=mark_block_size, role_geometries=role_geometries,
                                mark_band_allocation=mark_band_allocation))
    return SurfaceBaseGeometry(
        request, projection, layout_manifest, measured_sources, metric_values, decisions,
        slots, by_source, table, timeline,
        review_row_values, timeline_bounds,
        inline.slot_ids,
        scale, rows, raw_rows, groups, tracks, role_geometries, mark_block_size,
        lane_subtracks, group_header_size, row_padding, text_line_block, table_bounds,
        plot_rect(row_viewport, (row.bounds for row in rows)),
        group_tag_inline_size=group_tag_inline_size,
        as_of_foot_reserve=foot_reserve, as_of_foot_fallback=foot_fallback,
        mark_band_allocation=mark_band_allocation,
        as_of_chip_measurement=as_of_chip_measurement,
    )
