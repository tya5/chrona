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
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(width)}" height="{number(height)}" viewBox="0 0 {number(width)} {number(height)}" role="img">',
             f'<rect width="{number(width)}" height="{number(height)}" fill="{color("background", "fill")}"/>']
    for node in surface.primitives:
        common = f'data-scene-id="{escape(node.scene_id)}" data-source-ref="{escape(node.source_ref)}" data-purpose="{escape(node.purpose)}"'
        x, y, w, h = node.bounds
        if node.kind == "Rect":
            parts.append(f'<rect {common} x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" fill="{color(node.visual_role, "fill")}"/>')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            parts.append(f'<text {common} x="{number(node.baseline[0])}" y="{number(node.baseline[1])}" font-family="{escape(node.text_layout.family, quote=True)}" font-weight="{node.text_layout.weight}" fill="{color(node.visual_role, "fill")}">{escape(node.text)}</text>')
        elif node.kind == "Symbol":
            if node.shape != "diamond": raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            points = ((x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2))
            parts.append(f'<polygon {common} points="{" ".join(f"{number(px)},{number(py)}" for px,py in points)}" fill="{color(node.visual_role, "fill")}"/>')
        elif node.kind == "Path":
            if len(node.points) < 2: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            path = "M" + "L".join(f"{number(px)} {number(py)}" for px, py in node.points)
            parts.append(f'<path {common} d="{path}" fill="none" stroke="{color(node.visual_role, "stroke")}"/>')
        else: raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join((*parts, "</svg>")) + "\n"
