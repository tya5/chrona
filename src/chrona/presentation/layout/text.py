"""Measured text placement shared by surface Layout and Scene projection."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import CollisionDomain, TextPlacement


def measure_text_width(content: str, *, font_size: float, font_metrics: Any) -> float:
    """Measure text width at the Layout boundary."""
    return float(font_metrics.width(content, font_size))


def ellipsize_text(content: str, *, available_inline: float, font_size: float, font_metrics: Any) -> str:
    """Return the longest deterministic source prefix that fits with an ellipsis."""
    if measure_text_width(content, font_size=font_size, font_metrics=font_metrics) <= available_inline:
        return content
    marker = "…"
    if measure_text_width(marker, font_size=font_size, font_metrics=font_metrics) > available_inline:
        return ""
    prefix = content
    while prefix and measure_text_width(prefix + marker, font_size=font_size, font_metrics=font_metrics) > available_inline:
        prefix = prefix[:-1]
    return prefix + marker


def wrap_text(content: str, *, available_inline: float, font_size: float, font_metrics: Any) -> tuple[str, ...]:
    """Greedily wrap words with measured widths; long tokens remain intact."""
    if available_inline <= 0:
        raise ValueError("E_PRESENTATION_WRAP_INPUT")
    lines: list[str] = []
    current = ""
    for word in content.split():
        candidate = word if not current else f"{current} {word}"
        if current and measure_text_width(candidate, font_size=font_size, font_metrics=font_metrics) > available_inline:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return tuple(lines or [content])


def place_text(*, placement_id: str, source_ref: str, content: str,
               inline: float, baseline_block: float, typography_role: str,
               theme_tokens: Any, font_metrics: Any, overflow: str = "fit",
               required: bool = True, collision_region: str = "surface",
               collision_domain: CollisionDomain = CollisionDomain("surface", "content"),
               source_content: str | None = None, lines: tuple[str, ...] | None = None,
               available_inline_start: float | None = None,
               available_inline_size: float | None = None) -> TextPlacement:
    """Measure one text run before Scene turns it into a primitive."""
    family, weight, size, line_height = theme_tokens.typography(typography_role)
    font_size, leading = float(size), float(line_height)
    resolved_lines = lines or (content,)
    width = max(measure_text_width(line, font_size=font_size, font_metrics=font_metrics) for line in resolved_lines)
    return TextPlacement(
        placement_id, source_ref, content,
        Rect(Decimal(str(inline)), Decimal(str(baseline_block - font_size)),
             Decimal(str(width)), Decimal(str(font_size * leading * len(resolved_lines)))),
        typography_role, overflow, required,
        baseline=(inline, baseline_block), lines=resolved_lines, font_family=family,
        font_weight=int(weight), font_size=font_size, line_height=leading,
        font_asset_identity=str(font_metrics.content_identity), collision_region=collision_region,
        collision_domain=collision_domain,
        source_content=source_content,
        available_inline_start=available_inline_start,
        available_inline_size=available_inline_size,
    )
