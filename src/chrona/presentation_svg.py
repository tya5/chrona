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
        "table-header": paints["tableHeader"]["color"], "table-frame": strokes["frame"]["color"],
        "table-row": strokes["rowRule"]["color"], "group-separator": strokes["groupSeparator"]["color"],
        "row-shade": paints["rowShade"]["color"],
        "planned": paints["planned"]["color"], "baseline": paints["planned"]["color"],
        "actual": paints["actual"]["color"], "variance": paints["varianceBehind"]["color"],
        "variance-ahead": paints["varianceAhead"]["color"],
        "variance-on-track": paints["varianceOnTrack"]["color"],
        "variance-behind": paints["varianceBehind"]["color"],
        "variance-unknown": paints["varianceUnknown"]["color"],
        "missing-actual": paints["textMuted"]["color"],
        "milestone": paints["milestone"]["color"], "dependency": strokes["dependency"]["color"],
        "presentation-annotation": theme["annotation"]["boxStroke"]["color"],
        "year": strokes["axisMajor"]["color"],
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
        "table-row-rule": "table-row", "group-separator": "group-separator", "tick": "axis-major",
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
    marker_shapes = {node.shape for node in surface.primitives
                     if node.kind == "Path" and (node.purpose in {"dependency-connector", "explanatory-arrow"}
                                                 or node.visual_role == "dependency")}
    if len(marker_shapes) > 1:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    marker_shape = next(iter(marker_shapes), "none")
    scale = surface.scale_manifest
    if not scale.scale_id or scale.surface_id != surface.surface_id:
        raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
    scene_title = next((node.text for node in surface.primitives if node.purpose == "title-text" and node.text), "Presentation")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(scene_title)}</title>',
        '<desc id="desc">Completed presentation Scene.</desc>',
        _definitions(arrow, dependency_color, marker_shape, theme["missingPattern"],
                     any(node.purpose == "missing-actual-pattern" for node in surface.primitives), number),
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
        if node.lane_group_id is not None and node.stack_index is not None:
            lane += (f' data-lane-group-id="{escape(node.lane_group_id)}"'
                     f' data-stack="{node.stack_index}"')
        if node.purpose == "comparison-mark" and node.source_ref in rows:
            group = groups.get(row_groups[node.source_ref])
            if group is not None:
                lane += f' data-lane-offset="{number(node.bounds[1] - group.content_bounds[1])}"'
        if node.kind == "Rect":
            x, y, rect_width, rect_height = node.bounds
            fill = "none" if node.purpose == "table-frame" else (escape(node.color, quote=True) if node.color else color(role))
            stroke_token = strokes["frame"] if node.purpose == "table-frame" else None
            stroke = escape(stroke_token["color"], quote=True) if stroke_token else "none"
            if node.purpose == "annotation-box":
                fill = escape(theme["annotation"]["boxFill"]["color"], quote=True)
                stroke = escape(theme["annotation"]["boxStroke"]["color"], quote=True)
            elif node.purpose == "missing-actual-pattern":
                fill = "url(#missing-actual-pattern)"
            opacity = ""
            if node.purpose == "group-surface":
                token = theme["groupPaints"].get(node.source_ref, paints["groupBand"])
                opacity = f' opacity="{number(float(token["opacity"]))}"'
            elif node.opacity is not None:
                opacity = f' opacity="{number(node.opacity)}"'
            elif role in {"variance-ahead", "variance-on-track", "variance-behind", "variance-unknown"}:
                opacity = _role_opacity(role, paints, number).replace("fill-opacity", "opacity")
            stroke_attrs = _stroke_attributes(stroke_token, number) if stroke_token else ""
            if node.purpose == "annotation-box":
                opacity = (f' fill-opacity="{number(float(theme["annotation"]["boxFill"]["opacity"]))}"'
                           f' stroke-opacity="{number(float(theme["annotation"]["boxStroke"]["opacity"]))}"')
            radius = (f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"'
                      if node.corner_radius is not None else "")
            parts.append(f'<rect {common}{lane} x="{number(x)}" y="{number(y)}" width="{number(rect_width)}" '
                         f'height="{number(rect_height)}" fill="{fill}" stroke="{stroke}"{stroke_attrs}{opacity}{radius}/>' )
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            type_role = {"legend-label": "legend", "coverage-text": "coverage",
                         "summary-header": "summaryHeader", "summary-metric": "summaryMetric"}.get(node.purpose, role)
            paint_role = ("body" if node.purpose in {"axis-label", "table-column-label", "annotation-text", "project-note"}
                          else role)
            typography = theme["typography"].get(type_role, theme["typography"].get("body", {}))
            anchor = "middle" if node.purpose == "axis-label" else "start"
            opening = (f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" '
                       f'font-family="{escape(node.text_layout.family, quote=True)}" font-size="{typography.get("size", 12)}" '
                       f'font-weight="{node.text_layout.weight}" letter-spacing="{typography.get("letterSpacing", 0)}" '
                       f'fill="{color(paint_role)}"{_role_opacity(paint_role, paints, number)} text-anchor="{anchor}">')
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
            if node.shape not in {"diamond", "circle", "square"}:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            x, y, symbol_width, symbol_height = node.bounds
            cx, cy = x + symbol_width / 2.0, y + symbol_height / 2.0
            fill = escape(node.color, quote=True) if node.color else color(role)
            opacity = f' opacity="{number(node.opacity)}"' if node.opacity is not None else ""
            if node.shape == "circle":
                parts.append(f'<ellipse {common}{lane} cx="{number(cx)}" cy="{number(cy)}" rx="{number(symbol_width / 2.0)}" ry="{number(symbol_height / 2.0)}" fill="{fill}"{opacity}/>')
            elif node.shape == "square":
                parts.append(f'<rect {common}{lane} x="{number(x)}" y="{number(y)}" width="{number(symbol_width)}" height="{number(symbol_height)}" fill="{fill}"{opacity}/>')
            else:
                points = ((cx, y), (x + symbol_width, cy), (cx, y + symbol_height), (x, cy))
                path = "M" + "L".join(f"{number(px)} {number(py)}" for px, py in points) + "Z"
                parts.append(f'<path {common}{lane} d="{path}" fill="{fill}"{opacity}/>')
        elif node.kind == "Path":
            if len(node.points) < 2:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            path = "M" + "L".join(f"{number(x)} {number(y)}" for x, y in node.points)
            path_role = "dependency" if node.purpose in {"dependency-connector", "explanatory-arrow"} else role
            extra = ' fill="none"'
            stroke_token = {
                "tick": strokes["axisMajor"],
                "table-row-rule": strokes["rowRule"],
                "group-separator": strokes["groupSeparator"],
                "dependency-connector": strokes["dependency"],
                "explanatory-arrow": strokes["dependency"],
            }.get(node.purpose)
            annotation_token = theme["annotation"]["leader"] if node.purpose == "annotation-leader" else None
            if node.purpose in {"dependency-connector", "explanatory-arrow"} or node.visual_role == "dependency":
                if node.shape not in {"triangle", "chevron", "none"}:
                    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                if node.shape != "none":
                    extra += ' marker-end="url(#dependency-arrow)"'
            if node.from_port_id:
                extra += f' data-from-port-id="{escape(node.from_port_id)}" data-from-endpoint="{escape(node.from_port_id.rsplit(":", 1)[-1])}"'
            if node.to_port_id:
                extra += f' data-to-port-id="{escape(node.to_port_id)}" data-to-endpoint="{escape(node.to_port_id.rsplit(":", 1)[-1])}"'
            stroke_color = (escape(stroke_token["color"], quote=True) if stroke_token else
                            escape(annotation_token["color"], quote=True) if annotation_token else color(path_role))
            stroke_attrs = _stroke_attributes(stroke_token, number) if stroke_token else ""
            if annotation_token and float(annotation_token.get("opacity", 1)) != 1:
                stroke_attrs += f' stroke-opacity="{number(float(annotation_token["opacity"]))}"'
            parts.append(f'<path {common} d="{path}" stroke="{stroke_color}"{stroke_attrs}{extra}/>')
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join((*parts, "</svg>")) + "\n"


def _stroke_attributes(token: dict, number) -> str:
    attributes = f' stroke-width="{number(float(token["width"]))}"'
    if float(token.get("opacity", 1)) != 1:
        attributes += f' stroke-opacity="{number(float(token["opacity"]))}"'
    dash = token.get("dash", [])
    if dash:
        attributes += ' stroke-dasharray="' + " ".join(number(float(value)) for value in dash) + '"'
    return attributes


def _role_opacity(role: str, paints: dict, number) -> str:
    key = {"variance-ahead": "varianceAhead", "variance-on-track": "varianceOnTrack",
           "variance-behind": "varianceBehind", "variance-unknown": "varianceUnknown"}.get(role)
    if key is None or float(paints[key].get("opacity", 1)) == 1:
        return ""
    return f' fill-opacity="{number(float(paints[key]["opacity"]))}"'


def _definitions(arrow: dict, color: str, shape: str, missing: dict,
                 include_missing: bool, number) -> str:
    definitions = []
    width, height = arrow["width"], arrow["height"]
    if shape != "none":
        common = (f'<marker id="dependency-arrow" markerWidth="{width}" markerHeight="{height}" '
                  f'refX="{width - arrow["tipInset"]}" refY="{height / 2}" orient="{arrow["orientation"]}">')
        if shape == "triangle":
            mark = f'<path d="M0 0L{width} {height / 2}L0 {height}Z" fill="{color}"/>'
        elif shape == "chevron":
            mark = f'<path d="M0 0L{width} {height / 2}L0 {height}" fill="none" stroke="{color}"/>'
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        definitions.append(common + mark + "</marker>")
    if include_missing:
        spacing = number(float(missing["spacing"]))
        stroke = missing["stroke"]
        attributes = _stroke_attributes(stroke, number)
        definitions.append(
            f'<pattern id="missing-actual-pattern" width="{spacing}" height="{spacing}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate({number(float(missing["angle"]))})">'
            f'<path d="M0 0V{spacing}" stroke="{escape(stroke["color"], quote=True)}"{attributes}/></pattern>'
        )
    return "<defs>" + "".join(definitions) + "</defs>" if definitions else "<defs/>"
