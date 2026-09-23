"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect
from chrona.presentation.model.semantic_registry import REQUIRED_SLOTS
from chrona.presentation.layout.presentation import TrackPlacement, place_mark_tracks, place_rows, place_table_columns
from chrona.presentation.layout.axis import axis_intervals, axis_label_fits, fitting_axis, format_axis_label
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, place_text, wrap_text
from chrona.presentation.layout.annotations import (
    nearest_box_port, place_annotation_rail, project_annotation_box,
    resolve_annotation_anchor, route_annotation_leader,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelObstacle, LabelRect, LabelRequest, place_label
from chrona.presentation.layout.routing import place_relation_route, relation_route_quality
from chrona.presentation.layout.path_geometry import rounded_diamond_path, rounded_orthogonal_path
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, GroupPlacement, MarkPlacement, PlacementDecision, RelationPlacement, RowPlacement, ScalePlacement,
    IconPlacement, ShapePlacement, SlotPlacement, SurfacePlacement, SurfaceLayoutRequest,
)


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]


def progress_fill_bounds(host: Rect, fraction: float) -> Rect | None:
    """Return the optional completed progress submark bounds for one host mark."""
    if not 0 <= fraction <= 1:
        raise LayoutError("E_PRESENTATION_PROGRESS_INVALID", "/progressFill")
    if fraction == 0:
        return None
    return Rect(host.inline, host.block, host.inline_size * Decimal(str(fraction)), host.block_size)


def resolve_text_visual_requests(text: list[Any], request: SurfaceLayoutRequest) -> tuple[list[Any], list[IconPlacement]]:
    """Turn already-resolved View visual intents into completed Layout geometry.

    The caller supplies only placement identities; target vocabulary translation
    remains at the typed View boundary.  This helper deliberately has no Scene,
    Theme lookup, or catalog lookup dependency.
    """
    requested: dict[str, dict[str, Any]] = {}
    occupied: set[tuple[str, str]] = set()
    for visual in request.visual_requests:
        if visual.target_kind == "mark":
            continue
        selector = dict(visual.selector)
        placement_id = selector.get("placementId") or visual_target_placement_id(visual.target_kind, selector)
        key = (placement_id, visual.side)
        if key in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(key)
        if visual.ref is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", visual.source_ref)
        requested.setdefault(placement_id, {})[visual.side] = visual
    icons: list[IconPlacement] = []
    for index, item in enumerate(text):
        by_side = requested.pop(item.placement_id, None)
        if not by_side or item.overflow == "suppressed":
            continue
        resolved: dict[str, tuple[Any, float, float]] = {}
        for side, visual in by_side.items():
            icon = request.icon_assets.get(visual.ref)
            if icon is None:
                raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
            try:
                scale, gap_ratio = request.theme_tokens.icon_ratios(item.typography_role)
            except Exception as error:
                raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
            height = item.font_size * float(scale)
            if height <= 0 or icon.viewport[1] <= 0:
                raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", visual.source_ref)
            resolved[side] = (icon, height * icon.viewport[0] / icon.viewport[1], item.font_size * float(gap_ratio))
        leading = sum(width + gap for side, (_, width, gap) in resolved.items() if side == "leading")
        trailing = sum(width + gap for side, (_, width, gap) in resolved.items() if side == "trailing")
        available = (item.available_inline_size if item.available_inline_size is not None
                     else float(item.bounds.inline_size)) - leading - trailing
        if available <= 0:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", next(iter(by_side.values())).source_ref)
        source = item.source_content if item.source_content is not None else item.content
        if len(item.lines) > 1:
            lines = wrap_text(source, available_inline=available, font_size=item.font_size, font_metrics=request.font_metrics)
            content, overflow = "\n".join(lines), item.overflow
        elif item.source_content is not None:
            content = ellipsize_text(source, available_inline=available, font_size=item.font_size, font_metrics=request.font_metrics)
            lines, overflow = (content,), "ellipsized" if content != source else "fit"
        elif measure_text_width(source, font_size=item.font_size, font_metrics=request.font_metrics) <= available:
            content, lines, overflow = source, (source,), item.overflow
        else:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", next(iter(by_side.values())).source_ref)
        width = max(measure_text_width(line, font_size=item.font_size, font_metrics=request.font_metrics) for line in lines)
        baseline = item.baseline
        if baseline is None or not hasattr(request.font_metrics, "cap_height_at"):
            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(iter(by_side.values())).source_ref)
        shifted_baseline = (baseline[0] + leading, baseline[1])
        text[index] = replace(item, content=content, lines=lines, overflow=overflow,
                              bounds=Rect(Decimal(str(shifted_baseline[0])), item.bounds.block,
                                          Decimal(str(width)), Decimal(str(item.font_size * item.line_height * len(lines)))),
                              baseline=shifted_baseline)
        cap_height = float(request.font_metrics.cap_height_at(item.font_size))
        for side, visual in by_side.items():
            icon, icon_width, gap = resolved[side]
            inline = (float(item.bounds.inline) if side == "leading"
                      else float(item.bounds.inline) + leading + available + trailing - gap - icon_width)
            bounds = Rect(Decimal(str(inline)), Decimal(str(baseline[1] - cap_height + (cap_height - item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0])) / 2)),
                          Decimal(str(icon_width)), Decimal(str(item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0]))) )
            icons.append(IconPlacement(f"visual:{item.placement_id}:{side}", item.source_ref, visual.source_ref,
                                       icon.icon_id, icon.kind, icon.content_identity, icon.payload, icon.alternative,
                                       visual.decorative, bounds, "labelVisual"))
    if requested:
        raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(next(iter(requested.values())).values())).source_ref)
    return text, icons


def resolve_mark_visual_requests(marks: list[MarkPlacement], request: SurfaceLayoutRequest) -> list[IconPlacement]:
    """Project the closed View mark target onto one completed planned/actual mark."""
    icons: list[IconPlacement] = []
    occupied: set[str] = set()
    for visual in request.visual_requests:
        if visual.target_kind != "mark":
            continue
        placement_id = visual_target_placement_id("mark", dict(visual.selector))
        if placement_id in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(placement_id)
        # Row-instance identifiers extend the closed object/facet family after
        # the stable View selector; the selector itself never guesses an
        # instance suffix.
        mark = [item for item in marks if item.placement_id == placement_id
                or item.placement_id.startswith(placement_id + ":")]
        icon = request.icon_assets.get(visual.ref or "")
        if len(mark) != 1 or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if len(mark) != 1 else "E_ICON_NAME_UNKNOWN", visual.source_ref)
        host = mark[0]
        height = float(host.bounds.block_size)
        width = min(float(host.bounds.inline_size), height * icon.viewport[0] / icon.viewport[1])
        bounds = Rect(host.bounds.inline + (host.bounds.inline_size - Decimal(str(width))) / 2, host.bounds.block,
                      Decimal(str(width)), host.bounds.block_size)
        icons.append(IconPlacement(f"visual:{host.placement_id}", host.source_ref, visual.source_ref,
                                   icon.icon_id, icon.kind, icon.content_identity, icon.payload, icon.alternative,
                                   visual.decorative, bounds, "iconMark"))
    return icons


def visual_target_placement_id(kind: str, selector: dict[str, str]) -> str:
    """Map the closed View target vocabulary to one Layout placement identity."""
    if kind == "title": return "title"
    if kind == "column" and "id" in selector: return f"column:{selector['id']}"
    if kind == "cell" and {"object", "column"} <= selector.keys(): return f"cell:{selector['object']}:{selector['column']}"
    if kind == "group-header" and "id" in selector: return f"group-header:{selector['id']}"
    if kind == "plot-label" and "id" in selector: return f"member-label:{selector['id']}"
    if kind == "annotation" and "id" in selector: return f"annotation-text:{selector['id']}"
    if kind == "note-index" and "id" in selector: return f"note-index:{selector['id']}"
    if kind == "legend" and "role" in selector: return f"legend:{selector['role']}"
    if kind == "summary" and "id" in selector: return f"summary:{selector['id']}"
    if kind == "milestone" and "id" in selector: return f"milestone:{selector['id']}"
    if kind == "axis-label" and {"level", "index"} <= selector.keys(): return f"axis-label:{selector['level']}:{selector['index']}"
    if kind == "as-of-label": return "as-of-label"
    if kind == "mark" and {"object", "facet"} <= selector.keys(): return f"{selector['facet']}:{selector['object']}"
    raise LayoutError("E_LAYOUT_VISUAL_TARGET", "/body/visuals")


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
    required = tuple(slot.value for slot in REQUIRED_SLOTS)
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
    group_header_size = (float(metric_values["timeline.groupHeader.blockSize"])
                         if request.surface_content.group_presentation == "header" else 0.0)
    raw_rows = place_rows(review_rows=tuple(review_rows), timeline_bounds=timeline_bounds,
                          group_header_size=group_header_size)
    row_height = raw_rows[0].bounds[3] if raw_rows else timeline_bounds[3]
    minimum = float(metric_values["timeline.row.minBlockSize"])
    if any(row_height < minimum * max(1, sum(item.track != "shared" for item in row.items))
           for row in review_rows):
        raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", "/layoutManifest/timeline")
    rows = tuple(
        RowPlacement(item.row_id, item.table_subject_id, placement.group_id or "", _rect(placement.bounds),
                     depth=int(getattr(item, "depth", 0)))
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
                       collision_region="title", collision_domain=CollisionDomain("title", "content"),
                       source_content=title, available_inline_size=float(by_source["title"].bounds.inline_size))]
    table_columns = request.surface_content.table_columns
    table_cells = request.surface_content.table_cells
    columns = place_table_columns(columns=table_columns, cells=table_cells, bounds=table_bounds,
                                  font_metrics=request.font_metrics, font_size=body_size, overflow=table.overflow,
                                  gutter=float(metric_values.get("table.column.gutter.inlineSize", 0)))
    positions = {item.column_id: (item.inline, item.inline_size) for item in columns}
    column_widths = {item.column_id: item.inline_size for item in columns}
    def table_text(content: str, column_id: str) -> tuple[str, str]:
        if table.overflow != "ellipsize-with-source":
            return content, "fit"
        available = max(0.0, column_widths[column_id] - body_size)
        resolved = ellipsize_text(content, available_inline=available, font_size=body_size,
                                  font_metrics=request.font_metrics)
        return resolved, "ellipsized" if resolved != content else "fit"
    for column_id, label in table_columns:
        resolved, overflow = table_text(label, column_id)
        text.append(place_text(placement_id=f"column:{column_id}", source_ref="view:tableColumns", content=resolved,
                               inline=positions[column_id][0], baseline_block=table_bounds[1] + body_size,
                               typography_role="text", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                               overflow=overflow, collision_region="table", collision_domain=CollisionDomain("table", "header"),
                               source_content=label, available_inline_size=column_widths[column_id]))
    row_by_subject = {item.row_id: item for item in rows} | {item.object_id: item for item in rows}
    for object_id, column_id, content in table_cells:
        row = row_by_subject.get(object_id)
        position = positions.get(column_id)
        index = next((offset for offset, item in enumerate(table_columns) if item[0] == column_id), None)
        if row is not None and position is not None and index is not None:
            indent_token = metric_values.get("table.indent.inlineSize")
            if row.depth and indent_token is None:
                raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues/table.indent.inlineSize")
            indent = ((body_size if row.group_id else 0) + float(indent_token or 0) * row.depth
                      if index == 0 else 0)
            resolved, overflow = table_text(content, column_id)
            text.append(place_text(placement_id=f"cell:{object_id}:{column_id}", source_ref=object_id, content=resolved,
                                   inline=position[0] + indent,
                                   baseline_block=float(row.bounds.block + row.bounds.block_size / 2) + body_size / 2,
                                   typography_role="text", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   overflow=overflow, collision_region="table",
                                   collision_domain=CollisionDomain("table", f"row:{row.row_id}"), source_content=content,
                                   available_inline_size=max(0.0, column_widths[column_id] - indent)))
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    for group in groups:
        if group.header_bounds is not None:
            text.append(place_text(placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                                       content=labels[group.group_id], inline=float(group.header_bounds.inline),
                                       baseline_block=float(group.header_bounds.block) + body_size, typography_role="text",
                                   theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region=f"group:{group.group_id}",
                                   collision_domain=CollisionDomain("group-header", group.group_id)))
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
        x, x2 = _coordinate(interval.start, scale), _coordinate(interval.end, scale)
        inline_size = max(0.0, x2 - x)
        label = format_axis_label(interval, format_by_level, request.locale)
        shapes.append(ShapePlacement(f"axis-band-rect:{interval.level}:{interval.index}", "timeline-axis", "Rect",
                                     Rect(Decimal(str(x)), axis.bounds.block, Decimal(str(inline_size)), axis.bounds.block_size)))
        if axis_label_fits(content=label, available_inline=inline_size, font_size=axis_size, font_metrics=request.font_metrics):
            width = measure_text_width(label, font_size=axis_size, font_metrics=request.font_metrics)
            text.append(place_text(placement_id=f"axis-band:{interval.level}:{interval.index}", source_ref="timeline-axis",
                                   content=label, inline=x + (inline_size - width) / 2,
                                   baseline_block=float(axis.bounds.block) + axis_size, typography_role="axis",
                                   theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region="timeline-axis-band",
                                   collision_domain=CollisionDomain("timeline-axis", "coarse-band")))
    for interval in intervals:
        x = _coordinate(interval.start, scale)
        grid_level = "minor" if band_intervals else "major"
        shapes.append(ShapePlacement(f"axis-grid:{grid_level}:{interval.level}:{interval.index}", "timeline-axis", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size)))))
        label = format_axis_label(interval, format_by_level, request.locale)
        if axis_label_fits(content=label, available_inline=(interval.end - interval.start).days * scale.unit_ratio,
                           font_size=float(metric_values["text.body.size"]), font_metrics=request.font_metrics):
            text.append(place_text(placement_id=f"axis-label:{interval.level}:{interval.index}", source_ref="timeline-axis",
                                   content=label, inline=x, baseline_block=float(axis.bounds.block) + axis_size * (2 if band_intervals else 1),
                                   typography_role="axis", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region="timeline-axis-label",
                                   collision_domain=CollisionDomain("timeline-axis", "fine-label")))
    for interval in band_intervals:
        x = _coordinate(interval.start, scale)
        shapes.append(ShapePlacement(f"axis-grid:major:{interval.level}:{interval.index}", "timeline-axis", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size)))))
    contract = request.presentation_contract
    minimum_closed_day_width = metric_values.get("timeline.calendarClosed.minimumDayWidth")
    closed_days = contract.time.calendar_closed
    if minimum_closed_day_width is not None and scale.unit_ratio < float(minimum_closed_day_width):
        closed_days = contract.time.calendar_exceptions
    for closed_day in closed_days:
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
                               collision_region="timeline-as-of",
                               collision_domain=CollisionDomain("timeline", "overlay")))
    tracks = place_mark_tracks(review_rows=tuple(review_rows), row_placements=raw_rows,
                               mark_block_size=float(metric_values["timeline.mark.blockSize"]))
    track_by_id = {item.instance_id: item for item in tracks}
    marks: list[MarkPlacement] = []

    def place_mark(placement_id: str, source_ref: str, bounds: Rect,
                   start_port: tuple[float, float], end_port: tuple[float, float], *, shape: str) -> MarkPlacement:
        requested = float(metric_values.get(
            "timeline.point.cornerRadius" if shape == "point" else "timeline.mark.cornerRadius", 0))
        radius = min(requested, float(min(bounds.inline_size, bounds.block_size)) / 2)
        commands = (rounded_diamond_path(inline=float(bounds.inline), block=float(bounds.block),
                                         inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                    if shape == "point" and radius > 0 else ())
        return MarkPlacement(placement_id, source_ref, bounds, start_port, end_port,
                             mark_shape=shape, corner_radius=radius, path_commands=commands)
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
                marks.append(place_mark(f"planned:{instance_id}", item.object_id, bounds, port, port, shape="point"))
            elif source_kind != "actual":
                x1, x2 = _coordinate(planned["start"], scale), _coordinate(planned["end"], scale)
                bounds = Rect(Decimal(str(x1)), Decimal(str(track.block)),
                              Decimal(str(max(1.0, x2 - x1))), Decimal(str(track.block_size)))
                marks.append(place_mark(f"planned:{instance_id}", item.object_id, bounds,
                                        (x1, track.block + track.block_size / 2),
                                        (x2, track.block + track.block_size / 2), shape="span"))
            actual = item.actual or {}
            if source_kind in {"actual", "combined"} and item.source_type == "span" and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date):
                x1, x2 = _coordinate(actual["start"], scale), _coordinate(actual["finish"], scale)
                bounds = Rect(Decimal(str(x1)), Decimal(str(track.actual_block)),
                              Decimal(str(max(1.0, x2 - x1))), Decimal(str(track.block_size)))
                marks.append(place_mark(f"actual:{instance_id}", item.object_id, bounds,
                                        (x1, track.actual_block + track.block_size / 2),
                                        (x2, track.actual_block + track.block_size / 2), shape="span"))
            elif source_kind in {"actual", "combined"} and item.source_type == "point" and isinstance(actual.get("at"), date):
                x = _coordinate(actual["at"], scale)
                bounds = Rect(Decimal(str(x - track.block_size / 2)), Decimal(str(track.actual_block)),
                              Decimal(str(track.block_size)), Decimal(str(track.block_size)))
                port = (x, track.actual_block + track.block_size / 2)
                marks.append(place_mark(f"actual:{instance_id}", item.object_id, bounds, port, port, shape="point"))
            elif source_kind in {"actual", "combined"}:
                anchor = planned.get("end", planned.get("at"))
                if isinstance(anchor, date):
                    x = _coordinate(anchor, scale)
                    bounds = Rect(Decimal(str(x)), Decimal(str(track.block + track.block_size * 1.25)),
                                  Decimal(str(max(1.0, track.block_size * 1.5))), Decimal(str(track.block_size)))
                    marks.append(place_mark(f"missing-actual:{instance_id}", item.object_id, bounds,
                                            (x, track.block), (x, track.block), shape="span"))
    # A group-header target is a real GroupPlacement extent, not a synthetic table row.
    group_by_id = {group.group_id: group for group in groups}
    folded_by_group: dict[str, list[Any]] = {}
    for folded in getattr(projection, "folded_points", ()):
        folded_by_group.setdefault(folded.group_id, []).append(folded)
    for group_id, folded_points in folded_by_group.items():
        group = group_by_id.get(group_id)
        if group is None or group.header_bounds is None:
            folded = folded_points[0]
            raise LayoutError("E_REVIEW_POINT_GROUP_HEADER_UNAVAILABLE", f"/projection/foldedPoints/{folded.item.object_id}")
        block_size = float(metric_values["timeline.mark.blockSize"])
        capacity = int(float(group.header_bounds.block_size) // block_size)
        if capacity < len(folded_points):
            raise LayoutError("E_LAYOUT_GROUP_HEADER_OVERFLOW", f"/projection/foldedPoints/{group_id}")
        occupied = len(folded_points) * block_size
        first_block = float(group.header_bounds.block) + (float(group.header_bounds.block_size) - occupied) / 2
        for track_index, folded in enumerate(sorted(folded_points, key=lambda point: (point.item.planned.get("at"), point.item.object_id))):
            block = first_block + track_index * block_size
            members = sorted(enumerate(folded.all_items),
                             key=lambda pair: (0, {"snapshot": 0, "scenario": 1, "primary": 2, "actual": 3}.get(pair[1].source_kind, 4))
                             if pair[1].track == "shared" else (1, pair[0]))
            for _, item in members:
                instance_id = _folded_instance_id(folded, item)
                planned_at = item.planned.get("at")
                if item.source_kind != "actual" and isinstance(planned_at, date):
                    x = _coordinate(planned_at, scale)
                    bounds = Rect(Decimal(str(x - block_size / 2)), Decimal(str(block)), Decimal(str(block_size)), Decimal(str(block_size)))
                    port = (x, block + block_size / 2)
                    marks.append(place_mark(f"planned:{instance_id}", item.object_id, bounds, port, port, shape="point"))
                actual_at = (item.actual or {}).get("at")
                if item.source_kind in {"actual", "combined"} and isinstance(actual_at, date):
                    x = _coordinate(actual_at, scale)
                    bounds = Rect(Decimal(str(x - block_size / 2)), Decimal(str(block)), Decimal(str(block_size)), Decimal(str(block_size)))
                    port = (x, block + block_size / 2)
                    marks.append(place_mark(f"actual:{instance_id}", item.object_id, bounds, port, port, shape="point"))
    mark_by_id = {item.placement_id: item for item in marks}
    progress_source = request.surface_content.progress_fill_source
    if progress_source is not None:
        for review_row in review_rows:
            for item in review_row.items:
                if progress_source == "actual":
                    fraction = (item.actual or {}).get("progress")
                    host_prefix = "actual"
                else:
                    fraction = getattr(item, "planned_progress", None)
                    host_prefix = "planned"
                if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not 0 <= fraction <= 1:
                    continue
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                instance_id = layout_id if projection.rows else item.object_id
                host = mark_by_id.get(f"{host_prefix}:{instance_id}")
                if host is None or fraction == 0:
                    continue
                bounds = progress_fill_bounds(host.bounds, float(fraction))
                if bounds is not None and bounds.inline_size > 0:
                    shapes.append(ShapePlacement(f"progress-fill:{host.placement_id}", item.object_id,
                                                 "Rect", bounds, required=False))
    for review_row, row in zip(review_rows, rows, strict=True):
        if getattr(review_row, "rollup_presentation", "none") != "bar":
            continue
        subject = next((item for item in review_row.items
                        if item.item_id == review_row.table_subject_id and item.source_kind != "actual"), None)
        if subject is None or subject.source_type != "span":
            continue
        start_at, end_at = subject.planned.get("start"), subject.planned.get("end")
        if not isinstance(start_at, date) or not isinstance(end_at, date):
            continue
        x1, x2 = _coordinate(start_at, scale), _coordinate(end_at, scale)
        height = max(1.0, float(metric_values["timeline.mark.blockSize"]) / 3)
        shapes.append(ShapePlacement(f"summary-bar:{review_row.row_id}", subject.object_id, "Rect",
                                     Rect(Decimal(str(x1)), row.bounds.block,
                                          Decimal(str(max(1.0, x2 - x1))), Decimal(str(height)))))
    diagnostics: list[str] = []
    placement_decisions: list[PlacementDecision] = []
    label_requests: list[LabelRequest] = []
    if contract.labels.enabled:
        for review_row in review_rows:
            for item in review_row.items:
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                instance_id = layout_id if projection.rows else item.object_id
                planned = item.planned
                start_at, end_at = planned.get("start", planned.get("at")), planned.get("end", planned.get("at"))
                if not isinstance(start_at, date) and not isinstance(end_at, date):
                    continue
                parts = []
                if "title" in contract.labels.content:
                    parts.append(item.title)
                if "finishDelta" in contract.labels.content and item.finish_delta is not None:
                    parts.append(f"{item.finish_delta:+d}d")
                if not parts:
                    continue
                host_kind = "actual" if item.source_kind == "actual" else "planned"
                host_mark_id = f"{host_kind}:{instance_id}"
                mark = mark_by_id.get(host_mark_id)
                if item.source_kind == "actual" and mark is None:
                    raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:{instance_id}")
                track = track_by_id[layout_id]
                anchor = LabelRect(*_bounds(mark.bounds)) if mark is not None else LabelRect(
                    _coordinate(end_at if isinstance(end_at, date) else start_at, scale), track.block,
                    max(1.0, track.block_size), track.block_size)
                default_ladder = (request.surface_content.label_fallback or (("above", "below", "start", "end") if contract.labels.side == "auto" else (contract.labels.side,)))
                intent = getattr(item, "presentation", None) or {}
                preferred_side = (intent.get("label") or {}).get("side") if isinstance(intent, dict) else None
                wrap = ((intent.get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid")
                ladder = ((preferred_side,) + tuple(side for side in default_ladder if side != preferred_side)
                          if preferred_side else default_ladder)
                sides = tuple(side for side in ladder if side != "suppress")
                label_requests.append(LabelRequest(f"member-label:{instance_id}", item.object_id, " ".join(parts),
                                                   anchor, sides, "text", "plot-label", CollisionDomain("timeline", "overlay"),
                                                   "suppress" if "suppress" in ladder else contract.labels.overflow,
                                                   wrap, inside_host_obstacle_id=host_mark_id if mark is not None else None))
        for folded in getattr(projection, "folded_points", ()):
            instance_id = _folded_instance_id(folded, folded.item)
            host_kind = "actual" if folded.item.source_kind == "actual" else "planned"
            mark = mark_by_id.get(f"{host_kind}:{instance_id}")
            group = group_by_id.get(folded.group_id)
            if folded.item.source_kind == "actual" and mark is None:
                raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:group-header:{folded.group_id}:{folded.item.object_id}")
            if mark is None or group is None or group.header_bounds is None:
                continue
            default_ladder = ("end", "start") if contract.labels.side == "auto" else (contract.labels.side,)
            label_requests.append(LabelRequest(
                f"member-label:group-header:{folded.group_id}:{folded.item.object_id}", folded.item.object_id,
                folded.item.title, LabelRect(*_bounds(mark.bounds)), default_ladder, "groupHeader", "group-header-point",
                CollisionDomain("group-header", folded.group_id), "diagnose", bounds=LabelRect(*_bounds(group.header_bounds)),
                inside_host_obstacle_id=mark.placement_id))
    # The remaining text and routes are part of the same completed Layout closure.
    # Scene may select their semantic roles, but it must never remeasure or route them.
    for review_row in review_rows:
        for item in review_row.items:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            if not projection.rows and item.source_kind != "combined":
                continue
            if item.finish_delta is None or "finishDelta" in contract.labels.content:
                continue
            mark = mark_by_id.get(f"actual:{instance_id}") or mark_by_id.get(f"planned:{instance_id}")
            track = track_by_id[layout_id]
            actual = item.actual or {}
            anchor = actual.get("finish", item.planned.get("end", item.planned.get("at")))
            if isinstance(anchor, date):
                anchor_bounds = LabelRect(*_bounds(mark.bounds)) if mark is not None else LabelRect(
                    _coordinate(anchor, scale), track.block, max(1.0, track.block_size), track.block_size)
                label_requests.append(LabelRequest(f"variance:{instance_id}", item.object_id, f"{item.finish_delta:+d}d",
                                                   anchor_bounds, ("above", "below", "end", "start"), "summary",
                                                   f"variance:{instance_id}", CollisionDomain("timeline", "overlay"),
                                                   request.surface_content.label_overflow))

    timeline_rect = LabelRect(*timeline_bounds)
    for label_request in label_requests:
        _, _, font_size, line_height = request.theme_tokens.typography(label_request.typography_role)
        lines = (wrap_text(label_request.content, available_inline=max(1.0, timeline_rect.width * 0.4),
                           font_size=float(font_size), font_metrics=request.font_metrics)
                 if label_request.wrap == "allow" else (label_request.content,))
        placement_bounds = label_request.bounds or timeline_rect
        label_size = (max(measure_text_width(line, font_size=float(font_size), font_metrics=request.font_metrics) for line in lines),
                      float(font_size) * float(line_height) * len(lines))
        obstacles = [LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds))) for item in marks]
        obstacles.extend(LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds))) for item in text
                         if item.required and item.overflow != "suppressed")
        candidate = (place_label(label_request.anchor, label_size, label_request.candidates, bounds=placement_bounds,
                                 obstacles=obstacles, gap=max(1.0, float(font_size) * 0.25),
                                 inside_host_obstacle_id=label_request.inside_host_obstacle_id,
                                 required=label_request.overflow == "diagnose", overflow=label_request.overflow)
                     if label_request.candidates else None)
        provisional = place_text(placement_id=label_request.placement_id, source_ref=label_request.source_ref,
                                 content=label_request.content, inline=0, baseline_block=float(font_size),
                                 typography_role=label_request.typography_role, theme_tokens=request.theme_tokens,
                                 font_metrics=request.font_metrics, collision_region=label_request.collision_region,
                                 collision_domain=label_request.collision_domain)
        if candidate is None:
            ladder = label_request.candidates + (("suppress",) if label_request.overflow == "suppress" else ())
            if not ladder:
                raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{label_request.placement_id}")
            text.append(replace(provisional, overflow="suppressed", required=False,
                                fallback_ladder=ladder,
                                selected_rung="suppress"))
            placement_decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                                         ladder, "suppress", "suppressed"))
            diagnostics.append(f"W_LAYOUT_LABEL_SUPPRESSED:{label_request.placement_id}")
        else:
            text.append(replace(place_text(placement_id=provisional.placement_id, source_ref=provisional.source_ref,
                                   content=provisional.content, inline=candidate.bounds.x,
                                   baseline_block=candidate.bounds.y + float(font_size),
                                   typography_role=provisional.typography_role, theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region=provisional.collision_region,
                                   collision_domain=provisional.collision_domain,
                                   lines=lines),
                                fallback_ladder=label_request.candidates, selected_rung=candidate.side))
            placement_decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                                         label_request.candidates, candidate.side, "placed"))

    relations: list[RelationPlacement] = []
    instance_anchors: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    instance_rows: dict[str, str] = {}
    for review_row, row in zip(review_rows, rows, strict=True):
        fallback = (float(row.bounds.inline + row.bounds.inline_size),
                    float(row.bounds.block + row.bounds.block_size / 2))
        for item in review_row.items:
            instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}" if projection.rows else item.object_id
            instance_anchors.setdefault(item.object_id, []).append((instance_id, fallback))
            instance_rows[instance_id] = row.row_id
    for folded in getattr(projection, "folded_points", ()):
        instance_id = _folded_instance_id(folded, folded.item)
        mark = next((item for item in marks if item.placement_id == f"planned:{instance_id}"), None)
        if mark is not None:
            instance_anchors.setdefault(folded.item.object_id, []).append((instance_id, mark.end_port))
            instance_rows[instance_id] = f"group-header:{folded.group_id}"
    mark_ports = {mark.placement_id.removeprefix("planned:"): (mark.start_port, mark.end_port)
                  for mark in marks if mark.placement_id.startswith("planned:")}
    route_top = min((float(group.header_bounds.block) for group in groups if group.header_bounds is not None),
                    default=timeline_bounds[1])
    route_bottom = max((timeline_bounds[1] + timeline_bounds[3],
                        *(float(group.header_bounds.block + group.header_bounds.block_size)
                          for group in groups if group.header_bounds is not None)))
    for relation in request.surface_content.relations:
        source, target = relation.get("from", {}).get("object"), relation.get("to", {}).get("object")
        relation_id = str(relation.get("id", f"{source}-{target}"))
        for source_id, source_anchor in instance_anchors.get(str(source), ()):
            for target_id, target_anchor in instance_anchors.get(str(target), ()):
                source_port = mark_ports.get(source_id, (source_anchor, source_anchor))[1]
                target_port = mark_ports.get(target_id, (target_anchor, target_anchor))[0]
                scene_id = f"relation:{relation_id}:{source_id}:{target_id}" if projection.rows else f"relation:{relation_id}"
                if source_port == target_port:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, f"{source_id}:end", f"{target_id}:start",
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                    raise LayoutError("E_LAYOUT_RELATION_UNROUTABLE", f"/relations/{relation_id}")
                endpoint_rows = {instance_rows.get(source_id), instance_rows.get(target_id)}
                obstacles = tuple((float(row.bounds.inline), float(row.bounds.block),
                                   float(row.bounds.inline + row.bounds.inline_size),
                                   float(row.bounds.block + row.bounds.block_size))
                                  for row in rows if row.row_id not in endpoint_rows)
                try:
                    points = place_relation_route(source_port=source_port, target_port=target_port, obstacles=obstacles,
                                                  bounds=(timeline_bounds[0], route_top,
                                                          timeline_bounds[0] + timeline_bounds[2], route_bottom))
                except ValueError as error:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, f"{source_id}:end", f"{target_id}:start",
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                    raise LayoutError("E_LAYOUT_RELATION_UNROUTABLE", f"/relations/{relation_id}") from error
                if not relation_route_quality(tuple(points), max_bends=layout_manifest.relation_max_bends,
                                              max_detour_ratio=layout_manifest.relation_max_detour_ratio):
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, f"{source_id}:end", f"{target_id}:start",
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                    raise LayoutError("E_LAYOUT_RELATION_UNROUTABLE", f"/relations/{relation_id}")
                relation_radius = float(metric_values.get("timeline.relation.cornerRadius", 0))
                relations.append(RelationPlacement(scene_id, f"{source_id}:end", f"{target_id}:start", tuple(points),
                                                   semantic_id=str(relation.get("_semantic", "dependency")),
                                                   corner_radius=relation_radius,
                                                   path_commands=(rounded_orthogonal_path(tuple(points), relation_radius)
                                                                  if relation_radius > 0 else ())))

    legend = by_source.get("legend")
    if legend:
        _, _, legend_font_size, legend_line_height = request.theme_tokens.typography("legend")
        legend_size = float(legend_font_size)
        legend_step = legend_size * float(legend_line_height)
        swatch_size = max(2.0, legend_size * 0.8)
        for index, (role, label) in enumerate(request.surface_content.legend_entries):
            baseline = float(legend.bounds.block) + (index + 1) * legend_step
            shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                         Rect(legend.bounds.inline, Decimal(str(baseline - swatch_size)),
                                              Decimal(str(swatch_size)), Decimal(str(swatch_size)))))
            text.append(place_text(placement_id=f"legend:{role}", source_ref=role, content=label,
                                   inline=float(legend.bounds.inline) + swatch_size * 1.5, baseline_block=baseline,
                                   typography_role="legend", theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region="legend",
                                   collision_domain=CollisionDomain("legend", "content")))
    for slot_name, values, prefix, purpose, typography in (
        ("notes", request.surface_content.notes, "note", "project-note", "text"),
        ("group-details", request.surface_content.group_details, "group-detail", "group-detail", "text"),
        ("milestones", request.surface_content.milestones, "milestone", "milestone-digest-entry", "text"),
    ):
        slot = by_source.get(slot_name)
        if slot:
            for index, value in enumerate(values):
                if slot_name == "group-details":
                    source, content = value[0], f"{value[1]}: {value[2]}"
                elif slot_name == "milestones":
                    source, content = value[0], f"{value[1]} — {value[2].isoformat()}"
                else:
                    source, content = value
                text.append(place_text(placement_id=f"{prefix}:{source}", source_ref=source, content=content,
                                       inline=float(slot.bounds.inline),
                                       baseline_block=float(slot.bounds.block) + (index + 1) * body_size,
                                       typography_role=typography, theme_tokens=request.theme_tokens,
                                       font_metrics=request.font_metrics,
                                       collision_region=f"{slot_name}:{source}",
                                       collision_domain=CollisionDomain(slot_name, f"line:{index}")))
    summary_slot = by_source.get("summary")
    if summary_slot:
        cursor = float(summary_slot.bounds.block)
        for run in request.surface_content.summary.runs:
            _, _, font_size, line_height = request.theme_tokens.typography(run.typography_role)
            text.append(place_text(placement_id=run.placement_id, source_ref=run.source_ref, content=run.content,
                                   inline=float(summary_slot.bounds.inline), baseline_block=cursor + float(font_size),
                                   typography_role=run.typography_role, theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region="summary",
                                   collision_domain=CollisionDomain("summary", "content")))
            cursor += float(font_size) * float(line_height)

    annotation_slot = by_source.get("annotations")
    if annotation_slot:
        annotation_marks = _comparison_marks(projection)
        placed_boxes: list[LabelRect] = []
        for index, annotation in enumerate(request.surface_content.annotations):
            annotation_id, content = str(annotation.get("id", index)), str(annotation.get("text", ""))
            content = f"{annotation['number']}. {content}" if "number" in annotation else content
            resolved = resolve_annotation_anchor(annotation, annotation_marks)
            matching = [(review_row, row) for review_row, row in zip(review_rows, rows, strict=True)
                        if any(item.object_id == resolved.object_id for item in review_row.items)]
            anchor = annotation.get("anchor", {})
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
            elif folded_matches and folded_matches[0][1] is not None:
                folded, mark = folded_matches[0]
                anchor_bounds = LabelRect(*_bounds(mark.bounds))
                selected_items = (folded.item,)
            else:
                raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
            size, line_height = (float(item) for item in request.theme_tokens.typography("annotation")[2:])
            width = min(float(annotation_slot.bounds.inline_size), max(size * 4, measure_text_width(content, font_size=size, font_metrics=request.font_metrics)))
            annotation_lines = (content,)
            try:
                if annotation.get("purpose") == "callout":
                    intent = selected_items[0].presentation if selected_items else None
                    preferred = ((intent or {}).get("callout") or {}).get("placement") if isinstance(intent, dict) else None
                    wrap = ((intent or {}).get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid"
                    annotation_lines = (wrap_text(content, available_inline=width, font_size=size, font_metrics=request.font_metrics)
                                        if wrap == "allow" else (content,))
                    annotation_size = (max(measure_text_width(line, font_size=size, font_metrics=request.font_metrics)
                                           for line in annotation_lines), size * line_height * len(annotation_lines))
                    default_ladder = request.surface_content.annotation_fallback or ("rail",)
                    ladder = ((preferred,) + tuple(rung for rung in default_ladder if rung != preferred)
                              if preferred else default_ladder)
                    box, selected_rung = None, None
                    for rung in (rung for rung in ladder if rung != "suppress"):
                        if rung == "rail":
                            candidate_box = place_annotation_rail(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=placed_boxes, overflow="clip-optional", required=False)
                        else:
                            candidate_box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=placed_boxes, overflow="clip-optional", required=False)
                        if candidate_box is not None:
                            box, selected_rung = candidate_box, rung
                            break
                    if box is None:
                        if "suppress" not in ladder:
                            raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/annotations/{index}")
                        placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                     tuple(ladder), "suppress", "suppressed"))
                        diagnostics.append(f"W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:{annotation_id}")
                        continue
                    placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                 tuple(ladder), selected_rung, "placed"))
                else:
                    box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=(width, size * line_height),
                                                 candidate_sides=(annotation.get("placement", {}).get("side", ""),),
                                                 viewport=LabelRect(*_bounds(annotation_slot.bounds)), obstacles=placed_boxes,
                                                 overflow=annotation_slot.overflow, required=annotation_slot.priority == "required")
            except ValueError as error:
                raise LayoutError(str(error), f"/annotations/{index}") from error
            if box is None:
                continue
            placed_boxes.append(box.placement.bounds)
            bounds = box.placement.bounds
            shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                         Rect(Decimal(str(bounds.x)), Decimal(str(bounds.y)), Decimal(str(bounds.width)), Decimal(str(bounds.height)))))
            text.append(place_text(placement_id=f"annotation-text:{annotation_id}", source_ref=annotation_id, content=content,
                                   inline=bounds.x, baseline_block=bounds.y + size, typography_role="annotation",
                                   theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region="annotations", collision_domain=CollisionDomain("annotations", "content"),
                                   lines=annotation_lines))
            if "number" in annotation:
                text.append(place_text(placement_id=f"note-index:{annotation_id}", source_ref=annotation_id,
                                       content=str(annotation["number"]), inline=anchor_bounds.x + anchor_bounds.width,
                                       baseline_block=anchor_bounds.y + body_size, typography_role="annotation",
                                       theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                       collision_region="annotations",
                                       collision_domain=CollisionDomain("timeline", "overlay")))
            if box.leader_required:
                target = nearest_box_port(bounds, (anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2))
                try:
                    points = route_annotation_leader((anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2),
                                                     target, obstacles=placed_boxes[:-1], limit=1024)
                except ValueError as error:
                    raise LayoutError(str(error), f"/annotations/{index}") from error
                relations.append(RelationPlacement(f"annotation-leader:{annotation_id}",
                                                   f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}",
                                                   f"annotation-box:{annotation_id}", tuple(points)))
    text, icons = resolve_text_visual_requests(text, request)
    icons.extend(resolve_mark_visual_requests(marks, request))
    placement = SurfacePlacement(text=tuple(text), slots=slots, rows=rows, groups=tuple(groups), scale=scale,
                                 marks=tuple(marks), shapes=tuple(shapes), relations=tuple(relations),
                                 decisions=tuple(placement_decisions),
                                 diagnostics=tuple(diagnostics), icons=tuple(icons))
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks)


def _rect(bounds: tuple[float, float, float, float]) -> Rect:
    return Rect(*(Decimal(str(value)) for value in bounds))


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))


def _coordinate(value: date, scale: ScalePlacement) -> float:
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio


def _folded_instance_id(folded: Any, item: Any) -> str:
    """Keep a header point's comparison members addressable without inventing rows."""
    return f"group-header:{folded.group_id}:{item.item_id or item.object_id}"


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
