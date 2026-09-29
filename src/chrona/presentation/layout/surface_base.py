"""Owns validated surface slots and row inputs; reads the completed request and Layout manifest."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect, geometry_sum
from chrona.presentation.layout.lane_preflight import lane_inline_frame_for_manifest
from chrona.presentation.layout.lane_projection import LaneProjectionInstance, lane_missing_actual_visible
from chrona.presentation.layout.lane_subtracks import LaneSubtrackPlan
from chrona.presentation.layout.mark_aware_scale import PointMarkFootprint, inset_scale_for_point_facets
from chrona.presentation.layout.obstacles import obstacle_envelope
from chrona.presentation.layout.presentation import (
    MarkBandFrame, MarkGeometry, TrackPlacement, place_mark_tracks,
    place_rows, required_row_block_extents, table_text_line_block,
)
from chrona.presentation.layout.surface_lanes import place_lane_mark_tracks
from chrona.presentation.layout.surface_marks import folded_instance_id, resolve_mark_geometries
from chrona.presentation.layout.surface_lanes import review_rows
from chrona.presentation.layout.surface_geometry import bounds_from_rect, rect_from_bounds
from chrona.presentation.layout.surface_quality import (
    GroupPlacement, RowPlacement, ScalePlacement, SlotPlacement, SurfaceLayoutRequest,
)
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.lane_mark_facets import _mark_facets
from chrona.presentation.model.semantic_registry import REQUIRED_SLOTS


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
                              role_geometries: Mapping[str, MarkGeometry]) -> tuple[PointMarkFootprint, ...]:
    """Measure visible point-mark horizontal footprints for completed base scale."""
    frame = MarkBandFrame.zero_origin(scale, mark_block_size, role_geometries)
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


def prepare_surface_base(request: SurfaceLayoutRequest) -> SurfaceBaseGeometry:
    """Validate inputs and close slots, rows, groups, scale and mark tracks."""
    projection = request.projection
    layout_manifest = request.layout_manifest
    measured_sources = request.measured_sources
    metric_values = getattr(measured_sources, "metric_values", None)
    if not isinstance(layout_manifest, LayoutManifest):
        raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(metric_values, dict):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    decisions = {item.source: item for item in layout_manifest.decisions if item.source}
    required = tuple(slot.value for slot in REQUIRED_SLOTS)
    missing = next((name for name in required if name not in decisions), None)
    if missing is not None:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", f"/layoutManifest/sources/{missing}")
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
    slots += (review_surface,)
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
    group_header_size = (float(metric_values["timeline.groupHeader.blockSize"])
                         if request.surface_content.group_presentation == "header" else 0.0)
    role_geometries = resolve_mark_geometries(request.theme_tokens)
    mark_block_size = float(metric_values["timeline.mark.blockSize"])
    if projection.lane_membership is not None:
        assert request.fixed_lane_preflight is not None
        scale = request.fixed_lane_preflight.scale
    else:
        point_facets = _provisional_point_facets(
            projection=projection, rows=review_row_values, scale=provisional_scale,
            as_of=request.surface_content.as_of, theme_tokens=request.theme_tokens,
            slot_id=timeline.slot_id, mark_block_size=mark_block_size,
            role_geometries=role_geometries,
        )
        scale = inset_scale_for_point_facets(provisional_scale, point_facets)
    row_padding = float(metric_values["timeline.row.paddingBlock"])
    text_line_block = table_text_line_block(
        request.theme_tokens, (cell.typography_role for cell in request.surface_content.table_cells))
    lane_subtracks = None
    if projection.lane_membership is not None:
        assert request.fixed_lane_preflight is not None
        lane_subtracks = request.fixed_lane_preflight.subtracks
        requirement_by_row = dict(request.fixed_lane_preflight.row_requirements)
        requirements = tuple(requirement_by_row[row.row_id] for row in review_row_values)
    else:
        requirements = required_row_block_extents(
            review_rows=review_row_values, row_minimum=float(metric_values["timeline.row.minBlockSize"]),
            row_padding=row_padding, mark_block_size=mark_block_size,
            role_geometries=role_geometries, text_line_block=text_line_block,
        )
    raw_rows = place_rows(review_rows=review_row_values, timeline_bounds=timeline_bounds,
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
                                mark_block_size=mark_block_size, role_geometries=role_geometries))
    return SurfaceBaseGeometry(
        request, projection, layout_manifest, measured_sources, metric_values, decisions,
        slots, {slot.source_ref: slot for slot in slots}, table, timeline,
        review_row_values, timeline_bounds,
        frozenset(slot.slot_id for slot in slots),
        scale, rows, raw_rows, groups, tracks, role_geometries, mark_block_size,
        lane_subtracks, group_header_size, row_padding, text_line_block, table_bounds,
    )
