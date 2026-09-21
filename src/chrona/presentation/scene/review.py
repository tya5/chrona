"""Renderer-neutral composition of the table/timeline review Scene."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping

from chrona.presentation.scene.model import ScenePrimitive


@dataclass(frozen=True)
class ReviewScene:
    """A fully measured Scene that renderers may serialize but not reinterpret."""

    width: float
    height: float
    title: str
    description: str
    primitives: tuple[ScenePrimitive, ...]


@dataclass(frozen=True)
class SlotRect:
    """Physical slot rectangle handed from the Layout Manifest to composition."""

    x: float
    y: float
    width: float
    height: float


def compose_review_scene(title: str, projection: Any, project: Mapping[str, Any],
                         view: Mapping[str, Any], slots: Mapping[str, Any], *,
                         viewport: tuple[float, float], metric_values: Mapping[str, Any],
                         font_metrics: Any) -> ReviewScene:
    """Compose source-linked primitives from one frozen measurement/layout result."""
    table, timeline, axis, title_slot = slots["table"], slots["timeline"], slots["timeline-axis"], slots["title"]
    if table.y + axis.height != timeline.y or table.y + table.height != timeline.y + timeline.height:
        raise ValueError("E_GANTT_ROW_ALIGNMENT")
    font_size = float(metric_values["text.body.size"])
    line_height = font_size * float(metric_values["text.body.lineHeight"])
    advance = float(metric_values["text.measuredAverageAdvance"])
    edge = advance * 2
    row_count = max(1, len(projection.items))
    row_height = timeline.height / row_count
    if row_height < float(metric_values["timeline.row.minBlockSize"]):
        raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:rows")
    bar_height = font_size
    bar_gap = max(0.0, (row_height - 2 * bar_height) / 3)
    start, end = projection.window
    days = max(1, (end - start).days)

    def scale(value: Any) -> float:
        return timeline.x + edge + (value - start).days / days * (timeline.width - edge * 2)

    primitives: list[ScenePrimitive] = []

    def add(kind: str, scene_id: str, source: str, purpose: str,
            bounds: tuple[float, float, float, float], *, role: str,
            text: str | None = None, weight: int = 400,
            points: tuple[tuple[float, float], ...] = ()) -> None:
        baseline = (bounds[0], bounds[1]) if kind == "text" else None
        primitives.append(ScenePrimitive(
            scene_id=scene_id, kind=kind, source_ref=source, source_kind="review",
            semantic_facet=purpose, visual_role=role, bounds=bounds, purpose=purpose,
            text=text, baseline=baseline, shape=str(weight) if kind == "text" else None,
            points=points, z_order=len(primitives),
        ))

    width, height = viewport
    add("rect", "background", "project", "background", (0, 0, width, height), role="background")
    add("text", "heading", "project", "heading", (title_slot.x, title_slot.y + font_size, 0, 0),
        role="text", text=title, weight=700)
    add("rect", "table-header", "timeline-axis", "table-header",
        (table.x, table.y, timeline.x + timeline.width - table.x, axis.height), role="table-header")
    columns = view.get("body", {}).get("tableColumns", ({"id": "Activity", "source": "title"},))
    column_width = table.width / max(1, len(columns))
    for index, column in enumerate(columns):
        add("text", f"table-header-{index}", "view:tableColumns", "table-header",
            (table.x + edge + index * column_width, table.y + axis.height - line_height / 3, 0, 0),
            role="text", text=str(column["id"]), weight=700)

    cursor = start
    tick = 0
    while cursor <= end:
        x = scale(cursor)
        add("line", f"axis-grid-{tick}", "timeline-axis", "axis-grid", (0, 0, 0, 0),
            role="axis-major", points=((x, axis.y), (x, timeline.y + timeline.height)))
        add("text", f"axis-label-{tick}", "timeline-axis", "axis-label",
            (x + advance / 2, axis.y + font_size, 0, 0), role="text", text=cursor.isoformat())
        cursor += timedelta(days=28)
        tick += 1

    anchors: dict[str, tuple[float, float]] = {}
    for index, item in enumerate(projection.items):
        row_top = timeline.y + index * row_height
        baseline = row_top + (row_height + font_size) / 2
        values = item.fields | {"title": item.title}
        for column_index, column in enumerate(columns):
            source = column.get("source", "title")
            key = source.get("field") if isinstance(source, Mapping) else source
            value = values.get(key, column.get("missing", "—"))
            add("text", f"cell-{item.object_id}-{column_index}", item.object_id, "table-cell",
                (table.x + edge + column_index * column_width, baseline, 0, 0), role="text", text=str(value))
        if item.source_type == "point":
            x, y, radius = scale(item.planned["at"]), row_top + row_height / 2, bar_height / 2
            add("polygon", f"planned-{item.object_id}", item.object_id, "planned", (0, 0, 0, 0),
                role="planned", points=((x, y-radius), (x+radius, y), (x, y+radius), (x-radius, y)))
            anchors[item.object_id] = (x, y)
        else:
            x1, x2 = scale(item.planned["start"]), scale(item.planned["end"])
            y = row_top + bar_gap
            add("rect", f"planned-{item.object_id}", item.object_id, "planned",
                (x1, y, max(advance, x2-x1), bar_height), role="planned")
            anchors[item.object_id] = (x2, y + bar_height / 2)
            if item.actual and "finish" in item.actual:
                ax1, ax2 = scale(item.actual.get("start", item.planned["start"])), scale(item.actual["finish"])
                add("rect", f"actual-{item.object_id}", item.object_id, "actual",
                    (ax1, y + bar_height + bar_gap, max(advance, ax2-ax1), bar_height), role="actual")

    for relation in project.get("relations", ()):
        source, target = relation.get("from", {}).get("object"), relation.get("to", {}).get("object")
        if source not in anchors or target not in anchors:
            continue
        relation_id = str(relation.get("id", f"{source}-{target}"))
        add("line", f"relation-{relation_id}", relation_id, "routed-connector", (0, 0, 0, 0),
            role="dependency", points=(anchors[source], anchors[target]))

    notes = slots.get("notes")
    if notes:
        y = notes.y + font_size
        for annotation_id, annotation in project.get("annotations", {}).items():
            value = str(annotation.get("text", ""))
            if font_metrics.width(value, font_size) > notes.width or y > notes.y + notes.height:
                raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:notes")
            add("text", f"annotation-{annotation_id}", annotation_id, "presentation-annotation",
                (notes.x, y, 0, 0), role="text", text=value)
            y += line_height
    return ReviewScene(width, height, title,
                       f"Plan and Actual comparison; {len(projection.items)} selected items.",
                       tuple(primitives))
