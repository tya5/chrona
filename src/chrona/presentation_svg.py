"""SVG serialization for a completed renderer-neutral presentation surface."""
from __future__ import annotations

from html import escape

from .presentation_scene import ScenePrimitive, SceneSurface


def render_scene_surface_svg(surface: SceneSurface, *, viewport: dict, theme: dict) -> str:
    """Serialize Scene payloads in their existing order without geometry generation."""
    width, height = viewport["width"], viewport["height"]
    paints, strokes = theme["paints"], theme["strokes"]
    palette = {
        "heading": paints["text"]["color"], "body": paints["text"]["color"],
        "text-muted": paints["textMuted"]["color"], "tableHeader": paints["tableHeader"]["color"],
        "table-header": paints["tableHeader"]["color"], "table-frame": strokes["axisMajor"]["color"],
        "table-row": strokes["axisMinor"]["color"], "row-shade": paints["rowShade"]["color"],
        "planned": paints["planned"]["color"], "baseline": paints["planned"]["color"],
        "actual": paints["actual"]["color"], "variance": paints["varianceBehind"]["color"],
        "milestone": paints["milestone"]["color"], "dependency": strokes["dependency"]["color"],
        "presentation-annotation": theme["annotation"]["boxStroke"]["color"],
        "month": strokes["axisMajor"]["color"], "quarter": strokes["axisMajor"]["color"],
        "week": strokes["axisMinor"]["color"], "day": strokes["axisMinor"]["color"],
    }

    def number(value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def color(role: str) -> str:
        if role.startswith("group:"):
            token = theme["groupPaints"].get(role.removeprefix("group:"), paints["groupBand"])
            return escape(token["color"], quote=True)
        return escape(palette.get(role, paints["text"]["color"]), quote=True)

    purpose_map = {
        "table-header-band": "table-header", "table-column-label": "table-header",
        "table-row-rule": "table-row", "tick": "axis-major",
        "dependency-connector": "routed-connector", "annotation-box": "presentation-annotation",
        "annotation-text": "presentation-annotation", "project-note": "presentation-annotation",
        "coverage-text": "data-coverage",
        "title-text": "heading", "subtitle-text": "subtitle",
    }
    rows = {row.object_id: row for row in surface.rows}
    groups = {group.group_id: group for group in surface.groups}
    row_groups = {row.object_id: row.group_id for row in surface.rows}
    arrow = theme["arrow"]
    dependency_color = color("dependency")
    scale = surface.scale_manifest
    if not scale.scale_id or scale.surface_id != surface.surface_id:
        raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
    scene_title = next((node.text for node in surface.primitives if node.purpose == "title-text" and node.text), "Presentation")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(scene_title)}</title>',
        '<desc id="desc">Completed presentation Scene.</desc>',
        (f'<defs><marker id="dependency-arrow" markerWidth="{arrow["width"]}" markerHeight="{arrow["height"]}" '
         f'refX="{arrow["width"] - arrow["tipInset"]}" refY="{arrow["height"] / 2}" orient="auto">'
         f'<path d="M0 0L{arrow["width"]} {arrow["height"] / 2}L0 {arrow["height"]}Z" fill="{dependency_color}"/>'
         f'</marker></defs>'),
        f'<rect width="{width}" height="{height}" fill="{escape(paints["background"]["color"], quote=True)}"/>',
        f'<metadata data-presentation-scene="v0.2" data-surface-id="{escape(surface.surface_id)}" '
        f'data-axis-scale-id="{escape(scale.scale_id)}" data-scale-domain-start="{scale.domain_start.isoformat()}" '
        f'data-scale-domain-end="{scale.domain_end.isoformat()}" data-scale-range-start="{number(scale.range_start)}" '
        f'data-scale-range-end="{number(scale.range_end)}" data-scale-origin="{number(scale.origin)}" '
        f'data-scale-unit-ratio="{number(scale.unit_ratio)}" data-primitive-count="{len(surface.primitives)}"/>',
    ]

    for node in surface.primitives:
        purpose = purpose_map.get(node.purpose, node.purpose)
        if node.purpose == "axis-label":
            purpose = "axis-quarter" if node.visual_role == "quarter" else "axis-band"
        elif node.purpose == "comparison-mark":
            purpose = "variance" if node.semantic_facet == "finish-delta" else node.semantic_facet
            if purpose == "baseline":
                purpose = "planned"
        common = (f'data-scene-id="{escape(node.scene_id)}" data-purpose="{escape(purpose)}" '
                  f'data-source-ref="{escape(node.source_ref)}"')
        role = node.visual_role
        if node.purpose == "group-surface":
            role = f"group:{node.source_ref}"
        lane = ""
        if node.purpose == "comparison-mark" and node.source_ref in rows:
            group = groups.get(row_groups[node.source_ref])
            if group is not None:
                lane = f' data-lane-offset="{number(node.bounds[1] - group.content_bounds[1])}"'
        if node.kind == "Rect":
            x, y, rect_width, rect_height = node.bounds
            fill = "none" if node.purpose == "table-frame" else color(role)
            stroke = color("table-frame") if node.purpose == "table-frame" else "none"
            if node.purpose == "annotation-box":
                fill = escape(theme["annotation"]["boxFill"]["color"], quote=True)
                stroke = escape(theme["annotation"]["boxStroke"]["color"], quote=True)
            opacity = ""
            if node.purpose == "group-surface":
                token = theme["groupPaints"].get(node.source_ref, paints["groupBand"])
                opacity = f' opacity="{number(float(token["opacity"]))}"'
            parts.append(f'<rect {common}{lane} x="{number(x)}" y="{number(y)}" width="{number(rect_width)}" '
                         f'height="{number(rect_height)}" fill="{fill}" stroke="{stroke}"{opacity}/>' )
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            type_role = {"legend-label": "legend", "coverage-text": "coverage",
                         "summary-header": "summaryHeader", "summary-metric": "summaryMetric"}.get(node.purpose, role)
            typography = theme["typography"].get(type_role, theme["typography"].get("body", {}))
            anchor = "middle" if node.purpose == "axis-label" else "start"
            opening = (f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" '
                       f'font-family="{escape(node.text_layout.family, quote=True)}" font-size="{typography.get("size", 12)}" '
                       f'font-weight="{node.text_layout.weight}" letter-spacing="{typography.get("letterSpacing", 0)}" '
                       f'fill="{color(role)}" text-anchor="{anchor}">')
            if len(node.text_layout.lines) == 1:
                parts.append(opening + escape(node.text_layout.lines[0]) + '</text>')
            else:
                line_height = float(typography.get("size", 12)) * float(typography.get("lineHeight", 1.2))
                tspans = "".join(
                    f'<tspan x="{number(node.baseline[0])}" dy="{number(0.0 if index == 0 else line_height)}">{escape(line)}</tspan>'
                    for index, line in enumerate(node.text_layout.lines)
                )
                parts.append(opening + tspans + '</text>')
        elif node.kind == "Symbol":
            if node.shape != "diamond":
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            x, y, symbol_width, symbol_height = node.bounds
            cx, cy = x + symbol_width / 2.0, y + symbol_height / 2.0
            points = ((cx, y), (x + symbol_width, cy), (cx, y + symbol_height), (x, cy))
            path = "M" + "L".join(f"{number(px)} {number(py)}" for px, py in points) + "Z"
            parts.append(f'<path {common}{lane} d="{path}" fill="{color(role)}"/>')
        elif node.kind == "Path":
            if len(node.points) < 2:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            path = "M" + "L".join(f"{number(x)} {number(y)}" for x, y in node.points)
            path_role = "dependency" if node.purpose == "dependency-connector" else role
            extra = ' fill="none"'
            if node.purpose in {"dependency-connector", "explanatory-arrow"}:
                extra += ' marker-end="url(#dependency-arrow)"'
            if node.purpose == "tick":
                extra += ' stroke-dasharray="3 4"'
            if node.from_port_id:
                extra += f' data-from-port-id="{escape(node.from_port_id)}" data-from-endpoint="{escape(node.from_port_id.rsplit(":", 1)[-1])}"'
            if node.to_port_id:
                extra += f' data-to-port-id="{escape(node.to_port_id)}" data-to-endpoint="{escape(node.to_port_id.rsplit(":", 1)[-1])}"'
            parts.append(f'<path {common} d="{path}" stroke="{color(path_role)}"{extra}/>')
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join((*parts, "</svg>")) + "\n"
