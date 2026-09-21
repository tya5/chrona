"""Review SVG orchestration through resolved Layout Manifest slots."""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from chrona.presentation.model.projection import ReviewProjection


def render_table_timeline_svg(
    title: str, projection: ReviewProjection, project: dict[str, Any], view: dict[str, Any],
    theme: dict[str, Any], capabilities: set[str], profile: dict[str, Any],
    slots: dict[str, Any] | None = None, *, viewport: tuple[float, float] | None = None,
    metric_values: dict[str, Any] | None = None, font_metrics: Any | None = None,
) -> str:
    """Serialize a review whose source rectangles were resolved before rendering."""
    required = {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}
    if not required.issubset(capabilities):
        raise ValueError("E_OUTPUT_CAPABILITY_MISSING")
    if slots is None or viewport is None or metric_values is None or font_metrics is None:
        raise ValueError("E_RENDER_CONTEXT_REQUIRED")
    from chrona.presentation.renderers.table_timeline import render_gantt
    from chrona.presentation.scene.review import compose_review_scene
    scene = compose_review_scene(
        title, projection, project, view, slots, viewport=viewport,
        metric_values=metric_values, font_metrics=font_metrics,
    )
    return render_gantt(scene, theme, font_size=float(metric_values["text.body.size"]))


def append_review_summary(
    svg: str, projection: ReviewProjection, profile: dict[str, Any], as_of: date,
    rect: Any | None = None,
) -> str:
    """Append read-only summary facts to an already resolved summary rectangle."""
    total = len(projection.items)
    actual = sum(bool(item.actual) for item in projection.items)
    points = sorted(item.planned["at"] for item in projection.items
                    if item.source_type == "point" and item.planned["at"] >= as_of)
    values = {
        "selectedCount": str(total), "actualCoverage": f"{actual}/{total}" if total else "unknown",
        "knownFinishVarianceCount": str(sum(item.finish_delta is not None for item in projection.items)),
        "missingActualCount": str(total - actual),
        "nextPlannedPoint": points[0].isoformat() if points else "unknown",
    }
    labels = {"selectedCount": "Selected work", "actualCoverage": "Actual coverage",
              "knownFinishVarianceCount": "Known finish variance", "missingActualCount": "Missing Actual",
              "nextPlannedPoint": "Next planned point"}
    lines = []
    x, y = getattr(rect, "x", 32), getattr(rect, "y", 24) + 22
    for panel in profile["panels"]:
        lines.append(f'<text data-purpose="summary-panel" data-source-ref="derived:{escape(panel["id"])}" x="{x}" y="{y}">{escape(panel["id"])}</text>')
        y += 15
        for metric in panel["metrics"]:
            lines.append(f'<text data-purpose="summary-metric" data-source-ref="derived:{escape(panel["id"])}:{metric}" x="{x}" y="{y}">{escape(labels[metric])}: {escape(values[metric])}</text>')
            y += 13
    return svg.replace("</svg>", "\n".join(lines) + "\n</svg>")
