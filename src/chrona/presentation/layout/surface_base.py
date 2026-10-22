"""Owns validated surface slots and row inputs; reads the completed request and Layout manifest."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
from typing import Any

from chrona.presentation.layout.group_tags import (
    group_tag_column_size, vertical_group_tags)
from chrona.presentation.layout.group_header_fit import (
    GroupHeaderFitPlan, header_text_room, prepare_group_header_fit_plan,
    resolve_group_labels,
)
from chrona.presentation.layout.model import LayoutDecision, LayoutError, LayoutManifest, Rect, geometry_sum
from chrona.presentation.layout.lane_preflight import lane_inline_frame_for_manifest
from chrona.presentation.layout.lane_projection import LaneProjectionInstance, lane_missing_actual_visible
from chrona.presentation.model.projection import active_placement
from chrona.presentation.layout.lane_subtracks import LaneSubtrackPlan
from chrona.presentation.layout.mark_aware_scale import (
    PointMarkFootprint, inset_scale_for_point_facets, point_facet_insets)
from chrona.presentation.layout.obstacles import obstacle_envelope
from chrona.presentation.layout.presentation import (
    MarkBandFrame, MarkGeometry, TrackPlacement, place_mark_tracks,
    empty_group_header_blocks, empty_group_slots, place_rows, required_row_block_extents, row_block_slack, table_text_line_block,
)
from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT, below_plot_reserve, measure_as_of_chip
from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip
from chrona.presentation.layout.surface_lanes import place_lane_mark_tracks
from chrona.presentation.layout.surface_groups import resolve_group_tab
from chrona.presentation.layout.surface_marks import folded_instance_id, resolve_mark_geometries, resolve_mark_band
from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation
from chrona.presentation.layout.mark_role_geometry import (
    resolve_occurrence_mark_frame, selected_mark_style_intents,
)
from chrona.presentation.model.semantic_mark_facets import select_item_mark_facets
from chrona.presentation.layout.surface_lanes import review_rows
from chrona.presentation.layout.surface_geometry import bounds_from_rect, plot_rect, rect_from_bounds
from chrona.presentation.layout.surface_quality import (
    GroupPlacement, RowPlacement, ScalePlacement, SlotPlacement, SurfaceLayoutRequest,
)
from chrona.presentation.layout.window_row_admission import (
    ensure_request_window_row_admission, geometry_group_order, geometry_rows,
)
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.mark_facet_visibility import admitted_source_selection
from chrona.presentation.layout.projection_window import require_positive_projection_window
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, MarkOccurrence, MarkOccurrenceKind,
    ensure_request_mark_visibility_index,
)
from chrona.presentation.layout.lane_mark_facets import _mark_facets
from chrona.presentation.layout.key_row_lanes import assign_key_row_lanes
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
    group_header_fit_plan: GroupHeaderFitPlan | None
    row_requirements: tuple[float, ...]
    row_padding: float
    text_line_block: float
    natural_block_requirement: Decimal
    occurrence_frames: Mapping[str, MarkBandFrame] = field(default_factory=dict)


def _layout_manifest(request: SurfaceLayoutRequest) -> LayoutManifest:
    manifest = request.layout_manifest
    if not isinstance(manifest, LayoutManifest):
        raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    return manifest


def prepare_surface_slots(request: SurfaceLayoutRequest) -> SurfaceSlotAllocation:
    """Validate source allocations without closing any row, scale, track or axis geometry."""
    manifest = _layout_manifest(request)
    decisions = manifest.source_decisions()
    missing = next((slot.value for slot in REQUIRED_SLOTS if slot.value not in decisions), None)
    if missing is not None:
        surface = getattr(request.projection, "surface", "table-timeline")
        raise LayoutError(
            "E_PRESENTATION_PRIMITIVE_MISSING", f"/layoutManifest/sources/{missing}",
            detail=(f"surface={surface}; missing source={missing!r}; add this slot to a matching Layout Profile "
                    "and select it with --layout <profile>"))
    ordered = tuple(decisions[source] for source in sorted(decisions))
    slots = tuple(
        SlotPlacement(source, source, item.bounds, item.priority or "required",
                      item.overflow or "visible-overflow",
                      "primary" if source in {"timeline", "timeline-axis"} else None,
                      item.direction or "block", item.gap, item.item_min_inline_size, item.columns,
                      item.column_distribution)
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
    group_header_fit_plan: GroupHeaderFitPlan | None = None

    def text_slot(self, item: Any) -> str:
        """Resolve a text host against the prepared base slot identities."""
        if item.slot_id in self.slot_ids:
            return item.slot_id
        if item.collision_domain.slot == "group-header":
            return self.table.slot_id
        raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)


@dataclass(frozen=True)
class ClosedSurfaceRows:
    """One shared pre-route closure of group headers, row fill and the optional foot reserve."""

    fit_plan: GroupHeaderFitPlan | None
    group_header_sizes: Mapping[str, float] | None
    empty_slots: tuple[tuple[int, str], ...]
    foot_reserve: float
    foot_fallback: bool
    row_bounds: tuple[float, float, float, float]
    raw_rows: tuple[Any, ...]
    as_of_chip_measurement: MeasuredLabelChip | None


def close_surface_rows(request: SurfaceLayoutRequest, inline: SurfaceInlineGeometry,
                       row_viewport: Rect) -> ClosedSurfaceRows:
    """Close candidate-specific per-group headers before natural demand or any route is produced."""
    projection, content = inline.projection, request.surface_content
    review_rows, requirements = inline.review_rows, inline.row_requirements
    layout_manifest = inline.layout_manifest
    row_content_bounds = bounds_from_rect(row_viewport)
    group_header_size = inline.group_header_size
    group_order = geometry_group_order(projection, request.row_admission)
    plan = inline.group_header_fit_plan
    if plan is not None:
        if not plan.vertical_tag_plan:
            if plan.source_inline_demand:
                plan.require_horizontal_room()
            else:
                owner_id = request.group_header_inline_owner
                owner = next((item for item in layout_manifest.decisions if item.node_id == owner_id), None)
                if owner_id is None or owner is None:
                    raise LayoutError(
                        "E_LAYOUT_MEASUREMENT_REQUIRED", "/layout/groupHeaderBand",
                        detail="a shared outer inline owner is required for this full-span group header")
                plan.require_owner_horizontal_room(
                    owner_node_id=owner_id, available_owner_inline=owner.bounds.inline_size)
        row_groups = {row.group_id for row in review_rows if row.group_id}
        plan = plan.demote(frozenset(group_id for group_id in group_order if group_id not in row_groups))
    group_header_sizes = dict(plan.header_sizes) if plan is not None else None
    empty_slots = (empty_group_slots(review_rows, group_order)
                   if (group_header_size or group_header_sizes) else ())
    chip_measurement = request.as_of_chip_measurement
    if chip_measurement is None:
        chip_measurement = measure_as_of_chip(
            content, window=projection.window, theme_tokens=request.theme_tokens,
            font_metrics=request.font_metrics, visual_requests=request.visual_requests,
            icon_assets=request.icon_assets, scene_precision=request.scene_precision)
    start, end = projection.window
    wanted_foot = 0.0
    if (content.as_of_placement == BELOW_PLOT and content.as_of is not None and content.as_of_label
            and start <= content.as_of < end):
        wanted_foot = (below_plot_reserve(request.theme_tokens, chip_measurement=chip_measurement)
                       if chip_measurement is not None else below_plot_reserve(request.theme_tokens))

    def allocate() -> tuple[float, bool, tuple[float, float, float, float], tuple[Any, ...]]:
        empty_ids = tuple(group_id for _, group_id in empty_slots)
        slack = row_block_slack(
            review_rows=review_rows, timeline_block_size=row_content_bounds[3],
            group_header_size=group_header_size, required_block_sizes=requirements,
            empty_groups=len(empty_slots), group_header_sizes=group_header_sizes,
            empty_group_ids=empty_ids)
        reserve = wanted_foot if wanted_foot and slack >= wanted_foot else 0.0
        fallback = bool(wanted_foot and reserve == 0.0)
        bounds = (*row_content_bounds[:3], row_content_bounds[3] - reserve)
        rows = place_rows(
            review_rows=review_rows, timeline_bounds=bounds, group_header_size=group_header_size,
            required_block_sizes=requirements, distribution=layout_manifest.row_distribution,
            empty_groups=empty_slots, group_header_sizes=group_header_sizes)
        return reserve, fallback, bounds, rows

    foot_reserve, foot_fallback, row_bounds, raw_rows = allocate()
    if plan is not None:
        while True:
            spans: dict[str, float] = {}
            for row in raw_rows:
                if row.group_id:
                    spans[row.group_id] = spans.get(row.group_id, 0.0) + row.bounds[3]
            newly_unfit = frozenset(item.group_id for item in plan.groups
                                    if item.uses_vertical_tag
                                    and spans.get(item.group_id, 0.0) < item.vertical_required_block)
            if not newly_unfit:
                break
            plan = plan.demote(newly_unfit)
            group_header_sizes = dict(plan.header_sizes)
            empty_slots = empty_group_slots(review_rows, group_order)
            foot_reserve, foot_fallback, row_bounds, raw_rows = allocate()
    return ClosedSurfaceRows(
        plan, MappingProxyType(group_header_sizes) if group_header_sizes is not None else None,
        empty_slots, foot_reserve, foot_fallback, row_bounds, raw_rows, chip_measurement)


def _provisional_point_facets(*, projection: Any, rows: tuple[Any, ...], scale: ScalePlacement,
                              as_of: date | None, theme_tokens: Any, slot_id: str,
                              mark_block_size: float,
                              role_geometries: Mapping[str, MarkGeometry],
                              mark_band_allocation: MarkBandAllocation | None = None,
                              mark_visibility_index: ItemMarkVisibilityIndex | None = None,
                              style_intents: Any = None,
                              ) -> tuple[PointMarkFootprint, ...]:
    """Measure visible point-mark horizontal footprints for completed base scale."""
    frame = MarkBandFrame.zero_origin(scale, mark_block_size, role_geometries, mark_band_allocation)
    result: list[PointMarkFootprint] = []

    def include(item: Any, instance_id: str, source_kind: str, row_id: str,
                *, emit_missing_actual: bool = True,
                occurrence_kind: MarkOccurrenceKind | None = None,
                container_id: str | None = None) -> None:
        kind = (occurrence_kind if occurrence_kind is not None else
                MarkOccurrenceKind.LANE_SOURCE if projection.lane_membership is not None else
                MarkOccurrenceKind.ROW if projection.rows else MarkOccurrenceKind.AUTO)
        occurrence = MarkOccurrence(
                kind, (container_id if container_id is not None else
                       row_id if projection.rows else item.object_id),
                item.item_id or item.object_id, item.object_id, source_kind,
            )
        visibility = (mark_visibility_index.lookup(
            occurrence, projection=projection, as_of=as_of,
        ) if mark_visibility_index is not None else None)
        composition = compose_item_marks(
            item=item, instance_id=instance_id, source_kind=source_kind, frame=frame,
            as_of=as_of, theme_tokens=theme_tokens, slot_id=slot_id,
            emit_missing_actual=emit_missing_actual, emit_diagnostics=False,
            selection=admitted_source_selection(visibility) if visibility is not None else None,
            style_intents=occurrence.style_intents(style_intents) if style_intents is not None else None,
        )
        instance = LaneProjectionInstance(row_id, item.item_id or item.object_id,
                                          item.object_id, item.source_kind)
        for mark in composition.marks:
            if mark.mark_shape != "point":
                continue
            anchor = ((item.actual or {}).get("at") if mark.semantic_id == "actual"
                      else active_placement(item).get("at"))
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
                    f"folded:{folded.group_id}", emit_missing_actual=False,
                    occurrence_kind=MarkOccurrenceKind.FOLDED,
                    container_id=folded.group_id)
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
    start, end = require_positive_projection_window(projection)
    allocation = allocation if allocation is not None else prepare_surface_slots(request)
    decisions = {item.source: item for item in allocation.decisions}
    request = ensure_request_mark_visibility_index(request)
    request = ensure_request_window_row_admission(request)
    projection = request.projection
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
    review_row_values = (review_rows(projection, request.row_admission) if projection.has_rows else geometry_rows(tuple(
        type("_Row", (), {"row_id": item.object_id, "label": item.title,
                          "group_id": item.group_id, "table_subject_id": item.object_id,
                          "items": (item,)})() for item in projection.items), request.row_admission))
    timeline_bounds = bounds_from_rect(timeline.bounds)
    capacity = request.temporal_capacity
    if capacity is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/temporalCapacity")
    provisional_scale = capacity.prototype_scale((start, end), inline_origin=timeline_bounds[0])
    group_tags = vertical_group_tags(request)
    # A vertical group label replaces the header row: no row is reserved for it (#585).
    group_header_size = (float(metric_values["timeline.groupHeader.blockSize"])
                         if request.surface_content.group_presentation == "header" and not group_tags else 0.0)
    group_header_fit_plan = None
    group_tag_inline_size = group_tag_column_size(request.theme_tokens) if group_tags else 0.0
    group_tab = resolve_group_tab(request.theme_tokens)
    header_band_extent = layout_manifest.background_extents.get("groupHeaderBand")
    bounded_horizontal = (not group_tags and request.surface_content.group_presentation == "header"
                          and (header_band_extent in {"text", "table"}
                               or (group_tab is not None and group_tab.target == "header")))
    if group_tags or bounded_horizontal:
        labels = resolve_group_labels(
            projection=projection, row_admission=request.row_admission, review_rows=review_row_values,
            declared_headers=request.surface_content.group_headers)
        source_prefix = Decimal(str(group_tag_inline_size))
        source_inline_demand = True
        if group_tags:
            inline_start = float(table.bounds.inline) + group_tag_inline_size
            inline_end = float(table.bounds.inline + table.bounds.inline_size)
        else:
            table_start = table.bounds.inline
            table_end = table.bounds.inline + table.bounds.inline_size
            header_end = timeline.bounds.inline + timeline.bounds.inline_size
            treatment = request.theme_tokens.text_treatment("groupHeader")
            leading_ratio = request.theme_tokens.optional_number("groupHeader", "labelInset")
            trailing_ratio = request.theme_tokens.optional_number("groupHeader", "labelInsetEnd")
            leading_inset = (leading_ratio * treatment.font_size if leading_ratio is not None else Decimal(0))
            trailing_inset = (trailing_ratio * treatment.font_size if trailing_ratio is not None else Decimal(0))
            end_limit = (table_end if header_band_extent in {"text", "table"} else None)
            room = header_text_room(
                header_start=table_start, header_end=header_end,
                label_inset=leading_inset, label_inset_end=trailing_inset,
                label_inset_declared=leading_ratio is not None,
                tab_reserved=(group_tab.reserved if group_tab is not None and group_tab.target == "header"
                              else Decimal(0)),
                tab_position=(group_tab.position if group_tab is not None and group_tab.target == "header"
                             else None),
                text_end_limit=end_limit)
            inline_start = float(room.inline_start)
            inline_end = inline_start + float(room.inline_size)
            source_inline_demand = end_limit is not None
            if source_inline_demand:
                room_end = room.inline_start + room.inline_size
                source_prefix = max(Decimal(0), room.inline_start - table_start) + max(
                    Decimal(0), table_end - min(table_end, room_end))
        group_header_fit_plan = prepare_group_header_fit_plan(
            labels=labels, theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
            header_inline_start=inline_start, header_inline_size=inline_end - inline_start,
            minimum_header_block_size=float(metric_values["timeline.groupHeader.blockSize"]),
            source_inline_prefix=source_prefix,
            vertical_tag_plan=group_tags,
            source_inline_demand=source_inline_demand,
            marked_runs=dict(request.surface_content.group_header_runs))
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
            mark_visibility_index=request.mark_visibility_index,
            style_intents=getattr(request.surface_content, "style_intents", None),
        )
        capacity.require_usable(*point_facet_insets(provisional_scale, point_facets),
                                provisional=provisional_scale)
        scale = inset_scale_for_point_facets(provisional_scale, point_facets)
    review_row_values = assign_key_row_lanes(
        review_row_values, request=request, scale=scale, as_of=request.surface_content.as_of,
        slot_id=timeline.slot_id, mark_block_size=mark_block_size, role_geometries=role_geometries,
        mark_band_allocation=mark_band_allocation)
    occurrence_frames = {}
    style_index = getattr(request.surface_content, "style_intents", None)
    if style_index is not None and style_index.intents and projection.lane_membership is None:
        prototype = MarkBandFrame.zero_origin(scale, mark_block_size, role_geometries, mark_band_allocation)
        for row in review_row_values:
            for item in row.items:
                source_kind = item.source_kind if projection.rows else "combined"
                occurrence = MarkOccurrence(
                    MarkOccurrenceKind.ROW if projection.rows else MarkOccurrenceKind.AUTO,
                    row.row_id if projection.rows else item.object_id,
                    item.item_id or item.object_id, item.object_id, source_kind)
                visibility = (request.mark_visibility_index.lookup(
                    occurrence, projection=projection, as_of=request.surface_content.as_of)
                    if request.mark_visibility_index is not None else None)
                selection = (admitted_source_selection(visibility) if visibility is not None else
                             select_item_mark_facets(item=item, source_kind=source_kind,
                                                     as_of=request.surface_content.as_of))
                intents = selected_mark_style_intents(selection, request.theme_tokens,
                                                      occurrence.style_intents(style_index))
                selected = resolve_occurrence_mark_frame(prototype, request.theme_tokens, intents)
                if selected is not prototype:
                    occurrence_frames[f"{row.row_id}:{item.item_id or item.object_id}"] = selected
    row_padding = float(metric_values["timeline.row.paddingBlock"])
    text_line_block = table_text_line_block(
        request.theme_tokens, (cell.typography_role for cell in request.surface_content.table_cells))
    bounded_table = getattr(measured_sources, "bounded_tables", {}).get("table")
    row_text_blocks = dict(bounded_table.row_text_blocks) if bounded_table is not None else None
    if projection.lane_membership is not None:
        assert request.fixed_lane_preflight is not None
        requirement_by_row = dict(request.fixed_lane_preflight.row_requirements)
        requirements = tuple(requirement_by_row[row.row_id] for row in review_row_values)
        if row_text_blocks is not None:
            requirements = tuple(max(required, max(float(row_text_blocks.get(row.row_id, 0)),
                                                   float(row_text_blocks.get(row.table_subject_id, 0)))
                                     + row_padding)
                                 for row, required in zip(review_row_values, requirements, strict=True))
        natural_block = request.fixed_lane_preflight.natural_block_requirement
        if row_text_blocks is not None:
            natural_block += sum((Decimal(str(required)) - Decimal(str(requirement_by_row[row.row_id]))
                                  for row, required in zip(review_row_values, requirements, strict=True)), Decimal(0))
    else:
        requirements = required_row_block_extents(
            review_rows=review_row_values, row_minimum=float(metric_values["timeline.row.minBlockSize"]),
            row_padding=row_padding, mark_block_size=mark_block_size,
            role_geometries=role_geometries, text_line_block=text_line_block,
            mark_band_allocation=mark_band_allocation,
            row_text_blocks=row_text_blocks,
            occurrence_frames=occurrence_frames,
            as_of=request.surface_content.as_of,
        )
        headers = sum(bool(row.group_id) and bool(group_header_size)
                      and (index == 0 or review_row_values[index - 1].group_id != row.group_id)
                      for index, row in enumerate(review_row_values))
        if group_header_size:
            headers += len(empty_group_slots(
                review_row_values, geometry_group_order(projection, request.row_admission)))
        natural_block = (Decimal(str(geometry_sum(requirements)))
                         + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0))
    return SurfaceInlineGeometry(
        request, projection, layout_manifest, measured_sources, metric_values, allocation,
        decisions, slots, by_source, table, timeline, review_row_values, timeline_bounds,
        frozenset(slot.slot_id for slot in slots), scale, role_geometries, mark_block_size,
        mark_band_allocation, group_header_size,
        group_tag_inline_size, group_header_fit_plan,
        tuple(requirements), row_padding, text_line_block, natural_block,
        MappingProxyType(occurrence_frames),
    )


def prepare_surface_base(request: SurfaceLayoutRequest, *,
                         allocation: SurfaceSlotAllocation | None = None,
                         inline: SurfaceInlineGeometry | None = None,
                         row_viewport: Rect | None = None) -> SurfaceBaseGeometry:
    """Validate inputs and close slots, rows, groups, scale and mark tracks."""
    inline = inline if inline is not None else prepare_surface_inline(request, allocation=allocation)
    request = inline.request
    projection = inline.projection
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
    group_header_fit_plan = inline.group_header_fit_plan
    row_padding, text_line_block = inline.row_padding, inline.text_line_block
    # Full slots remain ownership/allocation evidence. Only shared row capacity
    # and plot geometry consume the completed native content viewport.
    row_viewport = row_viewport if row_viewport is not None else timeline.bounds
    lane_subtracks = request.fixed_lane_preflight.subtracks if projection.lane_membership is not None else None
    closed = close_surface_rows(request, inline, row_viewport)
    group_header_fit_plan = closed.fit_plan
    group_header_sizes = (dict(closed.group_header_sizes)
                          if closed.group_header_sizes is not None else None)
    empty_slots = closed.empty_slots
    foot_reserve, foot_fallback = closed.foot_reserve, closed.foot_fallback
    row_bounds, raw_rows = closed.row_bounds, closed.raw_rows
    as_of_chip_measurement = closed.as_of_chip_measurement
    rows = tuple(
        RowPlacement(item.row_id, item.table_subject_id, placement.group_id or "",
                     rect_from_bounds(placement.bounds), depth=int(getattr(item, "depth", 0)))
        for item, placement in zip(review_row_values, raw_rows, strict=True)
    )
    table_bounds = bounds_from_rect(table.bounds)
    groups: list[GroupPlacement] = []
    empty_blocks = empty_group_header_blocks(slots=empty_slots, row_placements=raw_rows,
                                             timeline_bounds=row_bounds, group_header_size=group_header_size,
                                             group_header_sizes=group_header_sizes)

    def empty_group(block: float, group_id: str) -> GroupPlacement:
        header_size = (group_header_sizes or {}).get(group_id, group_header_size)
        header_inline = (group_header_fit_plan.header_inline_start
                         if group_header_fit_plan is not None and group_header_fit_plan.vertical_tag_plan
                         else table_bounds[0])
        header_inline_size = (group_header_fit_plan.header_inline_size
                              if group_header_fit_plan is not None and group_header_fit_plan.vertical_tag_plan
                              else timeline_bounds[0] + timeline_bounds[2] - header_inline)
        header = Rect(Decimal(str(table_bounds[0])), Decimal(str(block)),
                      Decimal(str(timeline_bounds[0] + timeline_bounds[2] - table_bounds[0])),
                      Decimal(str(header_size)))
        if group_header_fit_plan is not None:
            header = Rect(Decimal(str(header_inline)), header.block, Decimal(str(header_inline_size)), header.block_size)
        return GroupPlacement(group_id, Rect(Decimal(str(timeline_bounds[0])), header.block,
                                             Decimal(str(timeline_bounds[2])), header.block_size), header)

    for index, row in enumerate(rows):
        groups.extend(empty_group(block, group_id)
                      for at, group_id, block in empty_blocks if at == index)
        if groups and groups[-1].group_id == row.group_id:
            previous = groups[-1]
            content = Rect(previous.content_bounds.inline, previous.content_bounds.block,
                           previous.content_bounds.inline_size,
                           previous.content_bounds.block_size + row.bounds.block_size)
            groups[-1] = GroupPlacement(previous.group_id, content, previous.header_bounds)
        else:
            header = None
            content = row.bounds
            row_header_size = (group_header_sizes or {}).get(row.group_id, group_header_size)
            if row.group_id and row_header_size:
                header_inline = (group_header_fit_plan.header_inline_start
                                 if group_header_fit_plan is not None and group_header_fit_plan.vertical_tag_plan
                                 else table_bounds[0])
                header_inline_size = (group_header_fit_plan.header_inline_size
                                      if group_header_fit_plan is not None and group_header_fit_plan.vertical_tag_plan
                                      else timeline_bounds[0] + timeline_bounds[2] - header_inline)
                header = Rect(Decimal(str(header_inline)), row.bounds.block - Decimal(str(row_header_size)),
                              Decimal(str(header_inline_size)), Decimal(str(row_header_size)))
                content = Rect(row.bounds.inline, header.block, row.bounds.inline_size,
                               row.bounds.block_size + Decimal(str(row_header_size)))
            groups.append(GroupPlacement(row.group_id, content, header))
    groups.extend(empty_group(block, group_id) for at, group_id, block in empty_blocks if at >= len(rows))
    groups = tuple(groups)
    tracks = (place_lane_mark_tracks(review_rows=review_row_values, row_placements=raw_rows,
                                     plan=lane_subtracks, mark_block_size=mark_block_size)
              if lane_subtracks is not None else
              place_mark_tracks(review_rows=review_row_values, row_placements=raw_rows,
                                mark_block_size=mark_block_size, role_geometries=role_geometries,
                                mark_band_allocation=mark_band_allocation,
                                occurrence_frames=inline.occurrence_frames,
                                as_of=request.surface_content.as_of))
    return SurfaceBaseGeometry(
        request, projection, layout_manifest, measured_sources, metric_values, decisions,
        slots, by_source, table, timeline,
        review_row_values, timeline_bounds,
        inline.slot_ids,
        scale, rows, raw_rows, groups, tracks, role_geometries, mark_block_size,
        lane_subtracks, group_header_size, row_padding, text_line_block, table_bounds,
        plot_rect(row_viewport, (row.bounds for row in rows)),
        group_tag_inline_size=group_tag_inline_size,
        group_header_fit_plan=group_header_fit_plan,
        as_of_foot_reserve=foot_reserve, as_of_foot_fallback=foot_fallback,
        mark_band_allocation=mark_band_allocation,
        as_of_chip_measurement=as_of_chip_measurement,
    )
