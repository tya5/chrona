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


def _cjk(character: str) -> bool:
    codepoint = ord(character)
    return (0x3040 <= codepoint <= 0x30FF or 0x3400 <= codepoint <= 0x9FFF
            or 0xAC00 <= codepoint <= 0xD7AF)


_CLOSING = frozenset("、。，．・：；？！ー）］｝」』】〉》")
_OPENING = frozenset("（［｛「『【〈《")


def _wrap_units(content: str) -> tuple[str, ...]:
    """Return words or bounded CJK break units without a Unicode-layout engine."""
    if not any(_cjk(character) for character in content):
        return tuple(content.split())
    units: list[str] = []
    current = ""
    for character in content:
        if character.isspace():
            if current:
                units.append(current); current = ""
            continue
        if _cjk(character):
            if current:
                units.append(current); current = ""
            if units and character in _CLOSING:
                units[-1] += character
            else:
                units.append(character)
            continue
        if character in _CLOSING and units and not current:
            units[-1] += character
            continue
        current += character
        if character in _OPENING:
            continue
    if current:
        if units and units[-1][-1:] in _OPENING:
            units[-1] += current
        else:
            units.append(current)
    return tuple(units)


def wrap_text(content: str, *, available_inline: float, font_size: float, font_metrics: Any) -> tuple[str, ...]:
    """Greedily wrap words and declared CJK character boundaries by measurement."""
    if available_inline <= 0:
        raise ValueError("E_PRESENTATION_WRAP_INPUT")
    lines: list[str] = []
    current = ""
    for word in _wrap_units(content):
        separator = " " if current and not (_cjk(word[0]) or _cjk(current[-1])) else ""
        candidate = word if not current else f"{current}{separator}{word}"
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
               available_inline_size: float | None = None,
               slot_id: str | None = None) -> TextPlacement:
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
        slot_id=slot_id or collision_domain.slot,
    )
