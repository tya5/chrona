"""Current-resource normalization for v0.5 optional Scene content."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Mapping

from chrona.presentation.model.projection import ObservationState, ReviewProjection
from chrona.core.relation_identity import relation_identity
from chrona.presentation.model.surface_content import (
    AnnotationIntent, AxisLabelIntent, AxisSecondaryIntent, AxisTier, HeadingContent, RelationPresentationFact, SummaryContent, SummaryPanel, SummaryTextRun, SurfaceContentInput, TableCellContent, TableColumnContent, TableColumnWidth, TableContent, TableRowLevel, _format_compact_date, display_value, table_value,
)
from chrona.presentation.table_presentation import affix_state
from chrona.presentation.review.detail import normalize_v05_review_detail_profile
from chrona.presentation.review.figure_facts import projected_counts
from chrona.presentation.model.placement_candidates import legacy_candidate_order, parse_candidates
from chrona.presentation.contracts.resources import ReviewDetailInput, SummaryProfileInput, ViewInput
from chrona.presentation.group_header_text import GroupHeaderTextError, compose_group_header_runs, compose_group_headers
from chrona.presentation.heading_text import render_heading
from chrona.presentation.model.color_scale import ResolvedColorScale
from chrona.presentation.model.axis_names import axis_name_table
from chrona.presentation.model.axis_color_scale import AxisBandFillSpec, AxisBandScaleError


def _diagnostic_value(value: object) -> str:
    """Bound diagnostic operands; avoid including arbitrary resource bodies."""
    if isinstance(value, (str, int, float, bool, type(None))):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    if isinstance(value, (tuple, list)):
        parts = [_diagnostic_value(part) for part in value[:8]]
        return "[" + ", ".join(parts) + (", ..." if len(value) > 8 else "") + "]"
    return f"<{type(value).__name__}>"


def cell_typography_role(column: Any) -> str:
    """Return the typography role in which one View table column's cells are set (`textRole`, #1062, else by format)."""
    if getattr(column, "text_role", None) is not None:
        return column.text_role
    return "numeric" if column.format in {"signedDays", "signedNumber"} else "text"


def normalize_v05_table_content(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput,
                                *, actual_set: Mapping[str, Any] | None = None,
                                locale: str = "en-US") -> TableContent:
    """Normalize the table once so measurement and composition read the same cells."""
    if getattr(view.rows.mode, "value", view.rows.mode) == "lanes":
        return _lane_table_content(projection, project, view)
    actual_body = _resource_body(actual_set, "ACTUAL_SET")
    columns = tuple(TableColumnContent(column.id, column.id, column.align, _column_width(column.width), column.header_orientation,
                                       text_wrap=column.text_wrap)
                    for column in view.table_columns)
    as_of = date.fromisoformat(str(actual_body["asOf"])) if isinstance(actual_body.get("asOf"), str) else None
    def cell_parts(item: Any, column: Any, row_index: int) -> tuple[str, str, str]:
        """The cell's (prefix, core, suffix): the affix of its state wraps the formatted text (#588)."""
        value = table_value(item, dict(project), column.source, row_index)
        missing = column.missing
        if value is None and column.missing_by:
            # The text of an absent value follows the item's observation state when the column declares it (#991).
            declared = column.missing_by.get(_absence_state(item), missing)
            missing = declared if isinstance(declared, Mapping) else str(declared)
        if value is None and missing == "in-progress" and _is_actual_source(column.source):
            core = _missing_actual_display(item, as_of)
        else:
            core = display_value(value, missing, column.format, locale=locale, zero=column.zero,
                                 end_display=column.end_display)
        affix = column.affixes.for_state(affix_state(value, column.format)) if column.affixes is not None else None
        return (affix.prefix, core, affix.suffix) if affix is not None else ("", core, "")

    def cell(item: Any, column: Any, row_index: int) -> str:
        prefix, core, suffix = cell_parts(item, column, row_index)
        return prefix + core + suffix

    def cell_affixes(item: Any, column: Any, row_index: int) -> tuple[str, str]:
        prefix, _, suffix = cell_parts(item, column, row_index)
        return prefix, suffix
    def cell_semantic(item: Any, column: Any) -> str:
        source = column.source
        facet = (source.get("comparisonFacet") if isinstance(source, Mapping) else None)
        if facet == "finishDelta" or (isinstance(source, Mapping) and source.get("facet") == "finishDelta"):
            delta = item.finish_delta
            return "tableVarianceBehind" if isinstance(delta, int) and delta > 0 else ("tableVarianceAhead" if isinstance(delta, int) and delta < 0 else ("tableVarianceOnTrack" if delta == 0 else "tableCell"))
        if facet == "missingActual" and item.observation_state == ObservationState.DUE_UNOBSERVED:
            return "missingActualCell"
        return "tableCell"
    if projection.rows:
        cells = tuple(
            TableCellContent(row.row_id, column.id, cell(item := next(item for item in row.items if item.item_id == row.table_subject_id), column, row_index), cell_semantic(item, column), cell_typography_role(column), *cell_affixes(item, column, row_index))
            for row_index, row in enumerate(projection.rows, 1) for column in view.table_columns)
        table_cell_objects = tuple(
            (row.row_id, column.id,
             next(item for item in row.items if item.item_id == row.table_subject_id).object_id,
             next(item for item in row.items if item.item_id == row.table_subject_id).source_kind in {"primary", "combined"})
            for row in projection.rows for column in view.table_columns)
        row_levels = tuple(TableRowLevel((row.row_id, row.table_subject_id), bool(row.group_id), row.depth)
                           for row in projection.rows)
    else:
        cells = tuple(TableCellContent(item.object_id, column.id, cell(item, column, row_index), cell_semantic(item, column), cell_typography_role(column), *cell_affixes(item, column, row_index))
                      for row_index, item in enumerate(projection.items, 1) for column in view.table_columns)
        table_cell_objects = tuple((item.object_id, column.id, item.object_id, True)
                                   for item in projection.items for column in view.table_columns)
        row_levels = tuple(TableRowLevel((item.object_id,), bool(item.group_id)) for item in projection.items)
    return TableContent(columns, cells, table_cell_objects, view.hierarchy_column, row_levels,
                        indent_under_headers=_indents_under_headers(view))


def _indents_under_headers(view: ViewInput) -> bool:
    """True when each row of a header group sits one declared step under its header (#1065).

    A hierarchy column with field (non-hierarchy) grouping shown as headers and no other nesting: hierarchy
    grouping, a row `depth` or a `parentRow` keep their own rule, so their output does not change.
    """
    grouping = view.grouping
    return (view.hierarchy_column is not None and grouping is not None and grouping.by != "hierarchy"
            and grouping.presentation == "header"
            and not any(row.depth > 0 or row.parent_row is not None for row in view.rows.items))


def _lane_table_content(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput) -> TableContent:
    """Build exact lane summary cells solely from the immutable membership projection."""
    lane_table = view.rows.lane_table
    if projection.lane_membership is None or not projection.lane_rows or lane_table is None:
        raise ValueError(f"E_REVIEW_LANE_TABLE_PROJECTION: laneMembership={projection.lane_membership is not None}, laneRows={len(projection.lane_rows)}, laneTable={lane_table is not None}")
    columns = (TableColumnContent("Lane", "Lane", "start", TableColumnWidth("content", "content"),
                                  text_wrap=lane_table.text_wrap),)
    if lane_table.count:
        columns += (TableColumnContent("Items", "Items", "end", TableColumnWidth("content", "content"),
                                       text_wrap=lane_table.text_wrap),)
    entities = project.get("entities", {})
    cells = []
    levels = []
    lanes_by_id = {lane.lane_id: lane for lane in projection.lane_membership.lanes}
    rows_by_group: dict[str, list[Any]] = {}
    for row in projection.lane_rows:
        rows_by_group.setdefault(row.group_id, []).append(row)
    disambiguate_groups = {
        group_id for group_id, group_rows in rows_by_group.items()
        if sum(len(row.member_item_ids) > 1 for row in group_rows) > 1
    }
    seen_groups: set[str] = set()

    def group_title(group_id: str, row: Any) -> str:
        group = entities.get(group_id, {}) if isinstance(entities, Mapping) else {}
        title = group.get("title") if isinstance(group, Mapping) else None
        if not isinstance(title, str) or not title.strip() or title == group_id:
            title = next((item.group_label for item in row.items
                          if item.group_label and item.group_label != group_id), None)
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"E_REVIEW_LANE_TITLE_MISSING:{group_id}: /entities/{_diagnostic_value(group_id)}/title is missing or aliases its id; expected nonblank display title")
        return title

    def member_title(member_id: str, row: Any) -> str:
        item = next((item for item in row.items if item.item_id == member_id), None)
        if item is None or not item.title.strip() or item.title in {item.object_id, item.item_id}:
            raise ValueError(f"E_REVIEW_LANE_TITLE_MISSING:{member_id}: /items/{_diagnostic_value(member_id)}/title={_diagnostic_value(None if item is None else item.title)}; expected distinct nonblank display title")
        return item.title

    for row in projection.lane_rows:
        lane = lanes_by_id.get(row.lane_id)
        if lane is None:
            raise ValueError(f"E_REVIEW_LANE_TABLE_PROJECTION: laneId={_diagnostic_value(row.lane_id)} is absent from membership lanes")
        if lane_table.label.value == "group":
            label = group_title(row.group_id, row) if row.group_id and row.group_id not in seen_groups else ""
            seen_groups.add(row.group_id)
        else:
            if not lane.member_item_ids:
                raise ValueError(f"E_REVIEW_LANE_TABLE_PROJECTION: laneId={_diagnostic_value(lane.lane_id)} has no memberItemIds for label={_diagnostic_value(lane_table.label.value)}")
            first_title = member_title(lane.member_item_ids[0], row)
            if len(lane.member_item_ids) == 1:
                label = first_title
            elif not row.group_id:
                label = first_title
            else:
                label = group_title(row.group_id, row)
                if row.group_id in disambiguate_groups:
                    label = f"{label} — {first_title}"
        cells.append(TableCellContent(row.lane_id, "Lane", label, "tableCell"))
        if lane_table.count:
            member_count = len(lane.member_item_ids)
            cells.append(TableCellContent(row.lane_id, "Items", str(member_count), "tableCell", "numeric"))
        levels.append(TableRowLevel((row.lane_id,), bool(row.group_id)))
    return TableContent(columns, tuple(cells), (), None, tuple(levels))


def _used_scale_values(color_scale: ResolvedColorScale, projection: ReviewProjection) -> set[Any]:
    return {item.fields.get(color_scale.source_field) for item in projection.items
            if isinstance(item.fields, Mapping) and item.source_kind in {"primary", "combined"}}


CALENDAR_CLOSED_LEGEND_ROLE = "calendar-closed"


def legend_entries(detail: ReviewDetailInput | None, project: Mapping[str, Any], projection: ReviewProjection,
                   color_scale: ResolvedColorScale | None, *, closed_days_drawn: bool) -> tuple[tuple[str, str], ...]:
    """Return the legend entries, `(role, label)`, exactly as Layout draws them (#497).

    The Detail Profile's own entries come first; a colour scale then adds one entry per
    value in use, labelled with the entity's declared title when the Project has one.
    Layout measures the legend slot and draws the legend from this one list. The closed-day key
    is a key for a band on the plot, so it is listed only when a closed day is drawn (#893).
    """
    entries = tuple((item.role, item.label) for item in detail.legend
                    if closed_days_drawn or item.role != CALENDAR_CLOSED_LEGEND_ROLE) if detail is not None else ()
    if color_scale is None:
        return entries
    used = _used_scale_values(color_scale, projection)
    entities = project.get("entities", {})
    return entries + tuple(
        (f"scale:{color_scale.scale_id}:{value}", str(entities.get(value, {}).get("title", value)))
        for value in color_scale.domain if value in used)


def normalize_v05_surface_content(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput,
                                  *, actual_set: Mapping[str, Any] | None = None,
                                  detail: ReviewDetailInput | None = None, summary: SummaryContent,
                                  locale: str = "en-US",
                                  color_scale: ResolvedColorScale | None = None,
                                  table: TableContent | None = None,
                                  group_tints: tuple[tuple[str, str], ...] = (),
                                  annotation_kind_colors: Mapping[str, str] | None = None,
                                  annotation_kind_also: Mapping[str, tuple[str, ...]] | None = None) -> SurfaceContentInput:
    """Normalize current Project/View/profile facts without legacy Settings."""
    if table is None:
        table = normalize_v05_table_content(projection, project, view, actual_set=actual_set, locale=locale)
    actual_body = _resource_body(actual_set, "ACTUAL_SET")
    columns, cells, table_cell_objects = table.columns, table.cells, table.cell_objects
    visible = view.visibility
    lane_mode = getattr(view.rows.mode, "value", view.rows.mode) == "lanes"
    group_presentation = view.grouping.presentation if view.grouping and view.grouping.presentation else "band"
    labels = visible.labels
    label_placement = "plot" if labels is True else "none"
    label_content: tuple[str, ...] = ("title",) if labels is True else ()
    label_side = "auto"
    label_text_role: str | None = None
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
            # ``both`` is ``plot`` plus a table title column the View validator already required.
            label_placement = "plot" if labels["placement"] == "both" else str(labels["placement"])
            label_content = tuple(str(item) for item in labels.get(
                "content", ("title", "finishDelta") if lane_mode else ()))
            label_side = str(labels.get("side", "auto"))
            label_overflow = str(labels.get("overflow", "suppress" if lane_mode else "visible-overflow"))
            label_text_role = str(labels["textRole"]) if "textRole" in labels else None
    if isinstance(visible.fallback, Mapping):
        label_fallback = tuple(str(item) for item in visible.fallback.get("labels", ()))
        annotation_fallback = tuple(str(item) for item in visible.fallback.get("annotations", ()))
    temporal = view.time_presentation or {}
    axis_tiers = normalize_axis_tiers(view, locale=locale)
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
    project_notes = project.get("annotations", {})
    consumed_note_ids: set[str] = set()

    def _annotation_text(annotation: Mapping[str, Any]) -> str:
        reference = annotation.get("projectAnnotation")
        if reference is None:
            return str(annotation["text"])
        # A Project reference selects text once (#466): the Project note is
        # the sole narrative authority, and a missing or empty selection is a
        # stable ingress error, never a skipped note or guessed target.
        source = project_notes.get(reference) if isinstance(project_notes, Mapping) else None
        text = source.get("text") if isinstance(source, Mapping) else None
        if not isinstance(text, str) or not text:
            raise ValueError(f"E_PRESENTATION_ANNOTATION_REFERENCE_MISSING:{reference}: /annotations/{_diagnostic_value(reference)}/text is missing or empty; expected nonempty text")
        consumed_note_ids.add(str(reference))
        return text

    item_titles = {item.object_id: item.title for item in projection.items}

    def _annotation(index: int, annotation: Mapping[str, Any]) -> AnnotationIntent:
        anchor = {str(key): ("finish" if key == "endpoint" and value == "end" else str(value)) for key, value in annotation["anchor"].items()}  # `end` aliases `finish` (I662 S4a)
        purpose = str(annotation["purpose"])
        number = index + 1 if annotation_numbered else None
        content = _annotation_text(annotation)
        # The kind is the referenced Project annotation's own `kind` (#584); an annotation that
        # carries its own text has none.
        reference = annotation.get("projectAnnotation")
        source_note = project_notes.get(reference) if reference is not None and isinstance(project_notes, Mapping) else None
        declared_kind = source_note.get("kind") if isinstance(source_note, Mapping) else None
        kind = declared_kind if isinstance(declared_kind, str) and declared_kind else None
        subject = item_titles.get(anchor.get("id", ""), "")
        subject_id = anchor.get("id", "") if anchor.get("id", "") in item_titles else ""
        declared_candidates = annotation.get("candidates")
        if declared_candidates is not None:
            # The declared candidate-list spelling (#466): no legacy fallback
            # ladder applies, and Layout falls back to visible-overflow on
            # the first declared candidate if every one is exhausted.
            return AnnotationIntent(str(annotation["id"]), purpose, anchor, "rail", "center",
                                    content, number, (), parse_candidates(declared_candidates),
                                    kind=kind, subject=subject, subject_id=subject_id,
                                    anchor_source_ref=f"/body/annotations/{index}/anchor")
        placement = annotation["placement"]
        return AnnotationIntent(str(annotation["id"]), purpose, anchor,
                                str(placement["side"]), str(placement["alignment"]),
                                content, number, annotation_fallback or ("rail",),
                                legacy_candidate_order(purpose, annotation_fallback)[0],
                                kind=kind, subject=subject, subject_id=subject_id,
                                anchor_source_ref=f"/body/annotations/{index}/anchor")

    annotations = tuple(_annotation(index, annotation) for index, annotation in enumerate(raw_annotations))
    # A selected Project annotation is consumed once: it is presented through
    # its View annotation and no longer duplicated into the notes slot (#466).
    notes = tuple((str(key), str(value.get("text", ""))) for key, value in project_notes.items()
                 if key not in consumed_note_ids)
    calendar_closed, calendar_exceptions = calendar_closures(project, projection, view)
    legend = legend_entries(detail, project, projection, color_scale, closed_days_drawn=bool(calendar_closed))
    detail_content = normalize_v05_review_detail_profile(detail, projection.items)
    scale_paints: tuple[tuple[str, str], ...] = ()
    scale_legend_paints: tuple[tuple[str, str], ...] = ()
    if color_scale is not None:
        scale_paints = tuple((item.object_id, color_scale.color_for(item.object_id, item.fields))
                             for item in projection.items if item.source_kind in {"primary", "combined"}
                             and color_scale.covers(item.fields))
        used = _used_scale_values(color_scale, projection)
        scale_legend_paints = tuple((f"scale:{color_scale.scale_id}:{value}", dict(color_scale.colors)[value])
                                    for value in color_scale.domain if value in used)
    return SurfaceContentInput(table_columns=columns, table_cells=cells, relations=relations, annotations=annotations,
                               show_member_labels=label_placement in {"plot", "legacy"}, label_placement=label_placement, label_content=label_content,
                               label_side=label_side,
                               label_overflow=label_overflow, relation_overflow=relation_overflow,
                               group_presentation=group_presentation,
                               axis_tiers=axis_tiers, axis_fiscal_start_month=fiscal_start_month,
                               as_of=as_of, as_of_label=_as_of_label(as_of_marker, as_of, locale),
                               annotation_numbered=annotation_numbered,
                               calendar_closed=calendar_closed, calendar_exceptions=calendar_exceptions,
                                   notes=notes, legend_entries=legend, coverage_text="",
                                   summary=summary,
                                   template_values=(),
                                   group_details=detail_content.group_details,
                                   milestones=detail_content.milestones,
                                   observation_columns=detail_content.observation_columns,
                                   observation_rows=detail_content.observation_rows,
                               label_fallback=label_fallback, label_text_role=label_text_role, annotation_fallback=annotation_fallback,
                               link_mode=link_mode, title_link_columns=title_link_columns,
                               attached_labels=_attached_labels(projection, locale),
                               table_cell_objects=table_cell_objects,
                               scale_target_role=color_scale.target_role if color_scale else None,
                               scale_paints=scale_paints, scale_legend_paints=scale_legend_paints,
                               progress_fill_source=view.progress_fill,
                               table_hierarchy_column=view.hierarchy_column,
                               table_indent_under_headers=table.indent_under_headers,
                               row_decoration=view.background_decoration[0],
                               group_decoration=view.background_decoration[1],
                               group_headers=_group_headers(projection, project, view),
                               group_header_runs=_group_header_runs(projection, project, view),
                               as_of_placement=str(as_of_marker.get("placement", "top")) if as_of_marker is not None else "top",
                               group_tints=group_tints,
                               slot_heading_text=tuple(sorted((view.slot_heading_text or {}).items())),
                               # `<id>` paints the bar, accent and stamp; `<id>#header` and `<id>#leader` carry the
                               # same colour to the elements a kind's `colorAlso` names (#991).
                               annotation_kind_paints=tuple(
                                   pair for item in annotations if annotation_kind_colors and item.kind in annotation_kind_colors
                                   for pair in ((item.annotation_id, annotation_kind_colors[item.kind]),
                                                *((f"{item.annotation_id}#{target}", annotation_kind_colors[item.kind])
                                                  for target in (annotation_kind_also or {}).get(item.kind, ())))))


def _group_header_facts(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput) -> dict[str, Any] | None:
    """The group ids, titles and secondaries a header template composes from, or None without a template."""
    declared = view.grouping.header if view.grouping is not None else None
    if declared is None:
        return None
    group_ids = tuple(dict.fromkeys(row.group_id for row in projection.rows if row.group_id))
    entities = project.get("entities", {})
    titles = {row.group_id: next((item.group_label for item in row.items if item.group_label), row.group_id)
              for row in projection.rows if row.group_id}
    secondaries: dict[str, str] | None = None
    if declared.secondary_field is not None:
        secondaries = {}
        for group_id in group_ids:
            entity = entities.get(group_id, {}) if isinstance(entities, Mapping) else {}
            fields = entity.get("fields", {}) if isinstance(entity, Mapping) else {}
            value = fields.get(declared.secondary_field) if isinstance(fields, Mapping) else None
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"E_REVIEW_GROUP_HEADER_SECONDARY:{group_id}:{declared.secondary_field}: /entities/{_diagnostic_value(group_id)}/fields/{_diagnostic_value(declared.secondary_field)}={_diagnostic_value(value)}; expected nonblank string")
            secondaries[group_id] = value
    return dict(group_ids=group_ids, titles=titles, secondaries=secondaries, text=declared.text,
                first=declared.first, ordinal=declared.ordinal, figures=dict(projection.figures),
                group_figures={group_id: dict(values) for group_id, values in projection.group_figures})


def _group_headers(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput) -> tuple[tuple[str, str], ...]:
    """Compose the View's group-header template per group in display order (#583)."""
    facts = _group_header_facts(projection, project, view)
    if facts is None:
        return ()
    try:
        return compose_group_headers(**facts)
    except GroupHeaderTextError as error:
        raise ValueError(f"{error.code}: {error.detail}; groups={_diagnostic_value(facts['group_ids'])}, ordinal={_diagnostic_value(facts['ordinal'])}, first={_diagnostic_value(facts['first'])}") from error


def _group_header_runs(projection: ReviewProjection, project: Mapping[str, Any], view: ViewInput
                       ) -> tuple[tuple[str, tuple[tuple[str, str | None], ...]], ...]:
    """The role-marked runs of the groups whose template marks a placeholder (#1192); none for an unmarked template."""
    facts = _group_header_facts(projection, project, view)
    if facts is None:
        return ()
    try:
        return tuple((group_id, tuple((run.text, run.role) for run in runs))
                     for group_id, runs in compose_group_header_runs(**facts))
    except GroupHeaderTextError as error:
        raise ValueError(f"{error.code}: {error.detail}; groups={_diagnostic_value(facts['group_ids'])}, ordinal={_diagnostic_value(facts['ordinal'])}, first={_diagnostic_value(facts['first'])}") from error


def _attached_labels(projection: ReviewProjection, locale: str) -> tuple[tuple[str, str], ...]:
    """Title, planned date and point delta of each attached point, in its View locale (#486)."""
    labels = []
    active_rows = projection.lane_rows if projection.lane_membership is not None else projection.rows
    for row in active_rows:
        for item in row.items:
            at = item.planned.get("at")
            if item.attached_to is None or not isinstance(at, date):
                continue
            parts = [item.title, _format_compact_date(at, include_year=False, locale=locale)]
            if item.at_delta is not None:
                parts.append(f"{item.at_delta:+d}d")
            labels.append((item.object_id, " · ".join(parts)))
    return tuple(labels)


def _as_of_label(marker: Mapping[str, Any] | None, as_of: date | None, locale: str) -> str:
    """Return the as-of label exactly as declared, plus a date only in a declared form (#428).

    A View without an as-of marker keeps the implicit "As of <localized date>"
    label; a declared marker is its own text unless it names a date form.
    """
    date_form = {"form": "localized-date"} if marker is None else marker.get("date")
    label = "As of" if marker is None else str(marker.get("label", ""))
    if not isinstance(date_form, Mapping) or as_of is None:
        return label
    table = axis_name_table(str(date_form.get("nameTable", locale)))
    formatted = table.format(str(date_form["form"]), {
        "year": as_of.year, "monthShort": table.month_short[as_of.month - 1],
        "monthLong": table.month_long[as_of.month - 1], "monthNumber": as_of.month,
        "monthNumeric": f"{as_of.month:02d}", "day": as_of.day, "dayNumeric": f"{as_of.day:02d}",
    })
    return f"{label} {formatted}" if label else formatted


def _heading_calendar_name(project: Mapping[str, Any]) -> str:
    """The `{calendar}` fact: the default calendar's declared `title` when it has one, else its identifier (#1026)."""
    project_body = project.get("project", {})
    calendar_id = project_body.get("calendar") if isinstance(project_body, Mapping) else None
    if not calendar_id:
        return ""
    calendars = project.get("calendars", {})
    calendar = calendars.get(calendar_id) if isinstance(calendars, Mapping) else None
    title = calendar.get("title") if isinstance(calendar, Mapping) else None
    return title if isinstance(title, str) and title else str(calendar_id)


def compose_heading(view: ViewInput, project: Mapping[str, Any], actual_set: Mapping[str, Any] | None,
                    locale: str) -> HeadingContent:
    """Compose the optional kicker, title and subtitle a table-timeline surface draws (#991, #1189).

    Without a declared `heading` the title is the Project title and there is no kicker or subtitle, as before.
    A declared template reads the Project title, the Actual Set's as-of date in the declared form and
    the Project's default calendar name (its declared `title`, else its id); a fact the Project lacks renders
    as empty text.
    """
    project_body = project.get("project", {})
    project_title = str(project_body.get("title", "Chrona")) if isinstance(project_body, Mapping) else "Chrona"
    heading = view.heading
    if heading is None:
        return HeadingContent(project_title)
    as_of_value = _resource_body(actual_set, "ACTUAL_SET").get("asOf")
    as_of_text = ""
    if isinstance(as_of_value, str):
        as_of = date.fromisoformat(as_of_value)
        table = axis_name_table(locale)
        as_of_text = table.format(heading.date_form, {
            "year": as_of.year, "monthShort": table.month_short[as_of.month - 1],
            "monthLong": table.month_long[as_of.month - 1], "monthNumber": as_of.month,
            "monthNumeric": f"{as_of.month:02d}", "day": as_of.day, "dayNumeric": f"{as_of.day:02d}",
        })
    facts = {"project": project_title, "asOf": as_of_text, "calendar": _heading_calendar_name(project)}
    title = render_heading(heading.title, facts) if heading.title is not None else project_title
    return HeadingContent(
        title=title,
        subtitle=render_heading(heading.subtitle, facts) if heading.subtitle is not None else None,
        kicker=render_heading(heading.kicker, facts) if heading.kicker is not None else None,
        text_wrap=heading.text_wrap,
    )


def normalize_axis_tiers(view: Any, *, locale: str) -> tuple[AxisTier, ...]:
    """The View's declared axis tiers as Layout-owned intent; measurement and placement read the same tiers."""
    axis = view.axis or {}
    return tuple(_axis_tier(item, locale=locale, tier_index=index)
                 for index, item in enumerate(axis.get("tiers", ())))


def _axis_tier(value: Mapping[str, Any], *, locale: str, tier_index: int = 0) -> AxisTier:
    """Detach one schema-validated View tier into Layout-owned typed intent."""
    role, unit = str(value["role"]), str(value["unit"])
    typography_role = str(value["typographyRole"]) if "typographyRole" in value else None
    raw_fill_scale = value.get("fillScale")
    fill_scale = None
    if raw_fill_scale is not None:
        if role != "band" or unit == "auto" or not isinstance(raw_fill_scale, Mapping):
            raise AxisBandScaleError(
                "E_PRESENTATION_AXIS_SCALE_TARGET", "target must be a fixed-unit band tier",
                f"/view/body/axis/tiers/{tier_index}/fillScale",
            )
        fill_scale = AxisBandFillSpec(
            raw_fill_scale["scale"], raw_fill_scale["key"], raw_fill_scale.get("containingTier"),
        )
    raw_label = value.get("label")
    if role != "labels" or not isinstance(raw_label, Mapping):
        return AxisTier(unit, int(value["every"]), role, typography_role=typography_role, fill_scale=fill_scale)
    candidates = raw_label.get("forms", {})
    candidate_forms = tuple((str(candidate), str(form)) for candidate, form in candidates.items()) if isinstance(candidates, Mapping) else ()
    table_id = str(raw_label.get("nameTable", locale))
    axis_name_table(table_id)
    raw_secondary = raw_label.get("secondary")
    secondary = None
    if isinstance(raw_secondary, Mapping):
        secondary_table = str(raw_secondary.get("nameTable", table_id))
        axis_name_table(secondary_table)
        secondary = AxisSecondaryIntent(str(raw_secondary["form"]), secondary_table,
                                        str(raw_secondary["typographyRole"]), str(raw_secondary["placement"]))
    return AxisTier(unit, int(value["every"]), role,
                    AxisLabelIntent(str(raw_label["form"]) if "form" in raw_label else None,
                                    candidate_forms, str(raw_label["align"]), str(raw_label["overflow"]),
                                    str(raw_label["orientation"]), table_id, secondary),
                    typography_role=typography_role, fill_scale=fill_scale)


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
    width_fields = tuple(value.keys()) if isinstance(value, Mapping) else ()
    raise ValueError(f"E_VIEW_TABLE_WIDTH: width type={type(value).__name__}, fields={_diagnostic_value(width_fields)}; expected content, fill, fr, or minmax width descriptor")


def calendar_closures(project: Mapping[str, Any], projection: ReviewProjection,
                      view: ViewInput) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """The closed days and closed exception days the View selects to draw, from the Project default calendar."""
    return _calendar_closures(project, projection.window, view.shading or {}, view.time_presentation or {})


def _calendar_closures(project: Mapping[str, Any], window: tuple[date, date], shading: Mapping[str, Any],
                       temporal: Mapping[str, Any]) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """Derive View-eligible closure and exception facts from the Project calendar."""
    calendar_id = project.get("project", {}).get("calendar")
    calendars = project.get("calendars", {})
    calendar = calendars.get(calendar_id) if isinstance(calendar_id, str) and isinstance(calendars, Mapping) else None
    if not isinstance(calendar, Mapping):
        # No declared default calendar declares no closed day: the scheduler does not assume a week for a Project
        # without one (`E_CALENDAR_REQUIRED`), so the plot is not shaded as if every day were closed (#893).
        return (), ()
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


def _resource_body(value: Mapping[str, Any] | None, name: str) -> Mapping[str, Any]:
    """Accept one current resource envelope; malformed optional input is not empty."""
    if value is None:
        return {}
    body = value.get("body") if isinstance(value, Mapping) else None
    if not isinstance(body, Mapping):
        raise ValueError(f"E_PRESENTATION_{name}_SHAPE: /{name.lower()}/body has type={type(body).__name__}; expected mapping envelope body")
    return body


def _is_actual_source(source: Any) -> bool:
    return isinstance(source, Mapping) and source.get("facet") == "actual"


def _absence_state(item: Any) -> str:
    """The `missingBy` key of an item: how its observation stands (#991)."""
    state = getattr(item, "observation_state", None)
    if state == ObservationState.DUE_UNOBSERVED:
        return "dueUnobserved"
    if state == ObservationState.NOT_YET_DUE:
        return "notYetDue"
    if state == ObservationState.RECORDED:
        actual = getattr(item, "actual", None) or {}
        return "inProgress" if actual.get("start") is not None and actual.get("finish") is None and actual.get("at") is None else "other"
    return "unavailable"


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
    counts = projected_counts(projection.items, as_of_available=as_of_value is not None)
    values: dict[str, Any] = {
        "actual.asOf": date.fromisoformat(as_of_value) if isinstance(as_of_value, str) else None,
        "planned.nextPoint": points[0] if points else None,
        "count.selected": counts.selected,
        "count.missingActual": counts.missing_actual,
        "count.knownFinishVariance": counts.known_finish_variance,
    }
    panels: list[SummaryPanel] = []
    grouped_ids = bool(summary and any(panel.arrangement == "inline" for panel in summary.panels))
    for panel_index, panel in enumerate(summary.panels if summary is not None else ()):
        inline = panel.arrangement == "inline"
        caption_role = "summary-caption" if inline else "summary"
        caption_semantic = "summaryCaption" if inline else ""
        title_id = (f"summary:/panels/{panel_index}/title" if grouped_ids else f"summary:{panel.id}")
        title_semantic = caption_semantic or ("summaryHeader" if grouped_ids else "")
        runs = [SummaryTextRun(title_id, panel.id, panel.title or panel.id, caption_role, title_semantic)]
        for metric_index, definition in enumerate(panel.metrics):
            metric_path = f"summary:/panels/{panel_index}/metrics/{metric_index}"
            if not isinstance(definition, tuple):
                metric_id, source, formatter = definition.id, definition.source, definition.format
                if isinstance(source, Mapping):
                    if source.get("actual") == "asOf":
                        source = "actual.asOf"
                    elif source.get("counts") == "finishDelta":
                        values["counts.finishDelta"] = f"{counts.behind} / {counts.ahead}"
                        source = "counts.finishDelta"
                    elif source.get("scenario") in {"id", "title"}:
                        values[f"scenario.{source['scenario']}"] = _scenario_summary_value(
                            projection, project or {}, source["scenario"])
                        source = f"scenario.{source['scenario']}"
                    elif isinstance(source.get("figure"), str):
                        values[f"figure.{source['figure']}"] = dict(projection.figures).get(source["figure"])
                        source = f"figure.{source['figure']}"
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
                    raise ValueError(f"E_PRESENTATION_SUMMARY_SOURCE: {metric_path}/source={_diagnostic_value(source)} is not a resolved summary value; expected a supported source")
                if formatter not in {"text", "date", "count", "signedDays"}:
                    raise ValueError(f"E_PRESENTATION_SUMMARY_FORMAT: {metric_path}/format={_diagnostic_value(formatter)}; expected text, date, count, or signedDays")
                raw = values[source]
                rendered = "unknown" if raw is None else (
                    raw.isoformat() if formatter == "date" and isinstance(raw, date)
                    else f"{raw:+d}d" if formatter == "signedDays" and isinstance(raw, int)
                    else str(raw)
                )
                label = definition.label
                if panel.presentation == "figures":
                    if inline:
                        runs.extend((
                            SummaryTextRun(f"{metric_path}/value" if grouped_ids else
                                           f"summary:{panel.id}:{metric_id}:value", panel.id, rendered,
                                            "metric", "summaryFigureValue"),
                            SummaryTextRun(f"{metric_path}/label" if grouped_ids else
                                           f"summary:{panel.id}:{metric_id}:caption", panel.id, label,
                                            "summary-unit", "summaryUnit"),
                        ))
                    else:
                        runs.extend((
                            SummaryTextRun(f"{metric_path}/value" if grouped_ids else
                                           f"summary:{panel.id}:{metric_id}:value", panel.id, rendered, "metric",
                                           "summaryFigureValue" if grouped_ids else ""),
                            SummaryTextRun(f"{metric_path}/label" if grouped_ids else
                                           f"summary:{panel.id}:{metric_id}:caption", panel.id, label, "summary",
                                           "summaryFigureCaption" if grouped_ids else ""),
                        ))
                else:
                    runs.append(SummaryTextRun(f"{metric_path}/text" if grouped_ids else
                                               f"summary:{panel.id}:{metric_id}", panel.id,
                                               f"{label}: {rendered}", caption_role,
                                               caption_semantic or ("summaryMetric" if grouped_ids else "")))
            else:
                metric_id, literal = definition
                runs.append(SummaryTextRun(f"{metric_path}/text" if grouped_ids else
                                           f"summary:{panel.id}:{metric_id}", panel.id,
                                           f"{metric_id}: {literal}", caption_role,
                                           caption_semantic or ("summaryMetric" if grouped_ids else "")))
        panels.append(SummaryPanel(panel.id, tuple(runs), panel.arrangement))
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
        raise ValueError(f"E_PRESENTATION_SUMMARY_SOURCE: subtree objectId={_diagnostic_value(root_id)} requires hierarchy grouping; current={projection.hierarchy_grouping!r}")
    root = next((item for item in projection.items
                 if item.object_id == root_id and item.source_kind == "primary"), None)
    if root is None or not root.hierarchy_path:
        raise ValueError(f"E_PRESENTATION_SUMMARY_SOURCE: subtree objectId={_diagnostic_value(root_id)} is not a selected primary hierarchy root with a path")
    prefix = root.hierarchy_path
    members = tuple(item for item in projection.items
                    if item.source_kind == "primary" and item.hierarchy_path[:len(prefix)] == prefix)
    endpoints = tuple(item.planned.get("at", item.planned.get("end")) for item in members)
    known = tuple(value for value in endpoints if isinstance(value, date))
    if not known:
        raise ValueError(f"E_PRESENTATION_SUMMARY_SOURCE: subtree objectId={_diagnostic_value(root_id)} has no selected member with a date endpoint; members={len(members)}")
    return max(known)
