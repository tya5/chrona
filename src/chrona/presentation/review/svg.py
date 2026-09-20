"""Review and table-timeline SVG orchestration."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from html import escape
from typing import Any

from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.review.surface_content import _surface_content_input, _template_values
from chrona.presentation.scene.paint import legacy_theme_colors

def render_review_svg(title: str, projection: ReviewProjection, theme: dict[str, Any], capabilities: set[str], profile:dict[str,Any]|None=None, settings: dict[str, Any] | None = None, surface_content: Any | None = None) -> str:
    """Render the completed review projection with source metadata and text alternatives."""
    required = {"sourceMetadata", "accessibleText", "semanticRoles", "marker"}
    if not required.issubset(capabilities):
        raise ValueError("E_OUTPUT_CAPABILITY_MISSING")
    presentation_scene = None
    if settings is not None:
        from chrona.presentation.model.surface_content import SurfaceContentInput
        from chrona.presentation.scene.builder import build_presentation_scene
        content = replace(surface_content or SurfaceContentInput(),
                          template_values=_template_values(title, projection))
        presentation_scene = build_presentation_scene(title, projection.items, projection.window, settings, content)
        from chrona.presentation.renderers.scene_svg import render_scene_surface_svg
        surface = next((candidate for candidate in presentation_scene.surfaces
                        if candidate.surface_id == "review"), None)
        if surface is None:
            raise ValueError("E_PRESENTATION_SURFACE_MISSING")
        return render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    start, end = presentation_scene.window if presentation_scene is not None else projection.window
    scene_marks = {}
    if presentation_scene is not None:
        for mark in presentation_scene.marks:
            scene_marks.setdefault(mark.source_id, {})[mark.facet] = mark
    if settings:
        viewport, layout, palette = settings["context"]["viewport"], settings["layout"], settings["theme"]
        left, top, day, row = layout["margins"]["left"], layout["margins"]["top"], layout["scale"]["dayWidth"], layout["row"]["height"]
        colors = {"background": palette["paints"]["background"]["color"], "planned": palette["paints"]["planned"]["color"], "actual": palette["paints"]["actual"]["color"], "behind": palette["paints"]["varianceBehind"]["color"], "text": palette["paints"]["text"]["color"], "muted": palette["paints"]["textMuted"]["color"], "grid": palette["strokes"]["axisMinor"]["color"], "separator": palette["strokes"]["groupSeparator"]["color"], "missing": palette["missingPattern"]["stroke"]["color"]}
        font, heading, body = palette["fontFamily"], palette["typography"]["heading"], palette["typography"]["body"]
        group_profile = {"mode": layout["group"]["mode"], "gapRows": 0}
        missing = palette["missingPattern"]
        labels = settings["detail"]
    else:
        left, top, day, row = 220, 96, 12, 56
        colors = legacy_theme_colors(theme); font, heading, body = "system-ui", {"size":20,"weight":700}, {"size":13,"weight":400}
        group_profile = (profile or {}).get("groupPresentation", {"mode":"none","gapRows":0})
        missing = {"width": 6, "height": 6, "angle": 45, "stroke": {"color": "#6b7280", "width": 2}}
        labels = {"title": "{title} — Plan / Actual Review", "missingActualLabel": "actual missing", "unmatchedActual": "Unmatched Actual: {unmatchedIds}", "formatting": {"signedDaysSuffix": "d", "positiveSign": "+"}}
    extra=sum(1+group_profile["gapRows"] for a,b in zip(projection.items,projection.items[1:]) if a.group_id!=b.group_id); width, height = (viewport["width"], viewport["height"]) if settings else (max(960, left + (end - start).days * day + 80), top + (len(projection.items)+extra) * row + 100)
    title_text = labels["title"].replace("{title}", title)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-labelledby="title desc">',f'<title id="title">{escape(title_text)}</title>',f'<desc id="desc">Planned and Actual engineering timeline review; {len(projection.unmatched_actual_ids)} unmatched Actual observations.</desc>', f'<defs><pattern id="missing" width="{missing["width"]}" height="{missing["height"]}" patternUnits="userSpaceOnUse" patternTransform="rotate({missing["angle"]})"><line x1="0" y1="0" x2="0" y2="{missing["height"]}" stroke="{colors.get("missing", missing["stroke"]["color"])}" stroke-width="{missing["stroke"]["width"]}"/></pattern></defs>',f'<rect width="{width}" height="{height}" fill="{colors["background"]}"/>',f'<text x="{left}" y="{top-heading["size"]}" font-family="{escape(font, quote=True)}" font-size="{heading["size"]}" font-weight="{heading["weight"]}" fill="{colors.get("text", "#111827")}">{escape(title_text)}</text>']
    if presentation_scene is not None:
        parts.append(f'<metadata data-presentation-scene="v0.1" data-axis-count="{len(presentation_scene.axes)}" data-mark-count="{len(presentation_scene.marks)}"/>')
    if settings is None:
        parts.append('<metadata data-presentation-adapter="legacy-v0.1" data-diagnostic="E_PRESENTATION_LEGACY_ADAPTER"/>')
    axis_ticks = presentation_scene.ticks if presentation_scene is not None else ()
    if axis_ticks:
        for tick in axis_ticks:
            x=left+(tick.start-start).days*day
            parts += [f'<line x1="{x}" y1="{top-body["size"]}" x2="{x}" y2="{height-layout["margins"]["bottom"]}" stroke="{colors.get("grid", "#ddd")}"/>',f'<text x="{x+layout["cellPadding"]["left"]}" y="{top-body["size"]-2}" font-family="{escape(font, quote=True)}" font-size="{body["size"]}">{escape(tick.label)}</text>']
    else:
        cursor = start
        while cursor <= end:
            x=left+(cursor-start).days*day
            if cursor.day <= 7: parts += [f'<line x1="{x}" y1="{top-body["size"]}" x2="{x}" y2="{height-30}" stroke="{colors.get("grid", "#ddd")}"/>',f'<text x="{x+3}" y="{top-body["size"]-2}" font-family="{escape(font, quote=True)}" font-size="{body["size"]}">{cursor:%Y-%m}</text>']
            cursor=date.fromordinal(cursor.toordinal()+7)
    y=top-row
    previous=None
    for item in projection.items:
        if item.group_id!=previous:
            if previous is not None: y+=row*(1+group_profile["gapRows"]); parts.append(f'<line data-purpose="group-separator" x1="{left}" y1="{y-row//2}" x2="{width-left}" y2="{y-row//2}" stroke="{colors.get("separator", "#9ca3af")}"/>')
            if group_profile["mode"] in {"header-and-separator","band", "header", "merged"}: parts.append(f'<text data-purpose="group-header" x="{left}" y="{y+row//2}" font-family="{escape(font, quote=True)}" font-size="{body["size"]}" font-weight="700">{escape(item.group_label)}</text>')
            y+=row; previous=item.group_id
        y+=row; parts.append(f'<text x="{left}" y="{y+5}" font-family="{escape(font, quote=True)}" font-size="{body["size"]}" fill="{colors.get("text", "#111827")}">{escape(item.title)}</text>')
        planned_mark = scene_marks.get(item.object_id, {}).get("baseline") or scene_marks.get(item.object_id, {}).get("planned")
        attrs=f'data-scene-id="item:{item.object_id}:planned" data-source-ref="{item.object_id}" data-purpose="planned"'
        if item.source_type=="point":
            radius = (settings["theme"]["point"]["size"] / 2) if settings else 8
            at = planned_mark.at if planned_mark else item.planned["at"]
            x=left+(at-start).days*day; parts.append(f'<path {attrs} d="M{x} {y-radius} L{x+radius} {y} L{x} {y+radius} L{x-radius} {y}Z" fill="{colors["planned"]}"/>')
        else:
            bar_height = settings["theme"]["bar"]["plannedHeight"] if settings else 12
            mark_start, mark_end = (planned_mark.start, planned_mark.end) if planned_mark else (item.planned["start"], item.planned["end"])
            x=left+(mark_start-start).days*day; w=max(settings["theme"]["bar"]["minWidth"] if settings else 4,(mark_end-mark_start).days*day); parts.append(f'<rect {attrs} x="{x}" y="{y-bar_height}" width="{w}" height="{bar_height}" rx="{settings["theme"]["bar"]["radius"] if settings else 2}" fill="{colors["planned"]}"/>')
        actual_mark = scene_marks.get(item.object_id, {}).get("actual")
        if actual_mark is None and presentation_scene is None and item.actual and "finish" in item.actual and item.source_type == "span":
            from types import SimpleNamespace
            actual_mark = SimpleNamespace(start=item.actual.get("start", item.planned["start"]), end=item.actual["finish"])
        if actual_mark is not None and item.source_type=="span":
            ax=left+((actual_mark.start-start).days)*day; aw=max(settings["theme"]["bar"]["minWidth"] if settings else 4,(actual_mark.end-actual_mark.start).days*day); parts.append(f'<rect data-scene-id="item:{item.object_id}:actual" data-source-ref="{item.object_id}" data-purpose="actual" x="{ax}" y="{y+layout["bars"]["gap"] if settings else y+4}" width="{aw}" height="{settings["theme"]["bar"]["actualHeight"] if settings else 9}" rx="{settings["theme"]["bar"]["radius"] if settings else 2}" fill="{colors["actual"]}"/>')
            delta_mark = scene_marks.get(item.object_id, {}).get("finish-delta")
            delta = delta_mark.variance_days if delta_mark is not None else item.finish_delta
            if delta is not None:
                suffix, sign = labels["formatting"]["signedDaysSuffix"], labels["formatting"]["positiveSign"]
                value = f'{sign}{delta}{suffix}' if delta > 0 else f'{delta}{suffix}'
                parts.append(f'<text data-scene-id="item:{item.object_id}:variance" data-source-ref="{item.object_id}" data-purpose="variance" x="{left+(item.planned.get("end",item.planned.get("at"))-start).days*day+layout["variance"]["labelGap"] if settings else left+(item.planned.get("end",item.planned.get("at"))-start).days*day+5}" y="{y+layout["variance"]["offset"] if settings else y+14}" font-family="{escape(font, quote=True)}" font-size="{palette["typography"]["variance"]["size"] if settings else 11}" fill="{colors["behind"]}">{value}</text>')
        else:
            missing_x=left+(item.planned.get("start",item.planned.get("at"))-start).days*day
            parts.append(f'<rect data-scene-id="item:{item.object_id}:missing" data-source-ref="{item.object_id}" data-purpose="actual" x="{missing_x}" y="{y+layout["bars"]["gap"] if settings else y+4}" width="{missing["width"] if settings else 18}" height="{missing["height"] if settings else 9}" fill="url(#missing)"/><text x="{missing_x+(layout["missingActual"]["gap"] if settings else 22)}" y="{y+body["size"]}" font-family="{escape(font, quote=True)}" font-size="{palette["typography"]["missingActual"]["size"] if settings else 10}">{escape(labels["missingActualLabel"])}</text>')
    if projection.unmatched_actual_ids:
        line = labels["unmatchedActual"].replace("{unmatchedIds}", labels.get("listSeparator", ", ").join(projection.unmatched_actual_ids))
        parts.append(f'<text x="{left}" y="{height-layout["margins"]["bottom"] if settings else height-24}" font-family="{escape(font, quote=True)}" font-size="{body["size"]}" fill="{colors["behind"]}">{escape(line)}</text>')
    return "\n".join(parts+["</svg>"])+"\n"



def render_table_timeline_svg(title: str, projection: ReviewProjection, project: dict[str, Any], view: dict[str, Any], theme: dict[str, Any], capabilities: set[str], profile: dict[str, Any], slots: dict[str, Any] | None = None, settings: dict[str, Any] | None = None, surface_content: Any | None = None) -> str:
    """One generic layout-backed adapter; no sample-specific branches."""
    from chrona.presentation.renderers.table_timeline import render_gantt
    required = {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}
    if not required.issubset(capabilities):
        raise ValueError("E_OUTPUT_CAPABILITY_MISSING")
    presentation_scene = None
    if settings is not None:
        from chrona.presentation.scene.builder import build_presentation_scene
        content = surface_content or _surface_content_input(projection, project, view, settings)
        content = replace(
            content, template_values=tuple((key, title if key == "title" else value)
                                           for key, value in content.template_values))
        presentation_scene = build_presentation_scene(title, projection.items, projection.window, settings, content)
        from chrona.presentation.renderers.scene_svg import render_scene_surface_svg
        surface = next((candidate for candidate in presentation_scene.surfaces
                        if candidate.surface_id == "table-timeline"), None)
        if surface is None:
            raise ValueError("E_PRESENTATION_SURFACE_MISSING")
        return render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    return render_gantt(title, projection, project, view, theme, profile, slots, settings, presentation_scene=presentation_scene)


def append_review_summary(svg: str, projection: ReviewProjection, profile: dict[str, Any], as_of: date, rect: Any | None = None, settings: dict[str, Any] | None = None) -> str:
    """Append only declared, read-only M16 metrics to an existing SVG composition."""
    if settings is not None:
        raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
    total=len(projection.items); actual=sum(bool(item.actual) for item in projection.items)
    points=sorted(item.planned["at"] for item in projection.items if item.source_type=="point" and item.planned["at"]>=as_of)
    values={"selectedCount":str(total),"actualCoverage":f"{actual}/{total}" if total else "unknown","knownFinishVarianceCount":str(sum(item.finish_delta is not None for item in projection.items)),"missingActualCount":str(total-actual),"nextPlannedPoint":points[0].isoformat() if points else "unknown"}
    labels = settings["detail"]["summaryLabels"] if settings else {"selectedCount":"Selected work","actualCoverage":"Actual coverage","knownFinishVarianceCount":"Known finish variance","missingActualCount":"Missing Actual","nextPlannedPoint":"Next planned point"}
    font = settings["theme"]["fontFamily"] if settings else "Inter, Arial, sans-serif"
    heading = settings["theme"]["typography"]["summaryHeader"] if settings else {"size": 11, "weight": 700}
    metric_style = settings["theme"]["typography"]["summaryMetric"] if settings else {"size": 10, "weight": 400}
    separator = settings["detail"]["formatting"]["rangeSeparator"] if settings else ": "
    lines=[]; x=getattr(rect,"x",32); y=getattr(rect,"y",24)+22
    for panel in profile["panels"]:
        lines.append(f'<text data-purpose="summary-panel" data-source-ref="derived:{escape(panel["id"])}" x="{x}" y="{y}" font-family="{escape(font, quote=True)}" font-size="{heading["size"]}" font-weight="{heading["weight"]}">{escape(panel["id"])}</text>'); y+=heading["size"] + 4
        for metric in panel["metrics"]:
            lines.append(f'<text data-purpose="summary-metric" data-source-ref="derived:{escape(panel["id"])}:{metric}" x="{x}" y="{y}" font-family="{escape(font, quote=True)}" font-size="{metric_style["size"]}" font-weight="{metric_style["weight"]}">{escape(labels[metric])}{escape(separator)}{escape(values[metric])}</text>'); y+=metric_style["size"] + 3
        y+=6
    return svg.replace("</svg>", "\n".join(lines)+"\n</svg>")
