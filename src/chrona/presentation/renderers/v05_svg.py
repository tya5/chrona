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
    marker_pairs = {(completed(node).stroke, node.shape) for node in surface.primitives if node.kind == "Path" and node.shape}
    patterns = {(node.visual_role, node.pattern, completed(node)) for node in surface.primitives if node.pattern}
    has_links = any(node.href is not None for node in surface.primitives)
    ns = ' xmlns:xlink="http://www.w3.org/1999/xlink"' if has_links else ""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg"{ns} width="{number(width)}" height="{number(height)}" viewBox="0 0 {number(width)} {number(height)}" role="img">',
             f'<rect width="{number(width)}" height="{number(height)}" {attrs(surface.canvas_paint, fill=True, stroke=False)}/>']
    paints = (surface.canvas_paint, *(completed(node) for node in surface.primitives))
    gradients = {gradient_id(paint): paint.gradient for paint in paints if paint.gradient}
    shadows = {shadow_id(paint): paint.shadow for paint in paints if paint.shadow}
    if marker_pairs or patterns or gradients or shadows:
        definitions: list[str] = []
        for color, marker in sorted(marker_pairs):
            if marker != "triangle" or color is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            definitions.append(f'<marker id="marker-{escape(color, quote=True)}-{marker}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="{escape(color, quote=True)}"/></marker>')
        for role, pattern, paint in sorted(patterns, key=lambda item: (item[0], item[1] or "")):
            if paint.stroke is None or paint.stroke_width is None: raise ValueError("E_PRESENTATION_PAINT_INVALID")
            if pattern == "diagonal-hatch":
                definitions.append(f'<pattern id="pattern-{role}-{pattern}" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" {attrs(paint, fill=False, stroke=True)}/></pattern>')
            elif pattern != "outline": raise ValueError("E_PRESENTATION_PATTERN_UNSUPPORTED")
        for identifier, gradient in sorted(gradients.items()):
            assert gradient is not None
            definitions.append(f'<linearGradient id="{identifier}" gradientUnits="userSpaceOnUse" x1="{number(gradient.start[0])}" y1="{number(gradient.start[1])}" x2="{number(gradient.end[0])}" y2="{number(gradient.end[1])}">' + "".join(f'<stop offset="{number(position * 100)}%" stop-color="{escape(color, quote=True)}"/>' for position, color in gradient.stops) + '</linearGradient>')
        for identifier, shadow in sorted(shadows.items()):
            assert shadow is not None
            definitions.append(f'<filter id="{identifier}"><feDropShadow dx="{number(shadow.offset_x)}" dy="{number(shadow.offset_y)}" stdDeviation="{number(shadow.blur)}" flood-color="{escape(shadow.color, quote=True)}" flood-opacity="{number(shadow.opacity)}"/></filter>')
        parts.append("<defs>" + "".join(definitions) + "</defs>")
    def append(node: ScenePrimitive, content: str) -> None:
        paint = completed(node)
        if node.href is None: parts.append(content); return
        title = f' xlink:title="{escape(node.link_title, quote=True)}"' if node.link_title is not None else ""
        parts.append(f'<a href="{escape(node.href, quote=True)}" target="_top"{title}>{content}</a>')
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
            if node.pattern == "outline": appearance = attrs(paint, fill=False, stroke=True)
            elif node.pattern == "diagonal-hatch": appearance = f'fill="url(#pattern-{escape(node.visual_role, quote=True)}-{node.pattern})" ' + attrs(paint, fill=False, stroke=True)
            elif node.pattern is None: appearance = attrs(paint, fill=paint.fill is not None, stroke=paint.stroke is not None)
            else: raise ValueError("E_PRESENTATION_PATTERN_UNSUPPORTED")
            radius = f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"' if node.corner_radius else ""
            append(node, f'<rect {common} x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{radius} {appearance}/>')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            lines = node.text_layout.lines
            body = escape(lines[0]) if len(lines) == 1 else "".join(f'<tspan x="{number(node.baseline[0])}" dy="{0 if index == 0 else number(node.text_layout.font_size * node.text_layout.line_height)}">{escape(line)}</tspan>' for index, line in enumerate(lines))
            append(node, f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" font-family="{escape(node.text_layout.family, quote=True)}" font-weight="{node.text_layout.weight}" font-size="{number(node.text_layout.font_size)}" {attrs(paint, fill=True, stroke=False)}>{body}</text>')
        elif node.kind == "Symbol":
            if node.shape != "diamond": raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            appearance = attrs(paint, fill=paint.fill is not None, stroke=paint.stroke is not None)
            if node.path_commands: append(node, f'<path {common} d="{path_data(node)}" {appearance}/>')
            else:
                points = " ".join(f"{number(px)},{number(py)}" for px, py in ((x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2)))
                append(node, f'<polygon {common} points="{points}" {appearance}/>')
        elif node.kind == "Path":
            if len(node.points) < 2 or paint.stroke is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            marker = f' marker-end="url(#marker-{escape(paint.stroke, quote=True)}-{escape(node.shape, quote=True)})"' if node.shape else ""
            append(node, f'<path {common} d="{path_data(node)}" fill="none" {attrs(paint, fill=False, stroke=True)}{marker}/>')
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
    return "\n".join((*parts, "</svg>")) + "\n"


class V05SvgRenderer:
    target_kind = "svg"

    def render(self, surface: object, *, viewport: tuple[float, float]) -> RenderArtifact:
        if not isinstance(surface, SceneSurface): raise ValueError("E_PRESENTATION_RENDER_INPUT")
        return RenderArtifact("svg", "image/svg+xml", render_v05_svg(surface, viewport=viewport).encode("utf-8"), "chrona-svg-v0.5")
