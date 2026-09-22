"""Current-resource normalization for v0.5 optional Scene content."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.model.surface_content import SurfaceContentInput, display_value, table_value
from chrona.presentation.review.detail import resolve_v05_review_detail_profile
from chrona.presentation.layout.model import LayoutManifest


def normalize_v05_surface_content(projection: ReviewProjection, project: Mapping[str, Any], view: Mapping[str, Any],
                                  *, actual_set: Mapping[str, Any] | None = None,
                                  detail: Mapping[str, Any] | None = None, summary: Mapping[str, Any] | None = None,
                                  layout_manifest: LayoutManifest | None = None) -> SurfaceContentInput:
    """Normalize current Project/View/profile facts without legacy Settings."""
    actual_body = _resource_body(actual_set, "ACTUAL_SET")
    detail_body = _resource_body(detail, "DETAIL_PROFILE")
    summary_body = _resource_body(summary, "SUMMARY_PROFILE")
    body = view.get("body", {})
    columns = tuple((str(column["id"]), str(column["id"])) for column in body.get("tableColumns", ()))
    if projection.rows:
        cells = tuple(
            (row.row_id, str(column["id"]),
             display_value(table_value(next(item for item in row.items if item.item_id == row.table_subject_id),
                                       dict(project), column["source"], row_index), column["missing"], column.get("format", "text")))
            for row_index, row in enumerate(projection.rows, 1) for column in body.get("tableColumns", ()))
    else:
        cells = tuple((item.object_id, str(column["id"]), display_value(table_value(item, dict(project), column["source"], row_index), column["missing"], column.get("format", "text")))
                      for row_index, item in enumerate(projection.items, 1) for column in body.get("tableColumns", ()))
    visible = body.get("visibility", {})
    group_presentation = str(body.get("grouping", {}).get("presentation", "band"))
    labels = visible.get("labels", False)
    label_placement = "legacy" if labels is True else "none"
    label_content: tuple[str, ...] = ("title",) if labels is True else ()
    label_side = "auto"
    label_overflow = "diagnose"
    if isinstance(labels, Mapping):
        if "members" in labels:
            label_placement, label_content = ("plot", ("title",)) if labels["members"] else ("none", ())
        else:
            label_placement = str(labels["placement"])
            label_content = tuple(str(item) for item in labels["content"])
            label_side = str(labels["side"])
            label_overflow = str(labels.get("overflow", "diagnose"))
    temporal = body.get("timePresentation", {})
    axis = body.get("axis", {})
    markers = body.get("markers", ())
    as_of_value = actual_body.get("asOf")
    as_of_marker = next((item for item in markers if item.get("kind") == "asOf" and item.get("source") == "actual"), None)
    as_of = date.fromisoformat(as_of_value) if ((as_of_marker is not None) or temporal.get("asOf", "line") == "line") and isinstance(as_of_value, str) else None
    annotation_visibility = visible.get("annotations", "none")
    annotation_mode = annotation_visibility.get("mode", "none") if isinstance(annotation_visibility, Mapping) else annotation_visibility
    annotation_numbered = (isinstance(annotation_visibility, Mapping) and annotation_visibility.get("marker") == "numbered") or body.get("annotationPresentation", "plain") == "numbered"
    relation_value = visible.get("relations", "none")
    relation_overflow = str(relation_value.get("overflow", "diagnose")) if isinstance(relation_value, Mapping) else "diagnose"
    relations = tuple(project.get("relations", ())) if (relation_value.get("mode", "none") if isinstance(relation_value, Mapping) else relation_value) != "none" else ()
    raw_annotations = tuple(body.get("annotations", ())) if annotation_mode != "none" else ()
    annotations = tuple({**annotation, "number": index + 1} for index, annotation in enumerate(raw_annotations)) if annotation_numbered else raw_annotations
    notes = tuple((str(key), str(value.get("text", ""))) for key, value in project.get("annotations", {}).items())
    resolved_detail = (resolve_v05_review_detail_profile(detail, projection.items, layout_manifest)
                       if layout_manifest is not None else None)
    legend = tuple((str(item["role"]), str(item["label"])) for item in detail_body.get("legend", ()))
    panels = _typed_summary_panels(summary_body, projection, actual_set)
    return SurfaceContentInput(table_columns=columns, table_cells=cells, relations=relations, annotations=annotations,
                               show_member_labels=label_placement in {"plot", "legacy"}, label_placement=label_placement, label_content=label_content,
                               label_side=label_side,
                               label_overflow=label_overflow, relation_overflow=relation_overflow,
                               group_presentation=group_presentation,
                               axis_level=str(temporal.get("axisLevel", "auto")),
                               axis_levels=tuple((str(item["unit"]), str(item["format"])) for item in axis.get("levels", ())),
                               axis_ticks=str(axis.get("ticks")) if axis.get("ticks") else None,
                               as_of=as_of, as_of_label=str(as_of_marker.get("label", "As of")) if as_of_marker else "As of",
                               annotation_numbered=annotation_numbered,
                               calendar_closed=_closed_calendar_days(project, projection.window) if body.get("shading", {}).get("nonWorking", temporal.get("calendarClosed", True)) else (),
                                   notes=notes, legend_entries=legend, coverage_text=str(body.get("coverageText", "")),
                                   summary_panels=panels,
                                   summary_presentations=tuple((str(item["id"]), str(item.get("presentation", "lines"))) for item in summary_body.get("panels", ())),
                                   template_values=tuple((str(key), str(value)) for key, value in body.get("templateValues", {}).items()),
                                   group_details=resolved_detail.group_details if resolved_detail else (),
                               milestones=resolved_detail.milestones if resolved_detail else (),
                               observation_columns=resolved_detail.observation_columns if resolved_detail else (),
                               observation_rows=resolved_detail.observation_rows if resolved_detail else ())


def _closed_calendar_days(project: Mapping[str, Any], window: tuple[date, date]) -> tuple[date, ...]:
    """Derive non-working calendar days from closed Project facts only."""
    calendar_id = project.get("project", {}).get("calendar")
    calendar = project.get("calendars", {}).get(calendar_id, {}) if isinstance(calendar_id, str) else {}
    working = set(calendar.get("working_days", ())) if isinstance(calendar, Mapping) else set()
    exceptions = {
        date.fromisoformat(str(entry["date"])): bool(entry["working"])
        for entry in calendar.get("exceptions", ())
        if isinstance(entry, Mapping) and entry.get("date") is not None and "working" in entry
    } if isinstance(calendar, Mapping) else {}
    names = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    current, end = window
    closed = []
    while current < end:
        if not exceptions.get(current, names[current.weekday()] in working):
            closed.append(current)
        current += timedelta(days=1)
    return tuple(closed)


def _resource_body(value: Mapping[str, Any] | None, name: str) -> Mapping[str, Any]:
    """Accept one current resource envelope; malformed optional input is not empty."""
    if value is None:
        return {}
    body = value.get("body") if isinstance(value, Mapping) else None
    if not isinstance(body, Mapping):
        raise ValueError(f"E_PRESENTATION_{name}_SHAPE")
    return body



def _typed_summary_panels(summary: Mapping[str, Any], projection: ReviewProjection,
                          actual_set: Mapping[str, Any] | None) -> tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...]:
    """Resolve summary-profile facts while keeping profiles free of copied values."""
    points = sorted(item.planned["at"] for item in projection.items
                    if item.source_type == "point" and isinstance(item.planned.get("at"), date))
    as_of_value = ((actual_set or {}).get("body") or {}).get("asOf")
    values: dict[str, Any] = {
        "actual.asOf": date.fromisoformat(as_of_value) if isinstance(as_of_value, str) else None,
        "planned.nextPoint": points[0] if points else None,
        "count.selected": len(projection.items),
        "count.missingActual": sum(not bool(item.actual) for item in projection.items),
        "count.knownFinishVariance": sum(item.finish_delta is not None for item in projection.items),
    }
    panels = []
    for panel in summary.get("panels", ()):
        metrics = []
        declared = panel.get("metrics", {})
        entries = declared.items() if isinstance(declared, Mapping) else ((item["id"], item) for item in declared)
        for metric_id, definition in entries:
            if isinstance(definition, Mapping):
                source, formatter = definition.get("source"), definition.get("format", "text")
                if isinstance(source, Mapping):
                    if source.get("actual") == "asOf":
                        source = "actual.asOf"
                    elif source.get("counts") == "finishDelta":
                        behind = sum(item.finish_delta > 0 for item in projection.items if item.finish_delta is not None)
                        ahead = sum(item.finish_delta < 0 for item in projection.items if item.finish_delta is not None)
                        values["counts.finishDelta"] = f"{behind} / {ahead}"
                        source = "counts.finishDelta"
                    elif isinstance(source.get("object"), str) and source.get("facet") == "planned":
                        selected = next((item for item in projection.items if item.object_id == source["object"]), None)
                        planned = selected.planned if selected is not None else {}
                        values[f"object.{source['object']}.planned"] = planned.get("at", planned.get("end"))
                        source = f"object.{source['object']}.planned"
                if source not in values:
                    raise ValueError("E_PRESENTATION_SUMMARY_SOURCE")
                if formatter not in {"text", "date", "count", "signedDays"}:
                    raise ValueError("E_PRESENTATION_SUMMARY_FORMAT")
                raw = values[source]
                rendered = "unknown" if raw is None else (
                    raw.isoformat() if formatter == "date" and isinstance(raw, date)
                    else f"{raw:+d}d" if formatter == "signedDays" and isinstance(raw, int)
                    else str(raw)
                )
                metrics.append((str(definition.get("label", metric_id)), rendered))
            else:
                metrics.append((str(metric_id), str(definition)))
        panels.append((str(panel["id"]), str(panel.get("title", panel["id"])), tuple(metrics)))
    return tuple(panels)
