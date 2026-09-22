"""SVG formatting for a completed v0.5 SceneSurface."""
from __future__ import annotations

from html import escape

from chrona.core.ports import RenderArtifact
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneSurface


def render_v05_svg(surface: SceneSurface, *, viewport: tuple[float, float], tokens: ThemeTokenView) -> str:
    """Serialize only completed primitives; never read raw presentation resources."""
    width, height = viewport
    def number(value: float) -> str: return f"{value:.3f}".rstrip("0").rstrip(".")
    def path_data(node) -> str:
        commands = node.path_commands
        if not commands:
            return "M" + "L".join(f"{number(px)} {number(py)}" for px, py in node.points)
        parts = []
        for command in commands:
            if command.kind == "move":
                parts.append("M" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "line":
                parts.append("L" + " ".join(number(value) for value in command.points[0]))
            elif command.kind == "quadratic":
                parts.append("Q" + " ".join(number(value) for point in command.points for value in point))
            else:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        return "".join(parts)
    def color(role: str, property_name: str) -> str: return escape(tokens.color(role, property_name), quote=True)
    markers = {(node.visual_role, node.shape) for node in surface.primitives if node.kind == "Path" and node.shape}
    patterns = {(node.visual_role, tokens.optional_pattern(node.visual_role))
                for node in surface.primitives if node.kind == "Rect" and tokens.optional_pattern(node.visual_role)}
    has_links = any(node.href is not None for node in surface.primitives)
    xlink_namespace = ' xmlns:xlink="http://www.w3.org/1999/xlink"' if has_links else ""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg"{xlink_namespace} width="{number(width)}" height="{number(height)}" viewBox="0 0 {number(width)} {number(height)}" role="img">',
             f'<rect width="{number(width)}" height="{number(height)}" fill="{color("background", "fill")}"/>']
    if markers or patterns:
        definitions = []
        for role, marker in sorted(markers):
            if marker != "triangle": raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            marker_id = f"marker-{role}-{marker}"
            definitions.append(f'<marker id="{marker_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="{color(role, "stroke")}"/></marker>')
        for role, pattern in sorted(patterns):
            pattern_id = f"pattern-{role}-{pattern}"
            if pattern == "diagonal-hatch":
                definitions.append(f'<pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{color(role, "stroke")}" stroke-width="1"/></pattern>')
            elif pattern != "outline":
                raise ValueError("E_PRESENTATION_PATTERN_UNSUPPORTED")
        parts.append("<defs>" + "".join(definitions) + "</defs>")
    def append(node, content: str) -> None:
        """Wrap a completed primitive only when Scene explicitly supplied a link."""
        if node.href is None:
            parts.append(content)
            return
        title = f' xlink:title="{escape(node.link_title, quote=True)}"' if node.link_title is not None else ""
        parts.append(f'<a href="{escape(node.href, quote=True)}" target="_top"{title}>{content}</a>')

    for node in surface.primitives:
        common = f'data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" data-purpose="{escape(node.purpose)}"'
        x, y, w, h = node.bounds
        if node.kind == "Rect":
            pattern = tokens.optional_pattern(node.visual_role)
            if pattern == "outline":
                paint = f'fill="none" stroke="{color(node.visual_role, "stroke")}"'
            elif pattern == "diagonal-hatch":
                paint = f'fill="url(#pattern-{escape(node.visual_role, quote=True)}-{pattern})" stroke="{color(node.visual_role, "stroke")}"'
            elif pattern is None:
                paint = f'fill="{color(node.visual_role, "fill")}"'
            else:
                raise ValueError("E_PRESENTATION_PATTERN_UNSUPPORTED")
            radius = (f' rx="{number(node.corner_radius)}" ry="{number(node.corner_radius)}"'
                      if node.corner_radius is not None and node.corner_radius > 0 else "")
            append(node, f'<rect {common} x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}"{radius} {paint}/>')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            lines = node.text_layout.lines
            if len(lines) == 1:
                body = escape(lines[0])
            else:
                step = number(node.text_layout.font_size * node.text_layout.line_height)
                body = "".join(f'<tspan x="{number(node.baseline[0])}" dy="{0 if index == 0 else step}">{escape(line)}</tspan>'
                               for index, line in enumerate(lines))
            append(node, f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" font-family="{escape(node.text_layout.family, quote=True)}" font-weight="{node.text_layout.weight}" font-size="{number(node.text_layout.font_size)}" fill="{color(node.visual_role, "fill")}">{body}</text>')
        elif node.kind == "Symbol":
            if node.shape != "diamond": raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if node.path_commands:
                append(node, f'<path {common} d="{path_data(node)}" fill="{color(node.visual_role, "fill")}"/>')
            else:
                points = ((x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2))
                append(node, f'<polygon {common} points="{" ".join(f"{number(px)},{number(py)}" for px,py in points)}" fill="{color(node.visual_role, "fill")}"/>')
        elif node.kind == "Path":
            if len(node.points) < 2: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            path = path_data(node)
            marker = f' marker-end="url(#marker-{escape(node.visual_role, quote=True)}-{escape(node.shape, quote=True)})"' if node.shape else ""
            append(node, f'<path {common} d="{path}" fill="none" stroke="{color(node.visual_role, "stroke")}"{marker}/>')
        else: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join((*parts, "</svg>")) + "\n"


class V05SvgRenderer:
    """Port adapter for serialization of completed v0.5 Scene surfaces."""

    target_kind = "svg"

    def render(self, surface: object, *, viewport: tuple[float, float], tokens: object) -> RenderArtifact:
        if not isinstance(surface, SceneSurface) or not isinstance(tokens, ThemeTokenView):
            raise ValueError("E_PRESENTATION_RENDER_INPUT")
        return RenderArtifact("svg", "image/svg+xml", render_v05_svg(surface, viewport=viewport, tokens=tokens).encode("utf-8"), "chrona-svg-v0.5")
