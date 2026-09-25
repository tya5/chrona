"""SVG formatting for a completed portable visual SceneSurface."""
from __future__ import annotations

from html import escape
from hashlib import sha256
from base64 import b64encode

from chrona.core.ports import RenderArtifact
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface


def render_v05_svg(surface: SceneSurface, *, viewport: tuple[float, float]) -> str:
    """Serialize completed primitives only; Theme and Scheme are not renderer inputs."""
    if surface.canvas_paint is None or surface.canvas_paint.fill is None:
        raise ValueError("E_PRESENTATION_PAINT_INVALID")
    width, height = viewport
    def number(value: float) -> str: return f"{value:.3f}".rstrip("0").rstrip(".")
    def completed(node: ScenePrimitive) -> ScenePaint:
        if node.paint is None: raise ValueError("E_PRESENTATION_PAINT_INVALID")
        return node.paint
    def path_data(node: ScenePrimitive) -> str:
        if not node.path_commands: return "M" + "L".join(f"{number(px)} {number(py)}" for px, py in node.points)
        parts: list[str] = []
        for command in node.path_commands:
            if command.kind == "move": parts.append("M" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "line": parts.append("L" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "quadratic": parts.append("Q" + " ".join(number(value) for point in command.points for value in point))
            else: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        return "".join(parts)
    def attrs(paint: ScenePaint, *, fill: bool, stroke: bool) -> str:
        result = [f'opacity="{number(paint.opacity)}"']
        if fill:
            if paint.fill is None: raise ValueError("E_PRESENTATION_PAINT_INVALID")
            value = paint.fill
            if paint.gradient is not None:
                value = f"url(#{gradient_id(paint)})"
            result.append(f'fill="{escape(value, quote=True)}"')
        if stroke:
            if paint.stroke is None or paint.stroke_width is None: raise ValueError("E_PRESENTATION_PAINT_INVALID")
            result.extend((f'stroke="{escape(paint.stroke, quote=True)}"', f'stroke-width="{number(paint.stroke_width)}"'))
            if paint.dash: result.append(f'stroke-dasharray="{" ".join(number(value) for value in paint.dash)}"')
            if paint.stroke_finish is not None:
                result.extend((f'stroke-linecap="{paint.stroke_finish.line_cap}"', f'stroke-linejoin="{paint.stroke_finish.line_join}"'))
        if paint.shadow is not None:
            result.append(f'filter="url(#{shadow_id(paint)})"')
        return " ".join(result)
    def gradient_id(paint: ScenePaint) -> str:
        assert paint.gradient is not None
        payload = repr((paint.gradient.start, paint.gradient.end, paint.gradient.stops)).encode()
        return "gradient-" + sha256(payload).hexdigest()[:12]
    def shadow_id(paint: ScenePaint) -> str:
        assert paint.shadow is not None
        return "shadow-" + sha256(repr(paint.shadow).encode()).hexdigest()[:12]
    def commands_data(commands: tuple[object, ...]) -> str:
        parts: list[str] = []
        for command in commands:
            if command.kind == "move": parts.append("M" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "line": parts.append("L" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "quadratic": parts.append("Q" + " ".join(number(value) for point in command.points for value in point))
            else: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        return "".join(parts)
    def marker_id(color: str, geometry: object) -> str:
        return "marker-" + sha256(repr((color, geometry)).encode()).hexdigest()[:12]
    def pattern_id(geometry: object, paint: ScenePaint) -> str:
        return "pattern-" + sha256(repr((geometry, paint.stroke, paint.opacity)).encode()).hexdigest()[:12]
    marker_pairs = {(completed(node).stroke, marker) for node in surface.primitives if node.kind == "Path"
                    for marker in (node.marker_start, node.marker_end) if marker}
    patterns = {(node.pattern, completed(node)) for node in surface.primitives if node.pattern}
    has_links = any(node.href is not None for node in surface.primitives)
    ns = ' xmlns:xlink="http://www.w3.org/1999/xlink"' if has_links else ""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg"{ns} width="{number(width)}" height="{number(height)}" viewBox="0 0 {number(width)} {number(height)}" role="img">',
             f'<rect width="{number(width)}" height="{number(height)}" {attrs(surface.canvas_paint, fill=True, stroke=False)}/>']
    paints = (surface.canvas_paint, *(completed(node) for node in surface.primitives))
    gradients = {gradient_id(paint): paint.gradient for paint in paints if paint.gradient}
    shadows = {shadow_id(paint): paint.shadow for paint in paints if paint.shadow}
    clip_hosts = {node.scene_id: node for node in surface.primitives
                  if any(item.clip_source_id == node.scene_id for item in surface.primitives)}
    if marker_pairs or patterns or gradients or shadows or clip_hosts:
        definitions: list[str] = []
        for color, marker in sorted(marker_pairs, key=repr):
            if color is None or marker is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            appearance = (f'fill="{escape(color, quote=True)}"' if marker.paint_mode == "fill"
                          else f'fill="none" stroke="{escape(color, quote=True)}"')
            definitions.append(f'<marker id="{marker_id(color, marker)}" viewBox="0 0 {number(marker.head_length)} {number(marker.head_width)}" refX="{number(marker.head_length - marker.attachment_offset)}" refY="{number(marker.head_width / 2)}" markerWidth="{number(marker.head_length)}" markerHeight="{number(marker.head_width)}" orient="auto"><path d="{commands_data(marker.outline)}" {appearance}/></marker>')
        for pattern, paint in sorted(patterns, key=repr):
            if paint.stroke is None or paint.stroke_width is None: raise ValueError("E_PRESENTATION_PAINT_INVALID")
            strokes = "".join(f'<line x1="{number(stroke.start[0])}" y1="{number(stroke.start[1])}" x2="{number(stroke.end[0])}" y2="{number(stroke.end[1])}" opacity="{number(paint.opacity)}" fill="none" stroke="{escape(paint.stroke, quote=True)}" stroke-width="{number(stroke.width)}"/>' for stroke in pattern.strokes)
            definitions.append(f'<pattern id="{pattern_id(pattern, paint)}" patternUnits="userSpaceOnUse" width="{number(pattern.tile_inline_size)}" height="{number(pattern.tile_block_size)}" patternTransform="rotate({number(pattern.angle_degrees)})">{strokes}</pattern>')
        for identifier, gradient in sorted(gradients.items()):
            assert gradient is not None
            definitions.append(f'<linearGradient id="{identifier}" gradientUnits="userSpaceOnUse" x1="{number(gradient.start[0])}" y1="{number(gradient.start[1])}" x2="{number(gradient.end[0])}" y2="{number(gradient.end[1])}">' + "".join(f'<stop offset="{number(position * 100)}%" stop-color="{escape(color, quote=True)}"/>' for position, color in gradient.stops) + '</linearGradient>')
        for identifier, shadow in sorted(shadows.items()):
            assert shadow is not None
            definitions.append(f'<filter id="{identifier}"><feDropShadow dx="{number(shadow.offset_x)}" dy="{number(shadow.offset_y)}" stdDeviation="{number(shadow.blur)}" flood-color="{escape(shadow.color, quote=True)}" flood-opacity="{number(shadow.opacity)}"/></filter>')
        for identifier, host in sorted(clip_hosts.items()):
            if host.kind not in {"Rect", "Symbol"}:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if host.kind == "Rect":
                x, y, w, h = host.bounds
                radius = f' rx="{number(host.corner_radius)}" ry="{number(host.corner_radius)}"' if host.corner_radius else ""
                clip_content = f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{radius}/>'
            else:
                if host.symbol is None:
                    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                clip_content = f'<path d="{commands_data(host.symbol.outline)}"/>'
            definitions.append(f'<clipPath id="clip-{escape(identifier, quote=True)}">{clip_content}</clipPath>')
        parts.append("<defs>" + "".join(definitions) + "</defs>")
    rendered: list[tuple[ScenePrimitive, str]] = []
    def append(node: ScenePrimitive, content: str) -> None:
        rendered.append((node, content))
    def link(node: ScenePrimitive, content: str) -> str:
        if node.href is None:
            return content
        title = f' xlink:title="{escape(node.link_title, quote=True)}"' if node.link_title is not None else ""
        return f'<a href="{escape(node.href, quote=True)}" target="_top"{title}>{content}</a>'
    def icon_path(path: object) -> str:
        values: list[str] = []
        for kind, points in path.commands:
            glyph = {"move": "M", "line": "L", "quadratic": "Q", "cubic": "C", "close": "Z"}.get(kind)
            if glyph is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            values.append(glyph if glyph == "Z" else glyph + " ".join(f"{number(px)} {number(py)}" for px, py in points))
        return "".join(values)

    def icon_appearance(path: object) -> str:
        if path.fill is not None and path.stroke is None:
            return f'fill="{escape(path.fill, quote=True)}" opacity="{number(path.opacity)}"'
        if path.fill is None and path.stroke is not None and path.stroke_width is not None:
            return (f'fill="none" opacity="{number(path.opacity)}" stroke="{escape(path.stroke, quote=True)}" '
                    f'stroke-width="{number(path.stroke_width)}" stroke-linecap="{path.line_cap}" stroke-linejoin="{path.line_join}"')
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    for node in surface.primitives:
        common = f'data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" data-purpose="{escape(node.purpose)}"'
        paint, (x, y, w, h) = completed(node), node.bounds
        if node.kind == "Rect":
            appearance = (f'fill="url(#{pattern_id(node.pattern, paint)})" ' + attrs(paint, fill=False, stroke=True)
                          if node.pattern is not None else attrs(paint, fill=paint.fill is not None, stroke=paint.stroke is not None))
            radius = f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"' if node.corner_radius else ""
            clip = f' clip-path="url(#clip-{escape(node.clip_source_id, quote=True)})"' if node.clip_source_id else ""
            append(node, f'<rect {common} x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{radius}{clip} {appearance}/>')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            lines = node.text_layout.lines
            body = escape(lines[0]) if len(lines) == 1 else "".join(f'<tspan x="{number(node.baseline[0])}" dy="{0 if index == 0 else number(node.text_layout.font_size * node.text_layout.line_height)}">{escape(line)}</tspan>' for index, line in enumerate(lines))
            append(node, f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" font-family="{escape(node.text_layout.family, quote=True)}" font-weight="{node.text_layout.weight}" font-size="{number(node.text_layout.font_size)}" {attrs(paint, fill=True, stroke=False)}>{body}</text>')
        elif node.kind == "Symbol":
            if node.symbol is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            appearance = attrs(paint, fill=paint.fill is not None, stroke=paint.stroke is not None)
            append(node, f'<path {common} d="{commands_data(node.symbol.outline)}" {appearance}/>')
        elif node.kind == "Path":
            if len(node.points) < 2 or paint.stroke is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            start = f' marker-start="url(#{marker_id(paint.stroke, node.marker_start)})"' if node.marker_start else ""
            end = f' marker-end="url(#{marker_id(paint.stroke, node.marker_end)})"' if node.marker_end else ""
            append(node, f'<path {common} d="{path_data(node)}" fill="none" {attrs(paint, fill=False, stroke=True)}{start}{end}/>')
        elif node.kind == "Icon":
            if node.icon_kind not in {"vector", "raster"} or node.icon_asset_identity is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            accessible = " aria-hidden=\"true\"" if node.icon_decorative else f' role="img" aria-label="{escape(node.icon_alternative or "", quote=True)}"'
            if not node.icon_decorative and not node.icon_alternative: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if node.icon_kind == "vector":
                if not node.icon_paths: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                paths = "".join(f'<path d="{icon_path(path)}" {icon_appearance(path)}/>' for path in node.icon_paths)
                append(node, f'<g {common}{accessible} data-asset-identity="{escape(node.icon_asset_identity, quote=True)}">{paths}</g>')
            else:
                if node.icon_raster is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                encoded = b64encode(node.icon_raster).decode("ascii")
                append(node, f'<image {common}{accessible} data-asset-identity="{escape(node.icon_asset_identity, quote=True)}" x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" href="data:image/png;base64,{encoded}"/>')
        else: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    mark_purposes = {"planned", "actual", "snapshot", "missingActual", "progress-fill", "icon-mark"}
    visual_marks = [(index, node, content) for index, (node, content) in enumerate(rendered)
                    if node.purpose in mark_purposes]
    for node, content in ((node, content) for node, content in rendered if node.purpose not in mark_purposes):
        parts.append(link(node, content))
    if visual_marks:
        parts.append('<g data-layer="mark-paint" aria-hidden="true">' + "".join(
            content for _, _, content in sorted(visual_marks, key=lambda item: (item[1].paint_order, item[0]))
        ) + '</g>')
        interactions = []
        for _, node, _ in visual_marks:
            if node.href is None:
                continue
            x, y, w, h = node.bounds
            title = f'<title>{escape(node.link_title)}</title>' if node.link_title else ""
            interactions.append(f'<a href="{escape(node.href, quote=True)}" target="_top" data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" data-purpose="{escape(node.purpose)}"><rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" fill="transparent" pointer-events="all"/>{title}</a>')
        if interactions:
            parts.append('<g data-layer="mark-interaction">' + "".join(interactions) + '</g>')
    return "\n".join((*parts, "</svg>")) + "\n"


class V05SvgRenderer:
    target_kind = "svg"

    def render(self, surface: object, *, viewport: tuple[float, float]) -> RenderArtifact:
        if not isinstance(surface, SceneSurface): raise ValueError("E_PRESENTATION_RENDER_INPUT")
        return RenderArtifact("svg", "image/svg+xml", render_v05_svg(surface, viewport=viewport).encode("utf-8"), "chrona-svg-v0.5")
