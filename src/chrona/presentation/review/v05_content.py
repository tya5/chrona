"""Current-resource normalization for v0.5 optional Scene content."""
from __future__ import annotations

from typing import Any, Mapping

from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.model.surface_content import SurfaceContentInput, display_value, table_value


def normalize_v05_surface_content(projection: ReviewProjection, project: Mapping[str, Any], view: Mapping[str, Any],
                                  *, detail: Mapping[str, Any] | None = None, summary: Mapping[str, Any] | None = None) -> SurfaceContentInput:
    """Normalize current Project/View/profile facts without legacy Settings."""
    body = view.get("body", {})
    columns = tuple((str(column["id"]), str(column["id"])) for column in body.get("tableColumns", ()))
    cells = tuple((item.object_id, str(column["id"]), display_value(table_value(item, dict(project), column["source"]), column["missing"]))
                  for item in projection.items for column in body.get("tableColumns", ()))
    visible = body.get("visibility", {})
    relations = tuple(project.get("relations", ())) if visible.get("relations", "none") != "none" else ()
    annotations = tuple(body.get("annotations", ())) if visible.get("annotations", "none") != "none" else ()
    notes = tuple((str(key), str(value.get("text", ""))) for key, value in project.get("annotations", {}).items())
    detail_body = (detail or {}).get("body", detail or {})
    summary_body = (summary or {}).get("body", summary or {})
    legend = tuple((str(item["role"]), str(item["label"])) for item in detail_body.get("legend", ()))
    panels = tuple((str(item["id"]), str(item.get("title", item["id"])), tuple((str(key), str(value)) for key, value in item.get("metrics", {}).items()))
                   for item in summary_body.get("panels", ()))
    return SurfaceContentInput(table_columns=columns, table_cells=cells, relations=relations, annotations=annotations,
                               notes=notes, legend_entries=legend, summary_panels=panels)
