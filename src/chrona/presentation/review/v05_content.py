"""Current-resource normalization for v0.5 optional Scene content."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.model.surface_content import (
    SummaryContent, SummaryPanel, SummaryTextRun, SurfaceContentInput, display_value, table_value,
)
from chrona.presentation.review.detail import resolve_v05_review_detail_profile
from chrona.presentation.layout.model import LayoutManifest


def normalize_v05_surface_content(projection: ReviewProjection, project: Mapping[str, Any], view: Mapping[str, Any],
                                  *, actual_set: Mapping[str, Any] | None = None,
                                  detail: Mapping[str, Any] | None = None, summary: SummaryContent,
                                  layout_manifest: LayoutManifest | None = None, locale: str = "en-US") -> SurfaceContentInput:
    """Normalize current Project/View/profile facts without legacy Settings."""
    actual_body = _resource_body(actual_set, "ACTUAL_SET")
    detail_body = _resource_body(detail, "DETAIL_PROFILE")
    body = view.get("body", {})
    columns = tuple((str(column["id"]), str(column["id"])) for column in body.get("tableColumns", ()))
    as_of = date.fromisoformat(str(actual_body["asOf"])) if isinstance(actual_body.get("asOf"), str) else None
    def cell(item: Any, column: Mapping[str, Any], row_index: int) -> str:
        value = table_value(item, dict(project), column["source"], row_index)
        if value is None and column["missing"] == "in-progress" and _is_actual_source(column["source"]):
            return _missing_actual_display(item, as_of)
        return display_value(value, column["missing"], column.get("format", "text"), locale=locale)
    if projection.rows:
        cells = tuple(
            (row.row_id, str(column["id"]), cell(next(item for item in row.items if item.item_id == row.table_subject_id), column, row_index))
            for row_index, row in enumerate(projection.rows, 1) for column in body.get("tableColumns", ()))
    else:
        cells = tuple((item.object_id, str(column["id"]), cell(item, column, row_index))
                      for row_index, item in enumerate(projection.items, 1) for column in body.get("tableColumns", ()))
    visible = body.get("visibility", {})
    group_presentation = str(body.get("grouping", {}).get("presentation", "band"))
    labels = visible.get("labels", False)
    label_placement = "plot" if labels is True else "none"
    label_content: tuple[str, ...] = ("title",) if labels is True else ()
    label_side = "auto"
    # Legacy boolean visibility never declared a failure policy.  Preserve its
    # materializability by treating a rejected candidate as optional.
    label_overflow = "suppress" if labels is True else "diagnose"
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
    calendar_closed, calendar_exceptions = _calendar_closures(project, projection.window, body, temporal)
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
                               calendar_closed=calendar_closed, calendar_exceptions=calendar_exceptions,
                                   notes=notes, legend_entries=legend, coverage_text=str(body.get("coverageText", "")),
                                   summary=summary,
                                   template_values=tuple((str(key), str(value)) for key, value in body.get("templateValues", {}).items()),
                                   group_details=resolved_detail.group_details if resolved_detail else (),
                               milestones=resolved_detail.milestones if resolved_detail else (),
                               observation_columns=resolved_detail.observation_columns if resolved_detail else (),
                               observation_rows=resolved_detail.observation_rows if resolved_detail else ())


def _calendar_closures(project: Mapping[str, Any], window: tuple[date, date], body: Mapping[str, Any],
                       temporal: Mapping[str, Any]) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """Derive View-eligible closure and exception facts from the Project calendar."""
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
    closed, exception_closed = [], []
    while current < end:
        is_closed = not exceptions.get(current, names[current.weekday()] in working)
        if is_closed:
            closed.append(current)
            if current in exceptions:
                exception_closed.append(current)
        current += timedelta(days=1)
    shading = body.get("shading", {})
    non_working = shading.get("nonWorking", temporal.get("calendarClosed", True)) if isinstance(shading, Mapping) else temporal.get("calendarClosed", True)
    exceptions_enabled = shading.get("exceptions", True) if isinstance(shading, Mapping) else True
    selected = tuple(closed) if non_working else tuple(exception_closed) if exceptions_enabled else ()
    return selected, tuple(exception_closed) if exceptions_enabled else ()


def _resource_body(value: Mapping[str, Any] | None, name: str) -> Mapping[str, Any]:
    """Accept one current resource envelope; malformed optional input is not empty."""
    if value is None:
        return {}
    body = value.get("body") if isinstance(value, Mapping) else None
    if not isinstance(body, Mapping):
        raise ValueError(f"E_PRESENTATION_{name}_SHAPE")
    return body


def _is_actual_source(source: Any) -> bool:
    return isinstance(source, Mapping) and source.get("facet") == "actual"


def _missing_actual_display(item: Any, as_of: date | None) -> str:
    """Render absence as progress only for an active planned span at the cutoff."""
    planned = item.planned if hasattr(item, "planned") else {}
    start, end = planned.get("start"), planned.get("end")
    if (getattr(item, "source_type", None) == "span" and isinstance(start, date)
            and isinstance(end, date) and as_of is not None and start <= as_of < end):
        return "in progress"
    return "—"



def normalize_summary_content(summary: Mapping[str, Any] | None, projection: ReviewProjection,
                              actual_set: Mapping[str, Any] | None) -> SummaryContent:
    """Resolve summary-profile facts once, before source measurement and Layout."""
    summary_body = _resource_body(summary, "SUMMARY_PROFILE")
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
    panels: list[SummaryPanel] = []
    for panel in summary_body.get("panels", ()):
        runs = [SummaryTextRun(f"summary:{panel['id']}", str(panel["id"]),
                               str(panel.get("title", panel["id"])), "summary")]
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
                label = str(definition.get("label", metric_id))
                if panel.get("presentation", "lines") == "figures":
                    runs.extend((
                        SummaryTextRun(f"summary:{panel['id']}:{metric_id}:value", str(panel["id"]), rendered, "metric"),
                        SummaryTextRun(f"summary:{panel['id']}:{metric_id}:caption", str(panel["id"]), label, "summary"),
                    ))
                else:
                    runs.append(SummaryTextRun(f"summary:{panel['id']}:{metric_id}", str(panel["id"]),
                                                f"{label}: {rendered}", "summary"))
            else:
                runs.append(SummaryTextRun(f"summary:{panel['id']}:{metric_id}", str(panel["id"]),
                                            f"{metric_id}: {definition}", "summary"))
        panels.append(SummaryPanel(str(panel["id"]), tuple(runs)))
    return SummaryContent(tuple(panels))
