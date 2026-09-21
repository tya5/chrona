"""Measured text placement shared by surface Layout and Scene projection."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import TextPlacement


def measure_text_width(content: str, *, font_size: float, font_metrics: Any) -> float:
    """Measure text width at the Layout boundary."""
    return float(font_metrics.width(content, font_size))


def place_text(*, placement_id: str, source_ref: str, content: str,
               inline: float, baseline_block: float, typography_role: str,
               theme_tokens: Any, font_metrics: Any, overflow: str = "fit",
               required: bool = True, collision_region: str = "surface") -> TextPlacement:
    """Measure one text run before Scene turns it into a primitive."""
    family, weight, size, line_height = theme_tokens.typography(typography_role)
    font_size, leading = float(size), float(line_height)
    width = measure_text_width(content, font_size=font_size, font_metrics=font_metrics)
    return TextPlacement(
        placement_id, source_ref, content,
        Rect(Decimal(str(inline)), Decimal(str(baseline_block - font_size)),
             Decimal(str(width)), Decimal(str(font_size * leading))),
        typography_role, overflow, required,
        baseline=(inline, baseline_block), lines=(content,), font_family=family,
        font_weight=int(weight), font_size=font_size, line_height=leading,
        font_asset_identity=str(font_metrics.content_identity), collision_region=collision_region,
    )
