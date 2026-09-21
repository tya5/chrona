"""Validated v0.5 Scene construction input boundary.

This module is intentionally renderer-neutral.  Primitive composition follows
in I27-R2; this seam ensures that it can only receive completed current inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from chrona.presentation.layout.axis import axis_intervals, axis_label_fits, fitting_axis, format_axis_label
from chrona.presentation.layout.text import measure_text_width, place_text
from chrona.presentation.layout.routing import place_relation_route
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.presentation import place_table_columns
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneGroup, ScenePrimitive, SceneRow, SceneSlot, SceneSurface, SurfaceScaleManifest, TextLayout
from chrona.presentation.layout.annotations import nearest_box_port, place_annotation_rail, project_annotation_box, resolve_annotation_anchor, route_annotation_leader
from chrona.presentation.layout.comparison_marks import ComparisonMark


class SceneBuildError(ValueError):
    """Stable diagnostic emitted before v0.5 primitive construction."""

    def __init__(self, diagnostic_id: str, path: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path


@dataclass(frozen=True)
class SceneBuildInput:
    """Closed current-runtime inputs for one v0.5 Scene construction."""

    projection: Any
    surface_content: SurfaceContentInput
    layout_manifest: LayoutManifest
    theme_tokens: ThemeTokenView
    font_metrics: Any
    measured_sources: MeasuredSources
    capabilities: Mapping[str, bool]
    locale: str = "en-US"


_REQUIRED_SOURCES = frozenset(("title", "table", "timeline", "timeline-axis"))


def build_scene_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool], locale: str = "en-US") -> SceneBuildInput:
    """Bind validated v0.5 inputs without reopening authoring or legacy contracts."""
    if not isinstance(layout_manifest, LayoutManifest):
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(measured_sources, MeasuredSources):
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    sources = {decision.source for decision in layout_manifest.decisions if decision.source}
    missing = sorted(_REQUIRED_SOURCES - sources)
    if missing:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/" + missing[0])
    if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in capabilities.items()):
        raise SceneBuildError("E_PRESENTATION_CAPABILITY_SCHEMA", "/capabilities")
    return SceneBuildInput(projection, surface_content, layout_manifest,
                           ThemeTokenView(resolved_theme), font_metrics, measured_sources,
                           dict(capabilities), locale)


def compose_review_surface(value: SceneBuildInput) -> SceneSurface:
    """Build the core, fully measured table/timeline surface from the frozen closure."""
    projection = value.projection
    if not hasattr(projection, "items") or not hasattr(projection, "window"):
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection")
    metric = value.measured_sources.metric_values
    contract = normalize_presentation_input(value.surface_content)
    if "text.body.size" not in metric or "text.body.lineHeight" not in metric:
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    try:
        composition = compose_surface_layout(SurfaceLayoutRequest(
            projection=projection, presentation_contract=contract,
            surface_content=value.surface_content, layout_manifest=value.layout_manifest,
            measured_sources=value.measured_sources, theme_tokens=value.theme_tokens,
            font_metrics=value.font_metrics, locale=value.locale,
            capabilities=dict(value.capabilities),
        ))
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path) from error
    placed_surface = composition.placement
    slots = tuple(SceneSlot(item.slot_id, item.source_ref, item.scale_id,
                            (float(item.bounds.inline), float(item.bounds.block),
                             float(item.bounds.inline_size), float(item.bounds.block_size)),
                            item.priority, item.overflow)
                  for item in placed_surface.slots)
    by_source = {slot.source: slot for slot in slots}
    table, timeline, axis, title_slot = (by_source[name] for name in ("table", "timeline", "timeline-axis", "title"))
    review_rows = composition.review_rows
    rows = tuple(
        SceneRow(placement.object_id, placement.group_id,
                 (float(placement.bounds.inline), float(placement.bounds.block),
                  float(placement.bounds.inline_size), float(placement.bounds.block_size)), placement.row_id)
        for placement in placed_surface.rows
    )
    groups = tuple(
        SceneGroup(item.group_id,
                   None if item.header_bounds is None else (float(item.header_bounds.inline), float(item.header_bounds.block),
                                                             float(item.header_bounds.inline_size), float(item.header_bounds.block_size)),
                   (float(item.content_bounds.inline), float(item.content_bounds.block),
                    float(item.content_bounds.inline_size), float(item.content_bounds.block_size)))
        for item in placed_surface.groups
    )
    if placed_surface.scale is None:
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    scale = SurfaceScaleManifest(placed_surface.scale.surface_id, placed_surface.scale.scale_id,
                                 placed_surface.scale.domain_start, placed_surface.scale.domain_end,
                                 placed_surface.scale.range_start, placed_surface.scale.range_end,
                                 placed_surface.scale.origin, placed_surface.scale.unit_ratio)
    start, end = scale.domain_start, scale.domain_end
    title = value.measured_sources.inputs["title"].lines[0] if value.measured_sources.inputs.get("title") and value.measured_sources.inputs["title"].lines else ""
    primitives: list[ScenePrimitive] = []
    def text(scene_id: str, source: str, purpose: str, role: str, content: str, x: float, y: float,
             *, typography_role: str = "text") -> None:
        placed = place_text(placement_id=scene_id, source_ref=source, content=content,
                            inline=x, baseline_block=y, typography_role=typography_role,
                            theme_tokens=value.theme_tokens, font_metrics=value.font_metrics)
        layout = TextLayout((float(placed.bounds.inline), float(placed.bounds.block),
                             float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                            placed.baseline or (x, y), placed.lines, placed.font_family,
                            placed.font_weight, placed.font_size, placed.line_height,
                            placed.font_asset_identity)
        primitives.append(ScenePrimitive(scene_id, "Text", source, "review", purpose, role, layout.bounds,
                                         text=content, baseline=layout.baseline, text_layout=layout, z_order=len(primitives)))
    title_measurement = value.measured_sources.measurements.get("title")
    if title_measurement is None:
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")
    title_baseline = float(title_measurement.first_baseline or 0)
    text("title", "title", "title-text", "text", title, title_slot.bounds[0], title_slot.bounds[1] + title_baseline, typography_role="heading")
    body_size = float(value.theme_tokens.typography("text")[2])
    table_placements = place_table_columns(
        columns=value.surface_content.table_columns,
        cells=value.surface_content.table_cells,
        bounds=table.bounds,
        font_metrics=value.font_metrics,
        font_size=body_size,
        overflow=table.overflow,
    )
    column_positions = {
        placement.column_id: (placement.inline, placement.inline_size)
        for placement in table_placements
    }
    for column_id, label in value.surface_content.table_columns:
        text(f"column:{column_id}", "view:tableColumns", "table-column-label", "text", label,
             column_positions[column_id][0], table.bounds[1] + body_size)
    for object_id, column_id, cell in value.surface_content.table_cells:
        row = next((item for item in rows if item.row_id == object_id or item.object_id == object_id), None)
        position = column_positions.get(column_id)
        index = next((offset for offset, item in enumerate(value.surface_content.table_columns) if item[0] == column_id), None)
        if row is not None and position is not None and index is not None:
            indent = body_size if index == 0 and row.group_id else 0
            text(f"cell:{object_id}:{column_id}", object_id, "table-cell", "text", cell,
                 position[0] + indent, row.bounds[1] + row.bounds[3] / 2 + body_size / 2)
    group_labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
                    for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    for group in groups:
        primitives.append(ScenePrimitive(f"group:{group.group_id}", "Rect", group.group_id, "group", "group-decoration", "group-band",
                                         group.content_bounds, opacity=0.12, z_order=len(primitives)))
        if group.header_bounds is not None:
            primitives.append(ScenePrimitive(f"group-header-band:{group.group_id}", "Rect", group.group_id, "group", "group-header-band", "group-band",
                                             group.header_bounds, opacity=0.2, z_order=len(primitives)))
            text(f"group-header:{group.group_id}", group.group_id, "group-header", "text",
                 group_labels[group.group_id], group.header_bounds[0], group.header_bounds[1] + body_size)
    def coordinate(at: date) -> float:
        return timeline.bounds[0] + (at - start).days * scale.unit_ratio
    calendar_binding = semantic_binding("calendarClosed")
    for closed_day in contract.time.calendar_closed:
        if start <= closed_day < end:
            x1, x2 = coordinate(closed_day), coordinate(closed_day.fromordinal(closed_day.toordinal() + 1))
            primitives.append(ScenePrimitive(f"calendar-closed:{closed_day.isoformat()}", "Rect", "project-calendar", "calendar",
                                             calendar_binding.purpose, calendar_binding.scene_role,
                                             (x1, timeline.bounds[1], max(0.0, x2 - x1), timeline.bounds[3]),
                                             opacity=0.12, z_order=len(primitives)))
    mark_placements = {placement.placement_id: placement for placement in placed_surface.marks}
    track_placements = {placement.instance_id: placement for placement in composition.track_placements}
    mark_ports: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {}
    for review_row, row in zip(review_rows, rows, strict=True):
      members = sorted(enumerate(review_row.items),
                       key=lambda pair: (0, {"snapshot": 0, "primary": 1, "actual": 2}.get(pair[1].source_kind, 3))
                       if pair[1].track == "shared" else (1, pair[0]))
      for _, item in members:
        layout_instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
        instance_id = (layout_instance_id if projection.rows else item.object_id)
        source_kind = item.source_kind if projection.rows else "combined"
        planned = item.planned
        planned_role = "snapshot" if source_kind == "snapshot" else "planned"
        planned_mark = mark_placements.get(f"planned:{instance_id}")
        if planned_mark is not None:
            bounds = (float(planned_mark.bounds.inline), float(planned_mark.bounds.block),
                      float(planned_mark.bounds.inline_size), float(planned_mark.bounds.block_size))
            height, y = bounds[3], bounds[1]
            mark_ports[instance_id] = (planned_mark.start_port, planned_mark.end_port)
            if item.source_type == "point":
                primitives.append(ScenePrimitive(f"planned:{instance_id}", "Symbol", item.object_id, "object", planned_role, planned_role,
                                                 bounds, projection_instance_id=instance_id, shape="diamond", z_order=len(primitives)))
            else:
                primitives.append(ScenePrimitive(f"planned:{instance_id}", "Rect", item.object_id, "object", planned_role, planned_role,
                                                 bounds, projection_instance_id=instance_id, z_order=len(primitives)))
        actual = item.actual or {}
        actual_mark = mark_placements.get(f"actual:{instance_id}")
        if actual_mark is not None:
            bounds = (float(actual_mark.bounds.inline), float(actual_mark.bounds.block),
                      float(actual_mark.bounds.inline_size), float(actual_mark.bounds.block_size))
            if item.source_type == "span":
                primitives.append(ScenePrimitive(f"actual:{instance_id}", "Rect", item.object_id, "object", "actual", "actual",
                                                 bounds, projection_instance_id=instance_id, z_order=len(primitives)))
            else:
                primitives.append(ScenePrimitive(f"actual:{instance_id}", "Symbol", item.object_id, "object", "actual", "actual",
                                                 bounds, projection_instance_id=instance_id, shape="diamond", z_order=len(primitives)))
        missing_mark = mark_placements.get(f"missing-actual:{instance_id}")
        if missing_mark is not None and "missingActual" in (getattr(projection, "comparison_facets", ()) or ("missingActual",)):
            bounds = (float(missing_mark.bounds.inline), float(missing_mark.bounds.block),
                      float(missing_mark.bounds.inline_size), float(missing_mark.bounds.block_size))
            primitives.append(ScenePrimitive(f"missing-actual:{instance_id}", "Rect", item.object_id, "object", "missingActual", "missing-actual",
                                             bounds, projection_instance_id=instance_id, optional=True, z_order=len(primitives)))
        if planned_mark is None:
            track = track_placements[layout_instance_id]
            height, y = track.block_size, track.block
        if contract.labels.enabled:
            start_at, end_at = planned.get("start", planned.get("at")), planned.get("end", planned.get("at"))
            label_at = start_at if value.surface_content.label_placement == "plot" and isinstance(start_at, date) else end_at
            if isinstance(label_at, date):
                label_content = contract.labels.content
                label_parts = []
                if "title" in label_content:
                    label_parts.append(item.title)
                if "finishDelta" in label_content and item.finish_delta is not None:
                    label_parts.append(f"{item.finish_delta:+d}d")
                if label_parts:
                    text(f"member-label:{instance_id}", item.object_id, "member-label", "text",
                         " ".join(label_parts), coordinate(label_at) + height, y + height, typography_role="text")
        if source_kind == "combined" and item.finish_delta is not None:
            role = "variance-behind" if item.finish_delta > 0 else "variance-ahead" if item.finish_delta < 0 else "variance-on-track"
            text(f"variance:{instance_id}", item.object_id, "finish-delta", role,
                 f"{item.finish_delta:+d}d", coordinate(actual.get("finish", planned.get("end", planned.get("at")))), y + height, typography_role="summary")
    configured_levels = value.surface_content.axis_levels
    try:
        intervals = (axis_intervals(start, end, configured_levels[-1][0]) if configured_levels
                     else fitting_axis(requested=value.surface_content.axis_level, start=start, end=end,
                                       inline_size=timeline.bounds[2],
                                       font_size=float(value.measured_sources.metric_values["text.body.size"]),
                                       font_metrics=value.font_metrics))
    except ValueError as error:
        raise SceneBuildError(str(error), "/view/body/timePresentation/axisLevel") from error
    axis_size = float(value.theme_tokens.typography("axis")[2])
    band_intervals = axis_intervals(start, end, configured_levels[0][0]) if len(configured_levels) > 1 else (axis_intervals(start, end, "quarter") if intervals and intervals[0].level in {"month", "week"} else ())
    format_by_level = {unit: formatter for unit, formatter in configured_levels}
    format_by_level.update({"month": format_by_level.get("month", "short-month"), "quarter": format_by_level.get("quarter", "year-quarter"), "date": "localized-date"})
    axis_band_binding = semantic_binding("axisBand")
    for interval in band_intervals:
        x = timeline.bounds[0] + (interval.start - start).days * scale.unit_ratio
        text(f"axis-band:{interval.level}:{interval.index}", "timeline-axis", axis_band_binding.purpose, "text",
             format_axis_label(interval, format_by_level, value.locale),
             x, axis.bounds[1] + axis_size, typography_role="axis")
    for interval in intervals:
        x = timeline.bounds[0] + (interval.start - start).days * scale.unit_ratio
        primitives.append(ScenePrimitive(f"axis:{interval.level}:{interval.index}", "Path", "timeline-axis", "axis", "axis-grid", "axis-major",
                                         (x, timeline.bounds[1], 0, timeline.bounds[3]), points=((x, axis.bounds[1]), (x, timeline.bounds[1] + timeline.bounds[3])), z_order=len(primitives)))
        axis_label = format_axis_label(interval, format_by_level, value.locale)
        clipped_width = (interval.end - interval.start).days * scale.unit_ratio
        if axis_label_fits(content=axis_label, available_inline=clipped_width,
                           font_size=float(value.measured_sources.metric_values["text.body.size"]),
                           font_metrics=value.font_metrics):
            text(f"axis-label:{interval.level}:{interval.index}", "timeline-axis", "axis-label", "text", axis_label, x,
                 axis.bounds[1] + axis_size * (2 if band_intervals else 1), typography_role="axis")
    if contract.time.as_of is not None and start <= contract.time.as_of < end:
        as_of_binding = semantic_binding("asOf")
        as_of_x = coordinate(contract.time.as_of)
        primitives.append(ScenePrimitive("as-of", "Path", "actual-set", "actual", as_of_binding.purpose, as_of_binding.scene_role,
                                         (as_of_x, timeline.bounds[1], 0, timeline.bounds[3]),
                                         points=((as_of_x, timeline.bounds[1]), (as_of_x, timeline.bounds[1] + timeline.bounds[3])),
                                         z_order=len(primitives)))
        text("as-of-label", "actual-set", "as-of-label", "text",
             f"{contract.time.as_of_label} {contract.time.as_of.isoformat()}", as_of_x, timeline.bounds[1] + body_size)
    instance_anchors: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    instance_rows: dict[str, str] = {}
    for review_row, row in zip(review_rows, rows, strict=True):
        anchor = (row.bounds[0] + row.bounds[2], row.bounds[1] + row.bounds[3] / 2)
        for item in review_row.items:
            instance_id = (f"{review_row.row_id}:{item.item_id or item.object_id}"
                           if projection.rows else item.object_id)
            instance_anchors.setdefault(item.object_id, []).append(
                (instance_id, anchor))
            instance_rows[instance_id] = row.row_id
    obstacles = tuple((row.bounds[0], row.bounds[1], row.bounds[0] + row.bounds[2], row.bounds[1] + row.bounds[3])
                      for row in rows)
    for relation in value.surface_content.relations:
        source = relation.get("from", {}).get("object")
        target = relation.get("to", {}).get("object")
        source_instances = instance_anchors.get(str(source), ())
        target_instances = instance_anchors.get(str(target), ())
        for source_id, source_anchor in source_instances:
            for target_id, target_anchor in target_instances:
                source_port = mark_ports.get(source_id, (source_anchor, source_anchor))[1]
                target_port = mark_ports.get(target_id, (target_anchor, target_anchor))[0]
                if source_port == target_port:
                    raise SceneBuildError("E_PRESENTATION_ROUTE_UNAVAILABLE", f"/relations/{relation.get('id', '')}")
                endpoint_rows = {instance_rows.get(source_id), instance_rows.get(target_id)}
                route_obstacles = tuple((item.bounds[0], item.bounds[1], item.bounds[0] + item.bounds[2], item.bounds[1] + item.bounds[3])
                                        for item in rows
                                        if item.row_id not in endpoint_rows)
                points = place_relation_route(source_port=source_port, target_port=target_port, obstacles=route_obstacles,
                    bounds=(timeline.bounds[0], timeline.bounds[1], timeline.bounds[0] + timeline.bounds[2], timeline.bounds[1] + timeline.bounds[3]))
                if len(points) < 2:
                    raise SceneBuildError("E_PRESENTATION_ROUTE_UNAVAILABLE", f"/relations/{relation.get('id', '')}")
                relation_id = str(relation.get("id", f"{source}-{target}"))
                scene_id = f"relation:{relation_id}:{source_id}:{target_id}" if projection.rows else f"relation:{relation_id}"
                primitives.append(ScenePrimitive(scene_id, "Path", relation_id, "relation", "dependency", "dependency",
                    (0, 0, 0, 0), shape=str(value.theme_tokens.token("dependency", "marker", "marker")), points=points,
                    from_port_id=f"{source_id}:end", to_port_id=f"{target_id}:start", z_order=len(primitives)))
    legend = by_source.get("legend")
    legend_binding = semantic_binding("legendEntry")
    if legend:
        legend_size = float(value.theme_tokens.typography("legend")[2])
        swatch_size = max(2.0, legend_size * 0.8)
        for index, (role, label) in enumerate(value.surface_content.legend_entries):
            baseline = legend.bounds[1] + (index + 1) * legend_size
            primitives.append(ScenePrimitive(f"legend-swatch:{role}", "Rect", role, "legend", legend_binding.purpose, role,
                                             (legend.bounds[0], baseline - swatch_size, swatch_size, swatch_size),
                                             z_order=len(primitives)))
            text(f"legend:{role}", role, "legend-label", "text", label,
                 legend.bounds[0] + swatch_size * 1.5, baseline, typography_role="legend")
    notes = by_source.get("notes")
    if notes:
        for index, (note_id, content) in enumerate(value.surface_content.notes):
            text(f"note:{note_id}", note_id, "project-note", "text", content, notes.bounds[0], notes.bounds[1] + (index + 1) * body_size)
    detail_slot = by_source.get("group-details")
    if detail_slot:
        for index, (group_id, label, description) in enumerate(value.surface_content.group_details):
            text(f"group-detail:{group_id}", group_id, "group-detail", "text", f"{label}: {description}", detail_slot.bounds[0], detail_slot.bounds[1] + (index + 1) * body_size)
    milestone_slot = by_source.get("milestones")
    if milestone_slot:
        for index, (object_id, label, at) in enumerate(value.surface_content.milestones):
            text(f"milestone:{object_id}", object_id, "milestone-digest-entry", "text", f"{label} — {at.isoformat()}", milestone_slot.bounds[0], milestone_slot.bounds[1] + (index + 1) * body_size)
    summary_slot = by_source.get("summary")
    if summary_slot:
        line = 1
        summary_size = float(value.theme_tokens.typography("summary")[2])
        presentations = dict(value.surface_content.summary_presentations)
        for panel_id, panel_title, metrics in value.surface_content.summary_panels:
            text(f"summary:{panel_id}", panel_id, "summary-header", "text", panel_title, summary_slot.bounds[0], summary_slot.bounds[1] + line * summary_size, typography_role="summary"); line += 1
            for key, metric_value in metrics:
                if presentations.get(panel_id) == "figures":
                    text(f"summary:{panel_id}:{key}:value", panel_id, "summary-figure-value", "metric", metric_value, summary_slot.bounds[0], summary_slot.bounds[1] + line * summary_size, typography_role="metric")
                    line += 1
                    text(f"summary:{panel_id}:{key}:caption", panel_id, "summary-figure-caption", "subtitle", key, summary_slot.bounds[0], summary_slot.bounds[1] + line * summary_size, typography_role="summary")
                else:
                    text(f"summary:{panel_id}:{key}", panel_id, "summary-metric", "text", f"{key}: {metric_value}", summary_slot.bounds[0], summary_slot.bounds[1] + line * summary_size, typography_role="summary")
                line += 1
    annotation_slot = by_source.get("annotations")
    annotation_binding = semantic_binding("annotation")
    if annotation_slot:
        marks = _comparison_marks(projection)
        placed: list[LabelRect] = []
        for index, annotation in enumerate(value.surface_content.annotations):
            annotation_id, content = str(annotation.get("id", index)), str(annotation.get("text", ""))
            content = f"{annotation['number']}. {content}" if "number" in annotation else content
            resolved = resolve_annotation_anchor(annotation, marks)
            anchor = annotation.get("anchor", {})
            matching = [(review_row, scene_row) for review_row, scene_row in zip(review_rows, rows, strict=True)
                        if any(item.object_id == resolved.object_id for item in review_row.items)]
            row_id, item_id = anchor.get("rowId"), anchor.get("itemId")
            if row_id is not None or item_id is not None:
                matching = [(review_row, scene_row) for review_row, scene_row in matching
                            if (row_id is None or review_row.row_id == row_id)
                            and (item_id is None or any(item.item_id == item_id and item.object_id == resolved.object_id for item in review_row.items))]
            if len(matching) > 1:
                raise SceneBuildError("E_PRESENTATION_ROW_ANCHOR_AMBIGUOUS", f"/annotations/{index}/anchor")
            row = matching[0][1] if matching else None
            if row is None:
                raise SceneBuildError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
            anchor_bounds = _annotation_anchor_bounds(resolved.mark, resolved.endpoint, row, coordinate)
            if "number" in annotation:
                text(f"note-index:{annotation_id}", annotation_id, "note-index", "note-index",
                     str(annotation["number"]), anchor_bounds.x + anchor_bounds.width, anchor_bounds.y + body_size,
                     typography_role="annotation")
            size, line_height = (float(item) for item in value.theme_tokens.typography("annotation")[2:])
            width, height = min(annotation_slot.bounds[2], max(size * 4, measure_text_width(content, font_size=size, font_metrics=value.font_metrics))), size * line_height
            try:
                if annotation.get("purpose") == "callout":
                    box = place_annotation_rail(annotation, resolved,
                                                anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                                text_size=(width, height), rail=LabelRect(*annotation_slot.bounds),
                                                obstacles=placed, overflow=annotation_slot.overflow,
                                                required=annotation_slot.priority == "required")
                else:
                    box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=(width, height),
                                                 candidate_sides=(annotation.get("placement", {}).get("side", ""),),
                                                 viewport=LabelRect(*annotation_slot.bounds), obstacles=placed,
                                                 overflow=annotation_slot.overflow, required=annotation_slot.priority == "required")
            except ValueError as error:
                raise SceneBuildError(str(error), f"/annotations/{index}") from error
            if box is None:
                continue
            placed.append(box.placement.bounds)
            bounds = (box.placement.bounds.x, box.placement.bounds.y, box.placement.bounds.width, box.placement.bounds.height)
            primitives.append(ScenePrimitive(f"annotation-box:{annotation_id}", "Rect", annotation_id, "annotation", f"{annotation_binding.purpose}-box", annotation_binding.scene_role, bounds, z_order=len(primitives)))
            text(f"annotation-text:{annotation_id}", annotation_id, "annotation", "annotation-text", content, bounds[0], bounds[1] + size, typography_role="annotation")
            if box.leader_required:
                target = nearest_box_port(box.placement.bounds, (anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2))
                try:
                    points = route_annotation_leader((anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2), target,
                                                     obstacles=placed[:-1], limit=1024)
                except ValueError as error:
                    raise SceneBuildError(str(error), f"/annotations/{index}") from error
                primitives.append(ScenePrimitive(f"annotation-leader:{annotation_id}", "Path", annotation_id, "annotation", f"{annotation_binding.purpose}-leader", annotation_binding.scene_role, (0, 0, 0, 0),
                                                 points=points, from_port_id=f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}", to_port_id=f"annotation-box:{annotation_id}", z_order=len(primitives)))
    return SceneSurface("table-timeline", slots, rows, groups, scale, tuple(primitives))


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


def _annotation_anchor_bounds(mark: ComparisonMark, endpoint: str, row: SceneRow, coordinate: Any) -> LabelRect:
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
        raise SceneBuildError("E_PRESENTATION_ANCHOR_MISSING", "/annotations/anchor")
    return LabelRect(coordinate(at), row.bounds[1] + row.bounds[3] * 0.35, 1.0, max(2.0, row.bounds[3] * 0.2))
