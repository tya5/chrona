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
from chrona.presentation.layout.model import LayoutManifest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneGroup, ScenePrimitive, SceneRow, SceneSlot, SceneSurface, SurfaceScaleManifest, TextLayout


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
                            (float(item.bounds.inline), float(item.bounds.block), float(item.bounds.inline_size), float(item.bounds.block_size)) )
                  for source, item in sorted(decisions.items()))
    by_source = {slot.source: slot for slot in slots}
    table, timeline, axis, title_slot = (by_source[name] for name in ("table", "timeline", "timeline-axis", "title"))
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    row_height = timeline.bounds[3] / max(1, len(projection.items))
    minimum = float(metric["timeline.row.minBlockSize"])
    if row_height < minimum:
        raise SceneBuildError("E_LAYOUT_REQUIRED_OVERFLOW", "/layoutManifest/timeline")
    rows = tuple(SceneRow(item.object_id, item.group_id,
                          (timeline.bounds[0], timeline.bounds[1] + index * row_height, timeline.bounds[2], row_height))
                 for index, item in enumerate(projection.items))
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
    font_size, line_height = float(metric["text.body.size"]), float(metric["text.body.lineHeight"])
    family = value.theme_tokens.font_family()
    title = value.measured_sources.inputs["title"].lines[0] if value.measured_sources.inputs.get("title") and value.measured_sources.inputs["title"].lines else ""
    primitives: list[ScenePrimitive] = []
    def text(scene_id: str, source: str, purpose: str, role: str, content: str, x: float, y: float) -> None:
        layout = TextLayout((x, y - font_size, value.font_metrics.width(content, font_size), font_size * line_height),
                            (x, y), (content,), family, 400, value.font_metrics.content_identity)
        primitives.append(ScenePrimitive(scene_id, "Text", source, "review", purpose, role, layout.bounds,
                                         text=content, baseline=layout.baseline, text_layout=layout, z_order=len(primitives)))
    text("title", "title", "title-text", "text", title, title_slot.bounds[0], title_slot.bounds[1] + font_size)
    column_width = table.bounds[2] / max(1, len(value.surface_content.table_columns))
    for index, (column_id, label) in enumerate(value.surface_content.table_columns):
        text(f"column:{column_id}", "view:tableColumns", "table-column-label", "text", label,
             table.bounds[0] + index * column_width, table.bounds[1] + font_size)
    for object_id, column_id, cell in value.surface_content.table_cells:
        row = next((item for item in rows if item.object_id == object_id), None)
        index = next((offset for offset, value in enumerate(value.surface_content.table_columns) if value[0] == column_id), None)
        if row is not None and index is not None:
            text(f"cell:{object_id}:{column_id}", object_id, "table-cell", "text", cell,
                 table.bounds[0] + index * column_width, row.bounds[1] + row.bounds[3] / 2 + font_size / 2)
    for group in groups:
        primitives.append(ScenePrimitive(f"group:{group.group_id}", "Rect", group.group_id, "group", "group-decoration", "group-band",
                                         group.content_bounds, opacity=0.12, z_order=len(primitives)))
    def coordinate(at: date) -> float:
        return timeline.bounds[0] + (at - start).days * scale.unit_ratio
    for item, row in zip(projection.items, rows, strict=True):
        y = row.bounds[1] + row.bounds[3] * 0.25
        height = max(2.0, row.bounds[3] * 0.2)
        planned = item.planned
        if item.source_type == "point":
            x = coordinate(planned["at"])
            primitives.append(ScenePrimitive(f"planned:{item.object_id}", "Symbol", item.object_id, "object", "planned", "planned",
                                             (x - height / 2, y, height, height), shape="diamond", z_order=len(primitives)))
        else:
            x1, x2 = coordinate(planned["start"]), coordinate(planned["end"])
            primitives.append(ScenePrimitive(f"planned:{item.object_id}", "Rect", item.object_id, "object", "planned", "planned",
                                             (x1, y, max(1.0, x2 - x1), height), z_order=len(primitives)))
        actual = item.actual or {}
        if item.source_type == "span" and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date):
            x1, x2 = coordinate(actual["start"]), coordinate(actual["finish"])
            primitives.append(ScenePrimitive(f"actual:{item.object_id}", "Rect", item.object_id, "object", "actual", "actual",
                                             (x1, y + height * 1.25, max(1.0, x2 - x1), height), z_order=len(primitives)))
        elif item.source_type == "point" and isinstance(actual.get("at"), date):
            x = coordinate(actual["at"])
            primitives.append(ScenePrimitive(f"actual:{item.object_id}", "Symbol", item.object_id, "object", "actual", "actual",
                                             (x - height / 2, y + height * 1.25, height, height), shape="diamond", z_order=len(primitives)))
        else:
            primitives.append(ScenePrimitive(f"missing-actual:{item.object_id}", "Rect", item.object_id, "object", "missingActual", "missing-actual",
                                             (row.bounds[0], y + height * 1.25, max(1.0, row.bounds[2] * 0.04), height), optional=True, z_order=len(primitives)))
        if item.finish_delta is not None:
            role = "variance-behind" if item.finish_delta > 0 else "variance-ahead" if item.finish_delta < 0 else "variance-on-track"
            text(f"variance:{item.object_id}", item.object_id, "finish-delta", role,
                 f"{item.finish_delta:+d}d", coordinate(actual.get("finish", planned.get("end", planned.get("at")))), y + height)
    intervals = _fitting_axis(value, start, end, timeline)
    for interval in intervals:
        x = timeline.bounds[0] + (interval.start - start).days * scale.unit_ratio
        primitives.append(ScenePrimitive(f"axis:{interval.level}:{interval.index}", "Path", "timeline-axis", "axis", "axis-grid", "axis-major",
                                         (x, timeline.bounds[1], 0, timeline.bounds[3]), points=((x, axis.bounds[1]), (x, timeline.bounds[1] + timeline.bounds[3])), z_order=len(primitives)))
        text(f"axis-label:{interval.level}:{interval.index}", "timeline-axis", "axis-label", "text", interval.label, x, axis.bounds[1] + font_size)
    anchors = {row.object_id: (row.bounds[0] + row.bounds[2], row.bounds[1] + row.bounds[3] / 2) for row in rows}
    obstacles = tuple(row.bounds for row in rows)
    for relation in value.surface_content.relations:
        source = relation.get("from", {}).get("object")
        target = relation.get("to", {}).get("object")
        if source in anchors and target in anchors:
            points = route_orthogonal(anchors[source], anchors[target], obstacles, bounds=(timeline.bounds[0], timeline.bounds[1], timeline.bounds[0] + timeline.bounds[2], timeline.bounds[1] + timeline.bounds[3]))
            primitives.append(ScenePrimitive(f"relation:{relation.get('id', source + '-' + target)}", "Path", str(relation.get("id", "")), "relation", "dependency", "dependency",
                                             (0, 0, 0, 0), points=points, from_port_id=f"{source}:end", to_port_id=f"{target}:start", z_order=len(primitives)))
    legend = by_source.get("legend")
    if legend:
        for index, (role, label) in enumerate(value.surface_content.legend_entries):
            text(f"legend:{role}", role, "legend-label", "text", label, legend.bounds[0], legend.bounds[1] + (index + 1) * font_size)
    notes = by_source.get("notes")
    if notes:
        for index, (note_id, content) in enumerate(value.surface_content.notes):
            text(f"note:{note_id}", note_id, "project-note", "text", content, notes.bounds[0], notes.bounds[1] + (index + 1) * font_size)
    return SceneSurface("table-timeline", slots, rows, tuple(groups), scale, tuple(primitives))


def _fitting_axis(value: SceneBuildInput, start: date, end: date, timeline: SceneSlot):
    for level in ("day", "week", "month", "quarter", "year"):
        intervals = axis_intervals(start, end, level)
        if all(value.font_metrics.width(item.label, float(value.measured_sources.metric_values["text.body.size"])) <= (item.end - item.start).days * timeline.bounds[2] / max(1, (end - start).days)
               for item in intervals):
            return intervals
    raise SceneBuildError("E_PRESENTATION_AXIS_OVERFLOW", "/layoutManifest/timeline-axis")
