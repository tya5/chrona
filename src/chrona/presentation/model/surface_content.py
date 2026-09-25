"""Normalized presentation content inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.presentation.model.projection import ReviewItem
from chrona.presentation.table_presentation import BooleanPresencePresentation


@dataclass(frozen=True)
class SummaryTextRun:
    """One normalized, ordered summary line before Layout gives it geometry."""

    placement_id: str
    source_ref: str
    content: str
    typography_role: str


@dataclass(frozen=True)
class SummaryPanel:
    """One selected summary panel and its canonical text-run sequence."""

    panel_id: str
    runs: tuple[SummaryTextRun, ...]


@dataclass(frozen=True)
class SummaryContent:
    """Immutable semantic summary facts shared by measurement and placement."""

    panels: tuple[SummaryPanel, ...]

    @property
    def runs(self) -> tuple[SummaryTextRun, ...]:
        return tuple(run for panel in self.panels for run in panel.runs)


@dataclass(frozen=True)
class RelationPresentationFact:
    """One selected dependency fact closed before Layout resolves geometry."""

    relation_id: str
    source_object_id: str
    source_endpoint: str
    target_object_id: str
    target_endpoint: str
    lag: object
    lag_calendar: str | None
    semantic_id: str
    label_content: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableColumnWidth:
    """Closed measured-allocation intent, normalized before Layout ingress."""

    minimum: str
    maximum: str
    fraction: float = 0.0

    @property
    def flexible(self) -> bool:
        return self.maximum in {"fill", "fr"}


@dataclass(frozen=True)
class TableColumnContent:
    """One semantic table column, retaining View intent without schema maps."""

    column_id: str
    header: str
    align: str
    width: TableColumnWidth
    header_orientation: str = "horizontal"


@dataclass(frozen=True)
class TableCellContent:
    """One rendered table fact with its selected, finite Scene semantic."""

    object_id: str
    column_id: str
    content: str
    semantic_id: str
    typography_role: str = "text"


@dataclass(frozen=True)
class AnnotationIntent:
    """One schema-validated annotation fact detached before Layout ingress."""

    annotation_id: str
    purpose: str
    anchor: dict[str, str]
    side: str
    alignment: str
    content: str
    number: int | None = None
    fallback_ladder: tuple[str, ...] = ()


@dataclass(frozen=True)
class AxisLabelIntent:
    """Finite label vocabulary and placement policy for one labels tier."""

    form: str | None
    candidate_forms: tuple[tuple[str, str], ...]
    align: str
    overflow: str
    orientation: str = "horizontal"


@dataclass(frozen=True)
class AxisTier:
    """One View-declared axis responsibility before Layout creates geometry."""

    unit: str
    every: int
    role: str
    label: AxisLabelIntent | None = None


@dataclass(frozen=True)
class SurfaceContentInput:
    """Selected presentation facts normalized once before Scene construction."""

    table_columns: tuple[TableColumnContent, ...]
    table_cells: tuple[TableCellContent, ...]
    relations: tuple[RelationPresentationFact, ...]
    annotations: tuple[AnnotationIntent, ...]
    show_member_labels: bool
    label_placement: str
    label_content: tuple[str, ...]
    label_side: str
    label_overflow: str
    relation_overflow: str
    group_presentation: str
    axis_tiers: tuple[AxisTier, ...]
    axis_fiscal_start_month: int
    as_of: date | None
    as_of_label: str
    annotation_numbered: bool
    calendar_closed: tuple[date, ...]
    calendar_exceptions: tuple[date, ...]
    notes: tuple[tuple[str, str], ...]
    legend_entries: tuple[tuple[str, str], ...]
    coverage_text: str
    summary: SummaryContent
    template_values: tuple[tuple[str, str], ...]
    group_details: tuple[tuple[str, str, str], ...]
    milestones: tuple[tuple[str, str, date], ...]
    observation_columns: tuple[tuple[str, str], ...]
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...]
    label_fallback: tuple[str, ...] = ()
    annotation_fallback: tuple[str, ...] = ()
    link_mode: str = "none"
    title_link_columns: tuple[str, ...] = ()
    # (table row id, column id, object id, is selected-current item).  This is
    # identity only: Scene uses it to attach presentation metadata and never to
    # infer geometry or re-resolve a View row.
    table_cell_objects: tuple[tuple[str, str, str, bool], ...] = ()
    # Completed data-dependent paint selected before Scene construction.  The
    # value is keyed by semantic source object, never by geometry or renderer.
    scale_target_role: str | None = None
    scale_paints: tuple[tuple[str, str], ...] = ()
    scale_legend_paints: tuple[tuple[str, str], ...] = ()
    progress_fill_source: str | None = None
    table_hierarchy_column: str | None = None
    row_decoration: str = "none"
    group_decoration: str = "all"


@dataclass(frozen=True)
class ResolvedPresentationInput:
    """One derived input boundary between authoring resources and Scene geometry."""

    title: str
    window: tuple[date, date]
    items: tuple[object, ...]
    settings: dict
    surface_content: SurfaceContentInput


def table_value(item: ReviewItem, project: dict[str, Any], source: Any, row_index: int | None = None) -> Any:
    """Resolve one renderer-neutral table cell from normalized review data."""
    if isinstance(source, str):
        if source == "path":
            return " / ".join(str(project.get("objects", {}).get(object_id, {}).get("title", object_id))
                              for object_id in item.hierarchy_path)
        return {"id": item.object_id, "title": item.title, "objectType": item.source_type,
                "entity": item.group_label, "rowIndex": row_index, "totalFloat": item.total_float,
                "wbsCode": item.wbs_code}.get(source)
    if "field" in source:
        return (item.fields or {}).get(source["field"])
    if "facet" in source:
        return {"planned": item.planned, "actual": item.actual,
                "finishDelta": item.finish_delta}.get(source["facet"])
    if "scenario" in source:
        if item.source_kind != "scenario" or item.scenario_id is None:
            return None
        if source["scenario"] == "id":
            return item.scenario_id
        declared = project.get("scenarios", {}).get(item.scenario_id, {})
        return declared.get("title") if isinstance(declared, dict) else None
    facet = source["comparisonFacet"]
    return {"finishDelta": item.finish_delta, "missingActual": not bool(item.actual),
            "progress": (item.actual or {}).get("progress")}.get(facet)


def display_value(value: Any, missing: str, formatter: str | BooleanPresencePresentation = "text", *, locale: str = "en-US") -> str:
    """Format a normalized table value according to its declared View contract."""
    if value is None:
        return {"blank": "", "em-dash": "—", "unknown": "unknown",
                "in-progress": "in progress"}[missing]
    if isinstance(value, bool):
        if isinstance(formatter, BooleanPresencePresentation):
            return formatter.when_true if value else formatter.when_false
        raise ValueError("E_VIEW_BOOLEAN_PRESENTATION")
    if isinstance(formatter, BooleanPresencePresentation):
        raise ValueError("E_VIEW_BOOLEAN_PRESENTATION")
    if formatter == "date":
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            point = value.get("at", value.get("finish", value.get("end", value.get("start"))))
            return point.isoformat() if isinstance(point, date) else str(point)
    if formatter == "dateRange" and isinstance(value, dict):
        start, end = value.get("start"), value.get("end", value.get("finish"))
        if isinstance(start, date) and isinstance(end, date):
            return _format_date_range(start, end, locale=locale)
        if isinstance(start, date) and end is None:
            return f"{_format_compact_date(start, include_year=True, locale=locale)} –"
        if isinstance(value.get("at"), date):
            return _format_compact_date(value["at"], include_year=True, locale=locale)
    if formatter == "signedDays" and isinstance(value, int) and not isinstance(value, bool):
        return f"{value:+d}d"
    return str(value)


def _format_date_range(start: date, end: date, *, locale: str) -> str:
    if start == end:
        return _format_compact_date(start, include_year=True, locale=locale)
    if start.year == end.year:
        return f"{_format_compact_date(start, include_year=False, locale=locale)} – {_format_compact_date(end, include_year=False, locale=locale)}"
    return f"{_format_compact_date(start, include_year=True, locale=locale)} – {_format_compact_date(end, include_year=True, locale=locale)}"


def _format_compact_date(value: date, *, include_year: bool, locale: str) -> str:
    if locale == "ja-JP":
        rendered = f"{value.month}月{value.day}日"
        return f"{value.year}年{rendered}" if include_year else rendered
    if locale != "en-US":
        raise ValueError("E_PRESENTATION_LOCALE_UNSUPPORTED")
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    rendered = f"{value.day:02d} {months[value.month - 1]}"
    return f"{rendered} {value.year}" if include_year else rendered
