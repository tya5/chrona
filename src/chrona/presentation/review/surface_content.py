"""Review summary and detail content normalization."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.model.surface_content import SurfaceContentInput

def _surface_content_input(projection: ReviewProjection, project: dict[str, Any], view: dict[str, Any], settings: dict[str, Any], summary_profile: dict[str, Any] | None = None, as_of: date | None = None, detail_profile: dict[str, Any] | None = None):
    """Normalize selected table/surface facts once, before Scene construction."""
    columns = tuple((str(column["id"]), str(column["id"]))
                    for column in view["body"].get("tableColumns", ()))
    cells = tuple(
        (item.object_id, str(column["id"]), str(_display_value(_table_value(item, project, column["source"]), column["missing"])))
        for item in projection.items for column in view["body"].get("tableColumns", ())
    )
    relations = tuple(project.get("relations", ())) if view["body"].get("visibility", {}).get("relations", "semantic") != "none" else ()
    annotations = tuple(view["body"].get("annotations", ())) if view["body"].get("visibility", {}).get("annotations", "none") != "none" else ()
    notes = tuple((str(key), str(value.get("text", ""))) for key, value in project.get("annotations", {}).items())
    legend = tuple((str(entry["role"]), str(entry["label"])) for entry in settings["detail"]["legend"])
    values = {
        "selectedCount": len(projection.items), "unmatchedCount": len(projection.unmatched_actual_ids),
        "missingCount": sum(1 for item in projection.items if not item.actual),
    }
    coverage = settings["detail"]["coverage"].format_map(values)
    template_values = _template_values("", projection)
    summary_panels = _summary_panels(projection, summary_profile, as_of or projection.window[0], settings)
    from chrona.presentation.review.detail import resolve_review_detail_profile
    detail = resolve_review_detail_profile(detail_profile, projection.items, settings)
    return SurfaceContentInput(
        table_columns=columns, table_cells=cells, relations=relations,
        annotations=annotations, notes=notes, legend_entries=legend,
        coverage_text=coverage, summary_panels=summary_panels,
        template_values=template_values, group_details=detail.group_details,
        milestones=detail.milestones,
        observation_columns=detail.observation_columns,
        observation_rows=detail.observation_rows,
    )


def _summary_panels(projection: ReviewProjection, profile: dict[str, Any] | None,
                    as_of: date, settings: dict[str, Any]):
    if not profile:
        return ()
    total = len(projection.items)
    actual = sum(bool(item.actual) for item in projection.items)
    points = sorted(item.planned["at"] for item in projection.items
                    if item.source_type == "point" and item.planned["at"] >= as_of)
    values = {
        "selectedCount": str(total),
        "actualCoverage": f"{actual}/{total}" if total else "unknown",
        "knownFinishVarianceCount": str(sum(item.finish_delta is not None for item in projection.items)),
        "missingActualCount": str(total - actual),
        "nextPlannedPoint": points[0].isoformat() if points else "unknown",
    }
    labels = settings["detail"]["summaryLabels"]
    separator = settings["detail"]["formatting"]["rangeSeparator"]
    return tuple(
        (
            str(panel["id"]),
            str(panel.get("title", panel["id"])),
            tuple((str(metric), f"{labels[metric]}{separator}{values[metric]}")
                  for metric in panel["metrics"]),
        )
        for panel in profile["panels"]
    )


def _template_values(title: str, projection: ReviewProjection) -> tuple[tuple[str, str], ...]:
    start, end = projection.window
    last_visible = end - timedelta(days=1) if end.day == 1 and end > start else end
    return (
        ("title", title), ("windowStart", f"{start:%b %Y}"), ("windowLastVisible", f"{last_visible:%b %Y}"),
        ("selectedCount", str(len(projection.items))),
        ("unmatchedCount", str(len(projection.unmatched_actual_ids))),
        ("missingCount", str(sum(1 for item in projection.items if not item.actual))),
    )


def _table_value(item: ReviewItem, project: dict[str, Any], source: Any) -> Any:
    if isinstance(source, str):
        return {"id": item.object_id, "title": item.title, "objectType": item.source_type,
                "entity": item.group_label}.get(source)
    if "field" in source:
        return (item.fields or {}).get(source["field"])
    facet = source["comparisonFacet"]
    return {"finishDelta": item.finish_delta, "missingActual": not bool(item.actual),
            "progress": (item.actual or {}).get("progress")}.get(facet)


def _display_value(value: Any, missing: str) -> str:
    if value is None:
        return {"blank": "", "em-dash": "—", "unknown": "unknown"}[missing]
    return f"{value:+d}d" if isinstance(value, int) and not isinstance(value, bool) else str(value)
