"""Painted-ink contact for already selected completed vector symbols.

This module knows nothing about scene roles, source identity, selection order,
or contrast policy. Its caller supplies the symbol parts and the text bounds.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Iterable, Mapping

from chrona.presentation.scene.ink_touch import InkTouchError, fill_touches, stroke_touches
from chrona.presentation.scene.paint_analysis import is_hex_color

Ink = tuple[str, str, float]  # completed part id, paint color, opacity
InkBounds = tuple[float, float, float, float]


def selected_symbol_ink(symbols: Iterable[Mapping[str, Any]], bounds: InkBounds, *,
                        unreadable_identity: str = "sparse-ink") -> tuple[list[Ink], str | None]:
    """Return touching readable fill/stroke inks, or the identity of unreadable ink.

    A touching malformed part or invalid opacity fails closed. Untouched parts
    do not contribute paint and therefore need not have readable opacity.
    The caller owns the fallback identity for a part with no completed ID.
    """
    found: list[Ink] = []
    for symbol_part in symbols:
        part_id = symbol_part.get("id") if isinstance(symbol_part.get("id"), str) else None
        paint = symbol_part.get("paint")
        symbol = symbol_part.get("symbol")
        outline = symbol.get("outline") if isinstance(symbol, Mapping) else None
        if not isinstance(paint, Mapping) or not isinstance(outline, list) or part_id is None:
            return [], part_id or unreadable_identity
        width, opacity = paint.get("strokeWidth"), paint.get("opacity", 1.0)
        stroked = is_hex_color(paint.get("stroke")) and isinstance(width, (int, float)) and width > 0
        filled = is_hex_color(paint.get("fill"))
        try:
            if filled:
                touches = fill_touches(outline, bounds)
            elif stroked:
                touches = stroke_touches(outline, bounds, float(width))
            else:
                continue
        except InkTouchError:
            return [], part_id
        if not touches:
            continue
        if not valid_opacity(opacity):
            return [], part_id
        found.append((part_id, str(paint["fill"] if filled else paint["stroke"]), float(opacity)))
    return found, None


def valid_opacity(value: Any) -> bool:
    """Whether a completed paint opacity can be composited without guessing."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and isfinite(float(value)) and 0 <= float(value) <= 1)
