"""SVG formatting for a completed v0.5 SceneSurface."""
from __future__ import annotations

from html import escape

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneSurface


def render_v05_svg(surface: SceneSurface, *, viewport: tuple[float, float], tokens: ThemeTokenView) -> str:
    """Serialize only completed primitives; never read raw presentation resources."""
    width, height = viewport
    def number(value: float) -> str: return f"{value:.3f}".rstrip("0").rstrip(".")
    def color(role: str, property_name: str) -> str: return escape(tokens.color(role, property_name), quote=True)
    markers = {(node.visual_role, node.shape) for node in surface.primitives if node.kind == "Path" and node.shape}
    patterns = {(node.visual_role, tokens.optional_pattern(node.visual_role))
                for node in surface.primitives if node.kind == "Rect" and tokens.optional_pattern(node.visual_role)}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(width)}" height="{number(height)}" viewBox="0 0 {number(width)} {number(height)}" role="img">',
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
            parts.append(f'<rect {common} x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" {paint}/>')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            parts.append(f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" font-family="{escape(node.text_layout.family, quote=True)}" font-weight="{node.text_layout.weight}" font-size="{number(node.text_layout.font_size)}" fill="{color(node.visual_role, "fill")}">{escape(node.text)}</text>')
        elif node.kind == "Symbol":
            if node.shape != "diamond": raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            points = ((x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2))
            parts.append(f'<polygon {common} points="{" ".join(f"{number(px)},{number(py)}" for px,py in points)}" fill="{color(node.visual_role, "fill")}"/>')
        elif node.kind == "Path":
            if len(node.points) < 2: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            path = "M" + "L".join(f"{number(px)} {number(py)}" for px, py in node.points)
            marker = f' marker-end="url(#marker-{escape(node.visual_role, quote=True)}-{escape(node.shape, quote=True)})"' if node.shape else ""
            parts.append(f'<path {common} d="{path}" fill="none" stroke="{color(node.visual_role, "stroke")}"{marker}/>')
        else: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join((*parts, "</svg>")) + "\n"


class V05SvgRenderer:
    """Port adapter for serialization of completed v0.5 Scene surfaces."""

    def render(self, surface: object, *, viewport: tuple[float, float], tokens: object) -> str:
        if not isinstance(surface, SceneSurface) or not isinstance(tokens, ThemeTokenView):
            raise ValueError("E_PRESENTATION_RENDER_INPUT")
        return render_v05_svg(surface, viewport=viewport, tokens=tokens)
