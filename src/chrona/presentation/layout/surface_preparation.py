"""Owns native surface candidate preparation; reads request manifests and typed Layout phases."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_lanes import review_rows as _review_rows, preflight_fixed_lane_layout
from chrona.presentation.layout.surface_base import SurfaceInlineGeometry, prepare_surface_inline
from chrona.presentation.layout.slot_heading import SlotHeadings, complete_slot_headings, content_slot
from chrona.presentation.layout.surface_table import (
    SurfaceTableHeaderSeed, prepare_table_header_seed, table_row_indent_intents,
)
from chrona.presentation.layout.surface_axis import (
    AxisVerticalSummary, SurfaceAxisFrame, SurfaceAxisMeasurement, SurfaceAxisPreparation,
    measure_surface_axis, prepare_surface_axis, summarize_surface_axis_vertical,
)
from chrona.presentation.layout.presentation import MarkGeometry, required_row_block_extents
from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation
from chrona.presentation.layout.surface_mark_visibility import ensure_request_mark_visibility_index
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest


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
    request = ensure_request_mark_visibility_index(request)
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
