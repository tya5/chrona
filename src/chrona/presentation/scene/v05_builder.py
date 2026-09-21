"""Validated v0.5 Scene construction input boundary.

This module is intentionally renderer-neutral.  Primitive composition follows
in I27-R2; this seam ensures that it can only receive completed current inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from chrona.presentation.layout.axis import axis_intervals
from chrona.presentation.layout.routing import route_orthogonal
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.model import LayoutManifest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneGroup, ScenePrimitive, SceneRow, SceneSlot, SceneSurface, SurfaceScaleManifest, TextLayout
from chrona.presentation.scene.annotations import nearest_box_port, place_annotation_rail, project_annotation_box, resolve_annotation_anchor, route_annotation_leader
from chrona.presentation.scene.marks import ComparisonMark


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


_REQUIRED_SOURCES = frozenset(("title", "table", "timeline", "timeline-axis"))


def build_scene_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool]) -> SceneBuildInput:
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
                           dict(capabilities))


def compose_review_surface(value: SceneBuildInput) -> SceneSurface:
    """Build the core, fully measured table/timeline surface from the frozen closure."""
    projection = value.projection
    if not hasattr(projection, "items") or not hasattr(projection, "window"):
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection")
    metric = value.measured_sources.metric_values
    if "text.body.size" not in metric or "text.body.lineHeight" not in metric:
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    decisions = {item.source: item for item in value.layout_manifest.decisions if item.source}
    slots = tuple(SceneSlot(source, source, "primary" if source in {"timeline", "timeline-axis"} else None,
                            (float(item.bounds.inline), float(item.bounds.block), float(item.bounds.inline_size), float(item.bounds.block_size)),
                            item.priority or "required", item.overflow or "diagnose")
                  for source, item in sorted(decisions.items()))
    by_source = {slot.source: slot for slot in slots}
    table, timeline, axis, title_slot = (by_source[name] for name in ("table", "timeline", "timeline-axis", "title"))
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    review_rows = projection.rows or tuple(
        type("_Row", (), {"row_id": item.object_id, "label": item.title, "group_id": item.group_id,
                           "table_subject_id": item.object_id, "items": (item,)})()
        for item in projection.items)
    row_height = timeline.bounds[3] / max(1, len(review_rows))
    minimum = float(metric["timeline.row.minBlockSize"])
    if any(row_height < minimum * len(review_row.items) for review_row in review_rows):
        raise SceneBuildError("E_LAYOUT_REQUIRED_OVERFLOW", "/layoutManifest/timeline")
    rows = tuple(SceneRow(
        review_row.table_subject_id, review_row.group_id,
        (timeline.bounds[0], timeline.bounds[1] + index * row_height, timeline.bounds[2], row_height),
        review_row.row_id)
        for index, review_row in enumerate(review_rows))
    groups: list[SceneGroup] = []
    for row in rows:
        if groups and groups[-1].group_id == row.group_id:
            previous = groups[-1]
            groups[-1] = SceneGroup(previous.group_id, previous.header_bounds,
                                    (previous.content_bounds[0], previous.content_bounds[1], previous.content_bounds[2],
                                     previous.content_bounds[3] + row.bounds[3]))
        else:
            groups.append(SceneGroup(row.group_id, None, row.bounds))
    scale = SurfaceScaleManifest("table-timeline", "primary", start, end, timeline.bounds[0],
                                 timeline.bounds[0] + timeline.bounds[2], timeline.bounds[0],
                                 timeline.bounds[2] / max(1, (end - start).days))
    title = value.measured_sources.inputs["title"].lines[0] if value.measured_sources.inputs.get("title") and value.measured_sources.inputs["title"].lines else ""
    primitives: list[ScenePrimitive] = []
    def text(scene_id: str, source: str, purpose: str, role: str, content: str, x: float, y: float,
             *, typography_role: str = "text") -> None:
        family, weight, size, line_height = value.theme_tokens.typography(typography_role)
        font_size = float(size)
        layout = TextLayout((x, y - font_size, value.font_metrics.width(content, font_size), font_size * float(line_height)),
                            (x, y), (content,), family, weight, font_size, float(line_height), value.font_metrics.content_identity)
        primitives.append(ScenePrimitive(scene_id, "Text", source, "review", purpose, role, layout.bounds,
                                         text=content, baseline=layout.baseline, text_layout=layout, z_order=len(primitives)))
    title_baseline = float(value.measured_sources.measurements["title"].first_baseline or 0)
    text("title", "title", "title-text", "text", title, title_slot.bounds[0], title_slot.bounds[1] + title_baseline, typography_role="heading")
    body_size = float(value.theme_tokens.typography("text")[2])
    column_width = table.bounds[2] / max(1, len(value.surface_content.table_columns))
    for index, (column_id, label) in enumerate(value.surface_content.table_columns):
        text(f"column:{column_id}", "view:tableColumns", "table-column-label", "text", label,
             table.bounds[0] + index * column_width, table.bounds[1] + body_size)
    for object_id, column_id, cell in value.surface_content.table_cells:
        row = next((item for item in rows if item.row_id == object_id or item.object_id == object_id), None)
        index = next((offset for offset, value in enumerate(value.surface_content.table_columns) if value[0] == column_id), None)
        if row is not None and index is not None:
            text(f"cell:{object_id}:{column_id}", object_id, "table-cell", "text", cell,
                 table.bounds[0] + index * column_width, row.bounds[1] + row.bounds[3] / 2 + body_size / 2)
    for group in groups:
        primitives.append(ScenePrimitive(f"group:{group.group_id}", "Rect", group.group_id, "group", "group-decoration", "group-band",
                                         group.content_bounds, opacity=0.12, z_order=len(primitives)))
    def coordinate(at: date) -> float:
        return timeline.bounds[0] + (at - start).days * scale.unit_ratio
    mark_ports: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {}
    for review_row, row in zip(review_rows, rows, strict=True):
      for member_index, item in enumerate(review_row.items):
        track_height = row.bounds[3] / len(review_row.items)
        y = row.bounds[1] + member_index * track_height + track_height * 0.25
        height = float(metric["timeline.mark.blockSize"])
        instance_id = (f"{review_row.row_id}:{item.item_id or item.object_id}"
                       if projection.rows else item.object_id)
        source_kind = item.source_kind if projection.rows else "combined"
        planned = item.planned
        planned_role = "snapshot" if source_kind == "snapshot" else "planned"
        if source_kind != "actual" and item.source_type == "point":
            x = coordinate(planned["at"])
            primitives.append(ScenePrimitive(f"planned:{instance_id}", "Symbol", item.object_id, "object", planned_role, planned_role,
                                             (x - height / 2, y, height, height), projection_instance_id=instance_id, shape="diamond", z_order=len(primitives)))
            mark_ports[instance_id] = ((x, y + height / 2), (x, y + height / 2))
        elif source_kind != "actual":
            x1, x2 = coordinate(planned["start"]), coordinate(planned["end"])
            primitives.append(ScenePrimitive(f"planned:{instance_id}", "Rect", item.object_id, "object", planned_role, planned_role,
                                             (x1, y, max(1.0, x2 - x1), height), projection_instance_id=instance_id, z_order=len(primitives)))
            mark_ports[instance_id] = ((x1, y + height / 2), (x2, y + height / 2))
        actual = item.actual or {}
        if source_kind in {"actual", "combined"} and item.source_type == "span" and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date):
            x1, x2 = coordinate(actual["start"]), coordinate(actual["finish"])
            primitives.append(ScenePrimitive(f"actual:{instance_id}", "Rect", item.object_id, "object", "actual", "actual",
                                             (x1, y + height * 1.25, max(1.0, x2 - x1), height), projection_instance_id=instance_id, z_order=len(primitives)))
        elif source_kind in {"actual", "combined"} and item.source_type == "point" and isinstance(actual.get("at"), date):
            x = coordinate(actual["at"])
            primitives.append(ScenePrimitive(f"actual:{instance_id}", "Symbol", item.object_id, "object", "actual", "actual",
                                             (x - height / 2, y + height * 1.25, height, height), projection_instance_id=instance_id, shape="diamond", z_order=len(primitives)))
        elif source_kind in {"actual", "combined"} and "missingActual" in (getattr(projection, "comparison_facets", ()) or ("missingActual",)):
            anchor_date = planned.get("end", planned.get("at"))
            anchor_x = coordinate(anchor_date) if isinstance(anchor_date, date) else row.bounds[0]
            primitives.append(ScenePrimitive(f"missing-actual:{instance_id}", "Rect", item.object_id, "object", "missingActual", "missing-actual",
                                             (anchor_x, y + height * 1.25, max(1.0, height * 1.5), height), projection_instance_id=instance_id, optional=True, z_order=len(primitives)))
        if projection.rows and value.surface_content.show_member_labels:
            label_at = planned.get("end", planned.get("at", planned.get("start")))
            if isinstance(label_at, date):
                text(f"member-label:{instance_id}", item.object_id, "member-label", "text",
                     item.title, coordinate(label_at) + height, y + height, typography_role="text")
        if source_kind == "combined" and item.finish_delta is not None:
            role = "variance-behind" if item.finish_delta > 0 else "variance-ahead" if item.finish_delta < 0 else "variance-on-track"
            text(f"variance:{instance_id}", item.object_id, "finish-delta", role,
                 f"{item.finish_delta:+d}d", coordinate(actual.get("finish", planned.get("end", planned.get("at")))), y + height, typography_role="summary")
    intervals = _fitting_axis(value, start, end, timeline)
    for interval in intervals:
        x = timeline.bounds[0] + (interval.start - start).days * scale.unit_ratio
        primitives.append(ScenePrimitive(f"axis:{interval.level}:{interval.index}", "Path", "timeline-axis", "axis", "axis-grid", "axis-major",
                                         (x, timeline.bounds[1], 0, timeline.bounds[3]), points=((x, axis.bounds[1]), (x, timeline.bounds[1] + timeline.bounds[3])), z_order=len(primitives)))
        label_width = value.font_metrics.width(interval.label, float(value.measured_sources.metric_values["text.body.size"]))
        clipped_width = (interval.end - interval.start).days * scale.unit_ratio
        if label_width <= clipped_width:
            text(f"axis-label:{interval.level}:{interval.index}", "timeline-axis", "axis-label", "text", interval.label, x, axis.bounds[1] + float(value.theme_tokens.typography("axis")[2]), typography_role="axis")
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
                route_obstacles = tuple((item.bounds[0], item.bounds[1], item.bounds[0] + item.bounds[2], item.bounds[1] + item.bounds[3])
                                        for item in rows
                                        if instance_rows.get(source_id) != instance_rows.get(target_id)
                                        or item.row_id != instance_rows.get(source_id))
                points = route_orthogonal(source_port, target_port, route_obstacles,
                    bounds=(timeline.bounds[0], timeline.bounds[1], timeline.bounds[0] + timeline.bounds[2], timeline.bounds[1] + timeline.bounds[3]))
                if len(points) < 2:
                    raise SceneBuildError("E_PRESENTATION_ROUTE_UNAVAILABLE", f"/relations/{relation.get('id', '')}")
                relation_id = str(relation.get("id", f"{source}-{target}"))
                scene_id = f"relation:{relation_id}:{source_id}:{target_id}" if projection.rows else f"relation:{relation_id}"
                primitives.append(ScenePrimitive(scene_id, "Path", relation_id, "relation", "dependency", "dependency",
                    (0, 0, 0, 0), shape=str(value.theme_tokens.token("dependency", "marker", "marker")), points=points,
                    from_port_id=f"{source_id}:end", to_port_id=f"{target_id}:start", z_order=len(primitives)))
    legend = by_source.get("legend")
    if legend:
        legend_size = float(value.theme_tokens.typography("legend")[2])
        swatch_size = max(2.0, legend_size * 0.8)
        for index, (role, label) in enumerate(value.surface_content.legend_entries):
            baseline = legend.bounds[1] + (index + 1) * legend_size
            primitives.append(ScenePrimitive(f"legend-swatch:{role}", "Rect", role, "legend", "legend-swatch", role,
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
        for panel_id, panel_title, metrics in value.surface_content.summary_panels:
            text(f"summary:{panel_id}", panel_id, "summary-header", "text", panel_title, summary_slot.bounds[0], summary_slot.bounds[1] + line * summary_size, typography_role="summary"); line += 1
            for key, metric_value in metrics:
                text(f"summary:{panel_id}:{key}", panel_id, "summary-metric", "text", f"{key}: {metric_value}", summary_slot.bounds[0], summary_slot.bounds[1] + line * summary_size, typography_role="summary"); line += 1
    annotation_slot = by_source.get("annotations")
    if annotation_slot:
        marks = _comparison_marks(projection)
        placed: list[LabelRect] = []
        for index, annotation in enumerate(value.surface_content.annotations):
            annotation_id, content = str(annotation.get("id", index)), str(annotation.get("text", ""))
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
            size, line_height = (float(item) for item in value.theme_tokens.typography("annotation")[2:])
            width, height = min(annotation_slot.bounds[2], max(size * 4, value.font_metrics.width(content, size))), size * line_height
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
            primitives.append(ScenePrimitive(f"annotation-box:{annotation_id}", "Rect", annotation_id, "annotation", "annotation-box", "annotation", bounds, z_order=len(primitives)))
            text(f"annotation-text:{annotation_id}", annotation_id, "annotation", "annotation-text", content, bounds[0], bounds[1] + size, typography_role="annotation")
            if box.leader_required:
                target = nearest_box_port(box.placement.bounds, (anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2))
                try:
                    points = route_annotation_leader((anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2), target,
                                                     obstacles=placed[:-1], limit=1024)
                except ValueError as error:
                    raise SceneBuildError(str(error), f"/annotations/{index}") from error
                primitives.append(ScenePrimitive(f"annotation-leader:{annotation_id}", "Path", annotation_id, "annotation", "annotation-leader", "annotation", (0, 0, 0, 0),
                                                 points=points, from_port_id=f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}", to_port_id=f"annotation-box:{annotation_id}", z_order=len(primitives)))
    return SceneSurface("table-timeline", slots, rows, tuple(groups), scale, tuple(primitives))


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


def _fitting_axis(value: SceneBuildInput, start: date, end: date, timeline: SceneSlot):
    for level in ("day", "week", "month", "quarter", "year"):
        intervals = axis_intervals(start, end, level)
        if all(value.font_metrics.width(item.label, float(value.measured_sources.metric_values["text.body.size"])) <= (item.natural_end - item.natural_start).days * timeline.bounds[2] / max(1, (end - start).days)
               for item in intervals):
            return intervals
    raise SceneBuildError("E_PRESENTATION_AXIS_OVERFLOW", "/layoutManifest/timeline-axis")
