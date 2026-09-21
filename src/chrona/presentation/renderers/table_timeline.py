"""SVG serialization of a completed renderer-neutral review Scene."""
from __future__ import annotations

from html import escape
from typing import Any, Mapping

from chrona.presentation.scene.review import ReviewScene


def _theme_value(theme: Mapping[str, Any], role: str, property_name: str) -> str:
    body = theme.get("body", {})
    binding = body.get("roles", {}).get(role, {}).get(property_name)
    declared = body.get("values", {}).get(binding)
    if not isinstance(declared, Mapping) or not isinstance(declared.get("value"), str):
        raise ValueError("E_THEME_ROLE_REQUIRED")
    return str(declared["value"])


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def render_gantt(scene: ReviewScene, theme: Mapping[str, Any], *, font_size: float) -> str:
    """Serialize primitives verbatim; geometry and source meaning are already closed."""
    font = _theme_value(theme, "text", "fontFamily")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_number(scene.width)}" height="{_number(scene.height)}" viewBox="0 0 {_number(scene.width)} {_number(scene.height)}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(scene.title)}</title>',
        f'<desc id="desc">{escape(scene.description)}</desc>',
        '<metadata data-presentation-scene="intent-layout-v0.2"/>',
    ]
    for item in scene.primitives:
        attrs = f'data-purpose="{escape(item.purpose)}" data-source-ref="{escape(item.source_ref)}"'
        if item.kind == "text":
            assert item.baseline is not None
            ink = _theme_value(theme, item.visual_role, "fill")
            parts.append(f'<text {attrs} x="{_number(item.baseline[0])}" y="{_number(item.baseline[1])}" font-family="{escape(font, quote=True)}" font-size="{_number(font_size)}" font-weight="{item.shape or "400"}" fill="{escape(ink, quote=True)}">{escape(item.text or "")}</text>')
        elif item.kind == "rect":
            x, y, width, height = item.bounds
            fill = _theme_value(theme, item.visual_role, "fill")
            parts.append(f'<rect {attrs} x="{_number(x)}" y="{_number(y)}" width="{_number(width)}" height="{_number(height)}" fill="{escape(fill, quote=True)}"/>')
        elif item.kind == "line":
            (x1, y1), (x2, y2) = item.points
            stroke = _theme_value(theme, item.visual_role, "stroke")
            parts.append(f'<line {attrs} x1="{_number(x1)}" y1="{_number(y1)}" x2="{_number(x2)}" y2="{_number(y2)}" stroke="{escape(stroke, quote=True)}"/>')
        elif item.kind == "polygon":
            fill = _theme_value(theme, item.visual_role, "fill")
            points = " ".join(f"{_number(x)},{_number(y)}" for x, y in item.points)
            parts.append(f'<polygon {attrs} points="{points}" fill="{escape(fill, quote=True)}"/>')
        else:
            raise ValueError("E_SCENE_PRIMITIVE_UNKNOWN")
    return "\n".join((*parts, "</svg>")) + "\n"
