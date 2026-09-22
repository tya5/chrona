"""Normalized presentation content inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.presentation.model.projection import ReviewItem


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
class SurfaceContentInput:
    """Selected presentation facts normalized once before Scene construction."""

    table_columns: tuple[tuple[str, str], ...]
    table_cells: tuple[tuple[str, str, str], ...]
    relations: tuple[dict, ...]
    annotations: tuple[dict, ...]
    show_member_labels: bool
    label_placement: str
    label_content: tuple[str, ...]
    label_side: str
    label_overflow: str
    relation_overflow: str
    group_presentation: str
    axis_level: str
    axis_levels: tuple[tuple[str, str], ...]
    axis_ticks: str | None
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
        return {"id": item.object_id, "title": item.title, "objectType": item.source_type,
                "entity": item.group_label, "rowIndex": row_index}.get(source)
    if "field" in source:
        return (item.fields or {}).get(source["field"])
    if "facet" in source:
        return {"planned": item.planned, "actual": item.actual,
                "finishDelta": item.finish_delta}.get(source["facet"])
    facet = source["comparisonFacet"]
    return {"finishDelta": item.finish_delta, "missingActual": not bool(item.actual),
            "progress": (item.actual or {}).get("progress")}.get(facet)


def display_value(value: Any, missing: str, formatter: str = "text", *, locale: str = "en-US") -> str:
    """Format a normalized table value according to its declared View contract."""
    if value is None:
        return {"blank": "", "em-dash": "—", "unknown": "unknown",
                "in-progress": "in progress"}[missing]
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
    if locale != "en-US":
        raise ValueError("E_PRESENTATION_LOCALE_UNSUPPORTED")
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    rendered = f"{value.day:02d} {months[value.month - 1]}"
    return f"{rendered} {value.year}" if include_year else rendered
