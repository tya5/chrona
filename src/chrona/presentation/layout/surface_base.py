"""Owns validated surface slots and row inputs; reads the completed request and Layout manifest."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect
from chrona.presentation.layout.lane_preflight import lane_inline_frame_for_manifest
from chrona.presentation.layout.surface_lanes import review_rows
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
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

    def text_slot(self, item: Any) -> str:
        """Resolve a text host against the prepared base slot identities."""
        if item.slot_id in self.slot_ids:
            return item.slot_id
        if item.collision_domain.slot == "group-header":
            return self.table.slot_id
        raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)


def prepare_surface_base(request: SurfaceLayoutRequest) -> SurfaceBaseGeometry:
    """Validate primitive slots, time window and measurements before geometry phases."""
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
    return SurfaceBaseGeometry(
        request, projection, layout_manifest, measured_sources, metric_values, decisions,
        slots, {slot.source_ref: slot for slot in slots}, table, timeline,
        review_rows(projection) or tuple(
            type("_Row", (), {"row_id": item.object_id, "label": item.title,
                              "group_id": item.group_id, "table_subject_id": item.object_id,
                              "items": (item,)})() for item in projection.items),
        bounds_from_rect(timeline.bounds),
        frozenset(slot.slot_id for slot in slots),
    )
