"""Normalized presentation content inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.presentation.model.projection import ReviewItem

@dataclass(frozen=True)
class SurfaceContentInput:
    """Selected presentation facts normalized once before Scene construction."""

    table_columns: tuple[tuple[str, str], ...] = ()
    table_cells: tuple[tuple[str, str, str], ...] = ()
    relations: tuple[dict, ...] = ()
    annotations: tuple[dict, ...] = ()
    show_member_labels: bool = False
    as_of: date | None = None
    calendar_closed: tuple[date, ...] = ()
    notes: tuple[tuple[str, str], ...] = ()
    legend_entries: tuple[tuple[str, str], ...] = ()
    coverage_text: str = ""
    summary_panels: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = ()
    template_values: tuple[tuple[str, str], ...] = ()
    group_details: tuple[tuple[str, str, str], ...] = ()
    milestones: tuple[tuple[str, str, date], ...] = ()
    observation_columns: tuple[tuple[str, str], ...] = ()
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = ()


@dataclass(frozen=True)
class ResolvedPresentationInput:
    """One derived input boundary between authoring resources and Scene geometry."""

    title: str
    window: tuple[date, date]
    items: tuple[object, ...]
    settings: dict
    surface_content: SurfaceContentInput


def table_value(item: ReviewItem, project: dict[str, Any], source: Any) -> Any:
    """Resolve one renderer-neutral table cell from normalized review data."""
    if isinstance(source, str):
        return {"id": item.object_id, "title": item.title, "objectType": item.source_type,
                "entity": item.group_label}.get(source)
    if "field" in source:
        return (item.fields or {}).get(source["field"])
    if "facet" in source:
        return {"planned": item.planned, "actual": item.actual,
                "finishDelta": item.finish_delta}.get(source["facet"])
    facet = source["comparisonFacet"]
    return {"finishDelta": item.finish_delta, "missingActual": not bool(item.actual),
            "progress": (item.actual or {}).get("progress")}.get(facet)


def display_value(value: Any, missing: str, formatter: str = "text") -> str:
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
            return f"{start.isoformat()} – {end.isoformat()}"
        if isinstance(value.get("at"), date):
            return value["at"].isoformat()
    if formatter == "signedDays" and isinstance(value, int) and not isinstance(value, bool):
        return f"{value:+d}d"
    return f"{value:+d}d" if isinstance(value, int) and not isinstance(value, bool) else str(value)
