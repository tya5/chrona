"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect
from chrona.presentation.layout.presentation import TrackPlacement, place_mark_tracks, place_rows, place_table_columns
from chrona.presentation.layout.axis import axis_intervals, axis_label_fits, fitting_axis, format_axis_label
from chrona.presentation.layout.text import place_text
from chrona.presentation.layout.surface_quality import (
    GroupPlacement, MarkPlacement, RowPlacement, ScalePlacement, ShapePlacement, SlotPlacement, SurfacePlacement,
    SurfaceLayoutRequest,
)


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]


def compose_surface_layout(request: SurfaceLayoutRequest) -> SurfaceLayoutComposition:
    """Resolve slots, rows, groups, temporal scale, and mark tracks in Layout."""
    projection = request.projection
    layout_manifest = request.layout_manifest
    measured_sources = request.measured_sources
    metric_values = getattr(measured_sources, "metric_values", None)
    if not isinstance(layout_manifest, LayoutManifest):
        raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(metric_values, dict):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
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
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    body_size = float(request.theme_tokens.typography("text")[2])
    title_input = measured_sources.inputs.get("title")
    title_measurement = measured_sources.measurements.get("title")
    if title_measurement is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")
    title = title_input.lines[0] if title_input and title_input.lines else ""
    text = [place_text(placement_id="title", source_ref="title", content=title,
                       inline=float(by_source["title"].bounds.inline),
                       baseline_block=float(by_source["title"].bounds.block) + float(title_measurement.first_baseline or 0),
                       typography_role="heading", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                       collision_region="title")]
    table_columns = request.surface_content.table_columns
    table_cells = request.surface_content.table_cells
    columns = place_table_columns(columns=table_columns, cells=table_cells, bounds=table_bounds,
                                  font_metrics=request.font_metrics, font_size=body_size, overflow=table.overflow)
    positions = {item.column_id: (item.inline, item.inline_size) for item in columns}
    for column_id, label in table_columns:
        text.append(place_text(placement_id=f"column:{column_id}", source_ref="view:tableColumns", content=label,
                               inline=positions[column_id][0], baseline_block=table_bounds[1] + body_size,
                               typography_role="text", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                               collision_region="table"))
    row_by_subject = {item.row_id: item for item in rows} | {item.object_id: item for item in rows}
    for object_id, column_id, content in table_cells:
        row = row_by_subject.get(object_id)
        position = positions.get(column_id)
        index = next((offset for offset, item in enumerate(table_columns) if item[0] == column_id), None)
        if row is not None and position is not None and index is not None:
            indent = body_size if index == 0 and row.group_id else 0
            text.append(place_text(placement_id=f"cell:{object_id}:{column_id}", source_ref=object_id, content=content,
                                   inline=position[0] + indent,
                                   baseline_block=float(row.bounds.block + row.bounds.block_size / 2) + body_size / 2,
                                   typography_role="text", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region="table"))
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    for group in groups:
        if group.header_bounds is not None:
            text.append(place_text(placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                                   content=labels[group.group_id], inline=float(group.header_bounds.inline),
                                   baseline_block=float(group.header_bounds.block) + body_size, typography_role="text",
                                   theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region=f"group:{group.group_id}"))
    scale = ScalePlacement("table-timeline", "primary", start, end, timeline_bounds[0],
                           timeline_bounds[0] + timeline_bounds[2], timeline_bounds[0],
                           timeline_bounds[2] / max(1, (end - start).days))
    axis = by_source["timeline-axis"]
    configured_levels = request.surface_content.axis_levels
    try:
        intervals = (axis_intervals(start, end, configured_levels[-1][0]) if configured_levels
                     else fitting_axis(requested=request.surface_content.axis_level, start=start, end=end,
                                       inline_size=float(axis.bounds.inline_size),
                                       font_size=float(metric_values["text.body.size"]), font_metrics=request.font_metrics))
    except ValueError as error:
        raise LayoutError(str(error), "/view/body/timePresentation/axisLevel") from error
    axis_size = float(request.theme_tokens.typography("axis")[2])
    band_intervals = axis_intervals(start, end, configured_levels[0][0]) if len(configured_levels) > 1 else (axis_intervals(start, end, "quarter") if intervals and intervals[0].level in {"month", "week"} else ())
    format_by_level = {unit: formatter for unit, formatter in configured_levels}
    format_by_level.update({"month": format_by_level.get("month", "short-month"), "quarter": format_by_level.get("quarter", "year-quarter"), "date": "localized-date"})
    shapes: list[ShapePlacement] = []
    for interval in band_intervals:
        x = _coordinate(interval.start, scale)
        text.append(place_text(placement_id=f"axis-band:{interval.level}:{interval.index}", source_ref="timeline-axis",
                               content=format_axis_label(interval, format_by_level, request.locale), inline=x,
                               baseline_block=float(axis.bounds.block) + axis_size, typography_role="axis",
                               theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                               collision_region="timeline-axis-band"))
    for interval in intervals:
        x = _coordinate(interval.start, scale)
        shapes.append(ShapePlacement(f"axis:{interval.level}:{interval.index}", "timeline-axis", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(axis.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size)))))
        label = format_axis_label(interval, format_by_level, request.locale)
        if axis_label_fits(content=label, available_inline=(interval.end - interval.start).days * scale.unit_ratio,
                           font_size=float(metric_values["text.body.size"]), font_metrics=request.font_metrics):
            text.append(place_text(placement_id=f"axis-label:{interval.level}:{interval.index}", source_ref="timeline-axis",
                                   content=label, inline=x, baseline_block=float(axis.bounds.block) + axis_size * (2 if band_intervals else 1),
                                   typography_role="axis", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region="timeline-axis-label"))
    contract = request.presentation_contract
    for closed_day in contract.time.calendar_closed:
        if start <= closed_day < end:
            x1, x2 = _coordinate(closed_day, scale), _coordinate(closed_day.fromordinal(closed_day.toordinal() + 1), scale)
            shapes.append(ShapePlacement(f"calendar-closed:{closed_day.isoformat()}", "project-calendar", "Rect",
                                         Rect(Decimal(str(x1)), timeline.bounds.block,
                                              Decimal(str(max(0.0, x2 - x1))), timeline.bounds.block_size)))
    if contract.time.as_of is not None and start <= contract.time.as_of < end:
        x = _coordinate(contract.time.as_of, scale)
        shapes.append(ShapePlacement("as-of", "actual-set", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size)))))
        text.append(place_text(placement_id="as-of-label", source_ref="actual-set",
                               content=f"{contract.time.as_of_label} {contract.time.as_of.isoformat()}", inline=x,
                               baseline_block=float(timeline.bounds.block) + body_size, typography_role="text",
                               theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                               collision_region="timeline-as-of"))
    tracks = place_mark_tracks(review_rows=tuple(review_rows), row_placements=raw_rows,
                               mark_block_size=float(metric_values["timeline.mark.blockSize"]))
    track_by_id = {item.instance_id: item for item in tracks}
    marks: list[MarkPlacement] = []
    for review_row in review_rows:
        members = sorted(
            enumerate(review_row.items),
            key=lambda pair: (0, {"snapshot": 0, "primary": 1, "actual": 2}.get(pair[1].source_kind, 3))
            if pair[1].track == "shared" else (1, pair[0]),
        )
        for _, item in members:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            track = track_by_id[layout_id]
            source_kind = item.source_kind if projection.rows else "combined"
            planned = item.planned
            if source_kind != "actual" and item.source_type == "point":
                x = _coordinate(planned["at"], scale)
                bounds = Rect(Decimal(str(x - track.block_size / 2)), Decimal(str(track.block)),
                              Decimal(str(track.block_size)), Decimal(str(track.block_size)))
                port = (x, track.block + track.block_size / 2)
                marks.append(MarkPlacement(f"planned:{instance_id}", item.object_id, bounds, port, port))
            elif source_kind != "actual":
                x1, x2 = _coordinate(planned["start"], scale), _coordinate(planned["end"], scale)
                bounds = Rect(Decimal(str(x1)), Decimal(str(track.block)),
                              Decimal(str(max(1.0, x2 - x1))), Decimal(str(track.block_size)))
                marks.append(MarkPlacement(f"planned:{instance_id}", item.object_id, bounds,
                                           (x1, track.block + track.block_size / 2),
                                           (x2, track.block + track.block_size / 2)))
            actual = item.actual or {}
            if source_kind in {"actual", "combined"} and item.source_type == "span" and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date):
                x1, x2 = _coordinate(actual["start"], scale), _coordinate(actual["finish"], scale)
                bounds = Rect(Decimal(str(x1)), Decimal(str(track.actual_block)),
                              Decimal(str(max(1.0, x2 - x1))), Decimal(str(track.block_size)))
                marks.append(MarkPlacement(f"actual:{instance_id}", item.object_id, bounds,
                                           (x1, track.actual_block + track.block_size / 2),
                                           (x2, track.actual_block + track.block_size / 2)))
            elif source_kind in {"actual", "combined"} and item.source_type == "point" and isinstance(actual.get("at"), date):
                x = _coordinate(actual["at"], scale)
                bounds = Rect(Decimal(str(x - track.block_size / 2)), Decimal(str(track.actual_block)),
                              Decimal(str(track.block_size)), Decimal(str(track.block_size)))
                port = (x, track.actual_block + track.block_size / 2)
                marks.append(MarkPlacement(f"actual:{instance_id}", item.object_id, bounds, port, port))
            elif source_kind in {"actual", "combined"}:
                anchor = planned.get("end", planned.get("at"))
                if isinstance(anchor, date):
                    x = _coordinate(anchor, scale)
                    bounds = Rect(Decimal(str(x)), Decimal(str(track.block + track.block_size * 1.25)),
                                  Decimal(str(max(1.0, track.block_size * 1.5))), Decimal(str(track.block_size)))
                    marks.append(MarkPlacement(f"missing-actual:{instance_id}", item.object_id, bounds,
                                               (x, track.block), (x, track.block)))
    placement = SurfacePlacement(text=tuple(text), slots=slots, rows=rows, groups=tuple(groups), scale=scale, marks=tuple(marks), shapes=tuple(shapes))
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks)


def _rect(bounds: tuple[float, float, float, float]) -> Rect:
    return Rect(*(Decimal(str(value)) for value in bounds))


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))


def _coordinate(value: date, scale: ScalePlacement) -> float:
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio
