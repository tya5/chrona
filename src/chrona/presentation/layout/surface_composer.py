"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect
from chrona.presentation.layout.presentation import TrackPlacement, place_mark_tracks, place_rows
from chrona.presentation.layout.surface_quality import (
    GroupPlacement, RowPlacement, ScalePlacement, SlotPlacement, SurfacePlacement,
)


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]


def compose_surface_layout(*, projection: Any, layout_manifest: LayoutManifest,
                           metric_values: dict[str, Any]) -> SurfaceLayoutComposition:
    """Resolve slots, rows, groups, temporal scale, and mark tracks in Layout."""
    decisions = {item.source: item for item in layout_manifest.decisions if item.source}
    required = ("title", "table", "timeline", "timeline-axis")
    missing = next((name for name in required if name not in decisions), None)
    if missing is not None:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", f"/layoutManifest/sources/{missing}")
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    if "timeline.row.minBlockSize" not in metric_values or "timeline.mark.blockSize" not in metric_values:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    slots = tuple(
        SlotPlacement(source, source, item.bounds, item.priority or "required",
                      item.overflow or "diagnose", "primary" if source in {"timeline", "timeline-axis"} else None)
        for source, item in sorted(decisions.items())
    )
    by_source = {slot.source_ref: slot for slot in slots}
    timeline = by_source["timeline"]
    review_rows = projection.rows or tuple(
        type("_Row", (), {"row_id": item.object_id, "label": item.title, "group_id": item.group_id,
                            "table_subject_id": item.object_id, "items": (item,)})()
        for item in projection.items
    )
    timeline_bounds = _bounds(timeline.bounds)
    group_header_size = float(metric_values.get("timeline.groupHeader.blockSize", 0))
    raw_rows = place_rows(review_rows=tuple(review_rows), timeline_bounds=timeline_bounds,
                          group_header_size=group_header_size)
    row_height = raw_rows[0].bounds[3] if raw_rows else timeline_bounds[3]
    minimum = float(metric_values["timeline.row.minBlockSize"])
    if any(row_height < minimum * max(1, sum(item.track != "shared" for item in row.items))
           for row in review_rows):
        raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", "/layoutManifest/timeline")
    rows = tuple(
        RowPlacement(item.row_id, item.table_subject_id, placement.group_id or "", _rect(placement.bounds))
        for item, placement in zip(review_rows, raw_rows, strict=True)
    )
    groups: list[GroupPlacement] = []
    table = by_source["table"]
    table_bounds = _bounds(table.bounds)
    for row in rows:
        if groups and groups[-1].group_id == row.group_id:
            previous = groups[-1]
            content = Rect(previous.content_bounds.inline, previous.content_bounds.block,
                           previous.content_bounds.inline_size,
                           previous.content_bounds.block_size + row.bounds.block_size)
            groups[-1] = GroupPlacement(previous.group_id, content, previous.header_bounds)
        else:
            header = None
            if row.group_id and group_header_size:
                header = Rect(Decimal(str(table_bounds[0])), row.bounds.block - Decimal(str(group_header_size)),
                              Decimal(str(timeline_bounds[0] + timeline_bounds[2] - table_bounds[0])),
                              Decimal(str(group_header_size)))
            groups.append(GroupPlacement(row.group_id, row.bounds, header))
    scale = ScalePlacement("table-timeline", "primary", start, end, timeline_bounds[0],
                           timeline_bounds[0] + timeline_bounds[2], timeline_bounds[0],
                           timeline_bounds[2] / max(1, (end - start).days))
    tracks = place_mark_tracks(review_rows=tuple(review_rows), row_placements=raw_rows,
                               mark_block_size=float(metric_values["timeline.mark.blockSize"]))
    placement = SurfacePlacement(slots=slots, rows=rows, groups=tuple(groups), scale=scale)
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks)


def _rect(bounds: tuple[float, float, float, float]) -> Rect:
    return Rect(*(Decimal(str(value)) for value in bounds))


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))
