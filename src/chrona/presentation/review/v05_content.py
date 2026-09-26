"""Current-resource normalization for v0.5 optional Scene content."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

from chrona.presentation.model.projection import ReviewProjection
from chrona.core.relation_identity import relation_identity
from chrona.presentation.model.surface_content import (
    AnnotationIntent, AxisLabelIntent, AxisTier, RelationPresentationFact, SummaryContent, SummaryPanel, SummaryTextRun, SurfaceContentInput, TableCellContent, TableColumnContent, TableColumnWidth, display_value, table_value,
)
from chrona.presentation.review.detail import resolve_v05_review_detail_profile
from chrona.presentation.layout.model import LayoutManifest
from chrona.presentation.contracts.resources import ReviewDetailInput, SummaryProfileInput, ViewInput
from chrona.presentation.model.color_scale import ResolvedColorScale
from chrona.presentation.model.axis_names import axis_name_table


def normalize_v05_surface_content(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput,
                                  *, actual_set: Mapping[str, Any] | None = None,
                                  detail: ReviewDetailInput | None = None, summary: SummaryContent,
                                  layout_manifest: LayoutManifest | None = None, locale: str = "en-US",
                                  color_scale: ResolvedColorScale | None = None) -> SurfaceContentInput:
    """Normalize current Project/View/profile facts without legacy Settings."""
    actual_body = _resource_body(actual_set, "ACTUAL_SET")
    columns = tuple(TableColumnContent(column.id, column.id, column.align, _column_width(column.width), column.header_orientation)
                    for column in view.table_columns)
    as_of = date.fromisoformat(str(actual_body["asOf"])) if isinstance(actual_body.get("asOf"), str) else None
    def cell(item: Any, column: Any, row_index: int) -> str:
        value = table_value(item, dict(project), column.source, row_index)
        if value is None and column.missing == "in-progress" and _is_actual_source(column.source):
            return _missing_actual_display(item, as_of)
        return display_value(value, column.missing, column.format, locale=locale)
    def cell_semantic(item: Any, column: Any) -> str:
        source = column.source
        facet = (source.get("comparisonFacet") if isinstance(source, Mapping) else None)
        if facet == "finishDelta" or (isinstance(source, Mapping) and source.get("facet") == "finishDelta"):
            delta = item.finish_delta
            return "tableVarianceBehind" if isinstance(delta, int) and delta > 0 else ("tableVarianceAhead" if isinstance(delta, int) and delta < 0 else ("tableVarianceOnTrack" if delta == 0 else "tableCell"))
        if facet == "missingActual" and not item.actual:
            return "missingActualCell"
        return "tableCell"
    def cell_typography_role(column: Any) -> str:
        return "numeric" if column.format == "signedDays" else "text"
    if projection.rows:
        cells = tuple(
            TableCellContent(row.row_id, column.id, cell(item := next(item for item in row.items if item.item_id == row.table_subject_id), column, row_index), cell_semantic(item, column), cell_typography_role(column))
            for row_index, row in enumerate(projection.rows, 1) for column in view.table_columns)
        table_cell_objects = tuple(
            (row.row_id, column.id,
             next(item for item in row.items if item.item_id == row.table_subject_id).object_id,
             next(item for item in row.items if item.item_id == row.table_subject_id).source_kind in {"primary", "combined"})
            for row in projection.rows for column in view.table_columns)
    else:
        cells = tuple(TableCellContent(item.object_id, column.id, cell(item, column, row_index), cell_semantic(item, column), cell_typography_role(column))
                      for row_index, item in enumerate(projection.items, 1) for column in view.table_columns)
        table_cell_objects = tuple((item.object_id, column.id, item.object_id, True)
                                   for item in projection.items for column in view.table_columns)
    visible = view.visibility
    group_presentation = view.grouping.presentation if view.grouping and view.grouping.presentation else "band"
    labels = visible.labels
    label_placement = "plot" if labels is True else "none"
    label_content: tuple[str, ...] = ("title",) if labels is True else ()
    label_side = "auto"
    label_fallback: tuple[str, ...] = ()
    annotation_fallback: tuple[str, ...] = ()
    link_mode = visible.links
    title_link_columns = tuple(column.id for column in view.table_columns if column.source == "title")
    # Legacy boolean visibility never declared a failure policy.  Preserve its
    # materializability by treating a rejected candidate as optional.
    label_overflow = "suppress" if labels is True else "visible-overflow"
    if isinstance(labels, Mapping):
        if "members" in labels:
            label_placement, label_content = ("plot", ("title",)) if labels["members"] else ("none", ())
        else:
            label_placement = str(labels["placement"])
            label_content = tuple(str(item) for item in labels["content"])
            label_side = str(labels["side"])
            label_overflow = str(labels.get("overflow", "visible-overflow"))
    if isinstance(visible.fallback, Mapping):
        label_fallback = tuple(str(item) for item in visible.fallback.get("labels", ()))
        annotation_fallback = tuple(str(item) for item in visible.fallback.get("annotations", ()))
    temporal = view.time_presentation or {}
    axis = view.axis or {}
    axis_tiers = tuple(_axis_tier(item, locale=locale) for item in axis.get("tiers", ()))
    project_body = project.get("project", {})
    calendar_id = project_body.get("calendar") if isinstance(project_body, Mapping) else None
    calendars = project.get("calendars", {})
    calendar = calendars.get(calendar_id, {}) if isinstance(calendars, Mapping) and isinstance(calendar_id, str) else {}
    fiscal_start_month = int(calendar.get("fiscalStartMonth", 1)) if isinstance(calendar, Mapping) else 1
    markers = view.markers
    as_of_value = actual_body.get("asOf")
    as_of_marker = next((item for item in markers if item.get("kind") == "asOf" and item.get("source") == "actual"), None)
    as_of = date.fromisoformat(as_of_value) if ((as_of_marker is not None) or temporal.get("asOf", "line") == "line") and isinstance(as_of_value, str) else None
    annotation_visibility = visible.annotations
    annotation_mode = annotation_visibility.get("mode", "none") if isinstance(annotation_visibility, Mapping) else annotation_visibility
    annotation_numbered = (isinstance(annotation_visibility, Mapping) and annotation_visibility.get("marker") == "numbered") or view.annotation_presentation == "numbered"
    relation_value = visible.relations
    relation_overflow = (str(relation_value.get("overflow", "visible-overflow"))
                         if isinstance(relation_value, Mapping) else "visible-overflow")
    relation_mode = relation_value.get("mode", "none") if isinstance(relation_value, Mapping) else relation_value
    relation_content = (tuple(str(item) for item in relation_value.get("content", ()))
                        if isinstance(relation_value, Mapping) else ())
    def relation_fact(relation: Mapping[str, Any], semantic_id: str) -> RelationPresentationFact:
        source, target = relation["from"], relation["to"]
        lag = relation.get("lag", "0d")
        return RelationPresentationFact(str(relation["id"]), str(source["object"]), str(source.get("endpoint", "end")),
                                        str(target["object"]), str(target.get("endpoint", "start")), lag,
                                        str(lag.get("calendar")) if isinstance(lag, Mapping) and lag.get("calendar") is not None else None,
                                        semantic_id, relation_content)
    if relation_mode == "critical":
        relations = tuple(relation_fact(relation, "dependency-critical")
                          for index, relation in enumerate(project.get("relations", ()))
                          if relation_identity(index, relation) in projection.driving_relations)
    elif relation_mode != "none":
        relations = tuple(relation_fact(relation, "dependency") for relation in project.get("relations", ()))
    else:
        relations = ()
    raw_annotations = view.annotations if annotation_mode != "none" else ()
    annotations = tuple(
        AnnotationIntent(str(annotation["id"]), str(annotation["purpose"]),
                         {str(key): str(value) for key, value in annotation["anchor"].items()},
                         str(annotation["placement"]["side"]), str(annotation["placement"]["alignment"]),
                         str(annotation["text"]), index + 1 if annotation_numbered else None,
                         annotation_fallback)
        for index, annotation in enumerate(raw_annotations)
    )
    notes = tuple((str(key), str(value.get("text", ""))) for key, value in project.get("annotations", {}).items())
    resolved_detail = (resolve_v05_review_detail_profile(_detail_mapping(detail), projection.items, layout_manifest,
                                                          profile_is_validated=True)
                       if layout_manifest is not None else None)
    legend = tuple((item.role, item.label) for item in detail.legend) if detail is not None else ()
    scale_paints: tuple[tuple[str, str], ...] = ()
    scale_legend_paints: tuple[tuple[str, str], ...] = ()
    if color_scale is not None:
        scale_paints = tuple((item.object_id, color_scale.color_for(item.object_id, item.fields))
                             for item in projection.items if item.source_kind in {"primary", "combined"})
        used = {item.fields.get(color_scale.source_field) for item in projection.items
                if isinstance(item.fields, Mapping) and item.source_kind in {"primary", "combined"}}
        scale_entries = tuple((f"scale:{color_scale.scale_id}:{value}", value)
                              for value in color_scale.domain if value in used)
        legend += scale_entries
        scale_legend_paints = tuple((f"scale:{color_scale.scale_id}:{value}", dict(color_scale.colors)[value])
                                    for value in color_scale.domain if value in used)
    calendar_closed, calendar_exceptions = _calendar_closures(project, projection.window, view.shading or {}, temporal)
    return SurfaceContentInput(table_columns=columns, table_cells=cells, relations=relations, annotations=annotations,
                               show_member_labels=label_placement in {"plot", "legacy"}, label_placement=label_placement, label_content=label_content,
                               label_side=label_side,
                               label_overflow=label_overflow, relation_overflow=relation_overflow,
                               group_presentation=group_presentation,
                               axis_tiers=axis_tiers, axis_fiscal_start_month=fiscal_start_month,
                               as_of=as_of, as_of_label=str(as_of_marker.get("label", "As of")) if as_of_marker else "As of",
                               annotation_numbered=annotation_numbered,
                               calendar_closed=calendar_closed, calendar_exceptions=calendar_exceptions,
                                   notes=notes, legend_entries=legend, coverage_text="",
                                   summary=summary,
                                   template_values=(),
                                   group_details=resolved_detail.group_details if resolved_detail else (),
                               milestones=resolved_detail.milestones if resolved_detail else (),
                               observation_columns=resolved_detail.observation_columns if resolved_detail else (),
                               observation_rows=resolved_detail.observation_rows if resolved_detail else (),
                               label_fallback=label_fallback, annotation_fallback=annotation_fallback,
                               link_mode=link_mode, title_link_columns=title_link_columns,
                               table_cell_objects=table_cell_objects,
                               scale_target_role=color_scale.target_role if color_scale else None,
                               scale_paints=scale_paints, scale_legend_paints=scale_legend_paints,
                               progress_fill_source=view.progress_fill,
                               table_hierarchy_column=view.hierarchy_column,
                               row_decoration=view.background_decoration[0],
                               group_decoration=view.background_decoration[1])


def _axis_tier(value: Mapping[str, Any], *, locale: str) -> AxisTier:
    """Detach one schema-validated View tier into Layout-owned typed intent."""
    role, unit = str(value["role"]), str(value["unit"])
    raw_label = value.get("label")
    if role != "labels" or not isinstance(raw_label, Mapping):
        return AxisTier(unit, int(value["every"]), role)
    candidates = raw_label.get("forms", {})
    candidate_forms = tuple((str(candidate), str(form)) for candidate, form in candidates.items()) if isinstance(candidates, Mapping) else ()
    table_id = str(raw_label.get("nameTable", locale))
    axis_name_table(table_id)
    return AxisTier(unit, int(value["every"]), role,
                    AxisLabelIntent(str(raw_label["form"]) if "form" in raw_label else None,
                                    candidate_forms, str(raw_label["align"]), str(raw_label["overflow"]),
                                    str(raw_label["orientation"]), table_id))


def _column_width(value: object) -> TableColumnWidth:
    """Translate schema-accepted width grammar into Layout's closed descriptor."""
    if value == "content":
        return TableColumnWidth("content", "content")
    if value == "fill":
        return TableColumnWidth("ellipsis", "fill", 1.0)
    if isinstance(value, Mapping) and "fr" in value:
        return TableColumnWidth("ellipsis", "fr", float(value["fr"]))
    if isinstance(value, Mapping) and "minmax" in value and isinstance(value["minmax"], Mapping):
        maximum = value["minmax"]["max"]
        if maximum == "content":
            return TableColumnWidth("content", "content")
        if maximum == "fill":
            return TableColumnWidth("content", "fill", 1.0)
        if isinstance(maximum, Mapping) and "fr" in maximum:
            return TableColumnWidth("content", "fr", float(maximum["fr"]))
    raise ValueError("E_VIEW_TABLE_WIDTH")


def _calendar_closures(project: Mapping[str, Any], window: tuple[date, date], shading: Mapping[str, Any],
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
    non_working = shading.get("nonWorking", temporal.get("calendarClosed", True)) if isinstance(shading, Mapping) else temporal.get("calendarClosed", True)
    exceptions_enabled = shading.get("exceptions", True) if isinstance(shading, Mapping) else True
    selected = tuple(closed) if non_working else tuple(exception_closed) if exceptions_enabled else ()
    return selected, tuple(exception_closed) if exceptions_enabled else ()


def _detail_mapping(detail: ReviewDetailInput | None) -> Mapping[str, Any] | None:
    """Adapt an accepted typed detail contract to the detail resolver's input shape."""
    if detail is None:
        return None
    # Detail contracts have already passed their resource-schema boundary.
    # Empty sections are absent presentation content, not a request for a
    # layout source; nonempty sections retain the immutable contract values.
    return {"body": {"legend": [{"role": item.role, "label": item.label} for item in detail.legend],
                      **({"groupDetails": detail.group_details} if detail.group_details else {}),
                      **({"milestones": detail.milestones} if detail.milestones else {}),
                      **({"observations": detail.observations} if detail.observations else {})}}


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



def normalize_summary_content(summary: SummaryProfileInput | None, projection: ReviewProjection,
                              actual_set: Mapping[str, Any] | None,
                              project: Mapping[str, Any] | None = None) -> SummaryContent:
    """Resolve summary-profile facts once, before source measurement and Layout."""
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
    for panel in summary.panels if summary is not None else ():
        runs = [SummaryTextRun(f"summary:{panel.id}", panel.id, panel.title or panel.id, "summary")]
        for definition in panel.metrics:
            if not isinstance(definition, tuple):
                metric_id, source, formatter = definition.id, definition.source, definition.format
                if isinstance(source, Mapping):
                    if source.get("actual") == "asOf":
                        source = "actual.asOf"
                    elif source.get("counts") == "finishDelta":
                        behind = sum(item.finish_delta > 0 for item in projection.items if item.finish_delta is not None)
                        ahead = sum(item.finish_delta < 0 for item in projection.items if item.finish_delta is not None)
                        values["counts.finishDelta"] = f"{behind} / {ahead}"
                        source = "counts.finishDelta"
                    elif source.get("scenario") in {"id", "title"}:
                        values[f"scenario.{source['scenario']}"] = _scenario_summary_value(
                            projection, project or {}, source["scenario"])
                        source = f"scenario.{source['scenario']}"
                    elif isinstance(source.get("object"), str) and source.get("facet") == "planned":
                        if definition.scope == "subtree":
                            values[f"object.{source['object']}.planned"] = _subtree_planned_completion(
                                projection, source["object"])
                        else:
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
                label = definition.label
                if panel.presentation == "figures":
                    runs.extend((
                        SummaryTextRun(f"summary:{panel.id}:{metric_id}:value", panel.id, rendered, "metric"),
                        SummaryTextRun(f"summary:{panel.id}:{metric_id}:caption", panel.id, label, "summary"),
                    ))
                else:
                    runs.append(SummaryTextRun(f"summary:{panel.id}:{metric_id}", panel.id,
                                                f"{label}: {rendered}", "summary"))
            else:
                metric_id, literal = definition
                runs.append(SummaryTextRun(f"summary:{panel.id}:{metric_id}", panel.id,
                                            f"{metric_id}: {literal}", "summary"))
        panels.append(SummaryPanel(panel.id, tuple(runs)))
    return SummaryContent(tuple(panels))


def _scenario_summary_value(projection: ReviewProjection, project: Mapping[str, Any], selector: str) -> str | None:
    """Resolve only Scenario identities that the View has actually selected."""
    scenario_ids = tuple(sorted({item.scenario_id for row in projection.rows for item in row.items
                                 if item.source_kind == "scenario" and item.scenario_id is not None}))
    if not scenario_ids:
        return None
    if selector == "id":
        return ", ".join(scenario_ids)
    declarations = project.get("scenarios", {})
    titles = tuple(declarations.get(item, {}).get("title") for item in scenario_ids
                   if isinstance(declarations, Mapping) and isinstance(declarations.get(item), Mapping))
    return ", ".join(titles) if len(titles) == len(scenario_ids) and all(isinstance(item, str) for item in titles) else None


def _subtree_planned_completion(projection: ReviewProjection, root_id: str) -> date:
    """Normalize one View-selected primary subtree into its planned completion."""
    if not projection.hierarchy_grouping:
        raise ValueError("E_PRESENTATION_SUMMARY_SOURCE")
    root = next((item for item in projection.items
                 if item.object_id == root_id and item.source_kind == "primary"), None)
    if root is None or not root.hierarchy_path:
        raise ValueError("E_PRESENTATION_SUMMARY_SOURCE")
    prefix = root.hierarchy_path
    members = tuple(item for item in projection.items
                    if item.source_kind == "primary" and item.hierarchy_path[:len(prefix)] == prefix)
    endpoints = tuple(item.planned.get("at", item.planned.get("end")) for item in members)
    known = tuple(value for value in endpoints if isinstance(value, date))
    if not known:
        raise ValueError("E_PRESENTATION_SUMMARY_SOURCE")
    return max(known)
