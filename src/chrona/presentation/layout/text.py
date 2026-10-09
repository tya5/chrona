"""Measured text placement shared by surface Layout and Scene projection."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import AnnotationPresentation, CollisionDomain, TextPlacement


def _text_error(code: str, owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"{code}: {owner} " + ", ".join(fields))


def paint_text(content: str, *, text_transform: str = "none") -> str:
    """Apply the finite treatment before it becomes measured display text."""
    return {
        "none": content,
        "uppercase": content.upper(),
        "lowercase": content.lower(),
        "capitalize": content.title(),
    }[text_transform]


class ScaledMetric:
    """One selected face measured at a declared horizontal compression (#585).

    ``width`` is the base width multiplied by the scale, letter spacing included: that is the width of the same run
    painted through a horizontal transform. Everything else (identity, ascent, numeric features) is the base face's.
    """

    __slots__ = ("base", "scale")

    def __init__(self, base: Any, scale: float) -> None:
        self.base, self.scale = base, scale

    def width(self, *args: Any, **kwargs: Any) -> float:
        return float(self.base.width(*args, **kwargs)) * self.scale

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)


def scaled_metric(font_metrics: Any, horizontal_scale: Any = 1) -> Any:
    """Return the metric itself for scale 1 (default output is the same object), else its compressed measure."""
    scale = float(horizontal_scale)
    if isinstance(font_metrics, ScaledMetric):
        font_metrics = font_metrics.base  # re-base: a scale is applied once, never stacked
    return font_metrics if scale == 1.0 else ScaledMetric(font_metrics, scale)


def metric_for_role(theme_tokens: Any, typography_role: str, font_metrics: Any) -> Any:
    """Select the exact declared metric, at the role's declared compression, before a role can affect geometry."""
    treatment = theme_tokens.text_treatment(typography_role)
    return metric_for_family(treatment.family, int(treatment.weight), font_metrics, treatment.horizontal_scale)


def metric_for_family(family: str, weight: int, font_metrics: Any, horizontal_scale: Any = 1) -> Any:
    """Select one exact metric when a completed placement owns family/weight (and its compression)."""
    if isinstance(font_metrics, ScaledMetric):
        font_metrics = font_metrics.base
    select = getattr(font_metrics, "select", None)
    return scaled_metric(select(family, weight) if callable(select) else font_metrics, horizontal_scale)


def measure_text_width(content: str, *, font_size: float, font_metrics: Any,
                       letter_spacing: float = 0, text_transform: str = "none",
                       numeric_spacing: str = "proportional") -> float:
    """Measure text width at the Layout boundary."""
    content = paint_text(content, text_transform=text_transform)
    supports_numeric_spacing = hasattr(font_metrics, "ensure_numeric_spacing")
    if supports_numeric_spacing:
        font_metrics.ensure_numeric_spacing(numeric_spacing)
    if letter_spacing == 0 and numeric_spacing == "proportional":
        return float(font_metrics.width(content, font_size))
    if numeric_spacing == "proportional":
        return float(font_metrics.width(content, font_size, letter_spacing=letter_spacing))
    if supports_numeric_spacing:
        return float(font_metrics.width(content, font_size, letter_spacing=letter_spacing,
                                        numeric_spacing=numeric_spacing))
    return float(font_metrics.width(content, font_size, letter_spacing=letter_spacing))


def ellipsize_text(content: str, *, available_inline: float, font_size: float, font_metrics: Any,
                   letter_spacing: float = 0, text_transform: str = "none",
                   numeric_spacing: str = "proportional") -> str:
    """Return the longest deterministic source prefix that fits with an ellipsis."""
    if measure_text_width(content, font_size=font_size, font_metrics=font_metrics,
                          letter_spacing=letter_spacing, text_transform=text_transform,
                          numeric_spacing=numeric_spacing) <= available_inline:
        return content
    marker = "…"
    if measure_text_width(marker, font_size=font_size, font_metrics=font_metrics,
                          letter_spacing=letter_spacing, numeric_spacing=numeric_spacing) > available_inline:
        return ""
    prefix = content
    while prefix and measure_text_width(prefix + marker, font_size=font_size, font_metrics=font_metrics,
                                        letter_spacing=letter_spacing, text_transform=text_transform,
                                        numeric_spacing=numeric_spacing) > available_inline:
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


def wrap_text(content: str, *, available_inline: float, font_size: float, font_metrics: Any,
              letter_spacing: float = 0, text_transform: str = "none",
              numeric_spacing: str = "proportional") -> tuple[str, ...]:
    """Greedily wrap words and declared CJK character boundaries by measurement."""
    if available_inline <= 0:
        raise _text_error("E_PRESENTATION_WRAP_INPUT", "text wrapping",
                          available_inline=available_inline, font_size=font_size,
                          letter_spacing=letter_spacing, numeric_spacing=numeric_spacing)
    lines: list[str] = []
    current = ""
    for word in _wrap_units(content):
        separator = " " if current and not (_cjk(word[0]) or _cjk(current[-1])) else ""
        candidate = word if not current else f"{current}{separator}{word}"
        if current and measure_text_width(candidate, font_size=font_size, font_metrics=font_metrics,
                                          letter_spacing=letter_spacing, text_transform=text_transform,
                                          numeric_spacing=numeric_spacing) > available_inline:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return tuple(lines or [content])


def measured_text_bounds(*, inline: float, baseline_block: float, width: float,
                         height: float, font_size: float,
                         rotation: Literal[0, 90, -90]) -> Rect:
    """Close a measured run's bounds with the native baseline-pivot arithmetic."""
    if rotation == 0:
        return Rect(Decimal(str(inline)), Decimal(str(baseline_block - font_size)),
                    Decimal(str(width)), Decimal(str(height)))
    if rotation == 90:
        return Rect(Decimal(str(inline + font_size - height)), Decimal(str(baseline_block)),
                    Decimal(str(height)), Decimal(str(width)))
    return Rect(Decimal(str(inline - font_size)), Decimal(str(baseline_block - width)),
                Decimal(str(height)), Decimal(str(width)))


def place_text(*, placement_id: str, source_ref: str, content: str,
               inline: float, baseline_block: float, typography_role: str,
               theme_tokens: Any, font_metrics: Any, overflow: str = "fit",
               required: bool = True, collision_region: str = "surface",
               collision_domain: CollisionDomain = CollisionDomain("surface", "content"),
               source_content: str | None = None, lines: tuple[str, ...] | None = None,
               available_inline_start: float | None = None,
               available_inline_size: float | None = None,
               slot_id: str | None = None, semantic_id: str = "",
               annotation: AnnotationPresentation | None = None,
               lane_row_id: str | None = None, lane_member_id: str | None = None,
               lane_source_kind: str | None = None,
               orientation: str = "horizontal") -> TextPlacement:
    """Measure one text run before Scene turns it into a primitive."""
    treatment = theme_tokens.text_treatment(typography_role)
    font_metrics = metric_for_role(theme_tokens, typography_role, font_metrics)
    font_size, leading = float(treatment.font_size), float(treatment.line_height)
    source = source_content if source_content is not None else content
    resolved_lines = tuple(paint_text(line, text_transform=treatment.transform) for line in (lines or (content,)))
    painted_content = paint_text(content, text_transform=treatment.transform)
    letter_spacing = float(treatment.letter_spacing)
    width = max(measure_text_width(line, font_size=font_size, font_metrics=font_metrics,
                                   letter_spacing=letter_spacing,
                                   numeric_spacing=treatment.numeric_spacing)
                for line in (lines or (content,)))
    scale = float(treatment.horizontal_scale)
    rotation = {"horizontal": 0, "rotate-cw": 90, "rotate-ccw": -90}.get(orientation)
    if rotation is None:
        raise _text_error("E_PRESENTATION_TEXT_ORIENTATION", "text placement",
                          placement_id=placement_id, orientation=orientation,
                          typography_role=typography_role)
    height = font_size * leading * len(resolved_lines)
    bounds = measured_text_bounds(inline=inline, baseline_block=baseline_block, width=width,
                                  height=height, font_size=font_size, rotation=rotation)
    return TextPlacement(
        placement_id, source_ref, painted_content,
        bounds,
        typography_role, overflow, required,
        baseline=(inline, baseline_block), lines=resolved_lines, font_family=treatment.family,
        font_weight=int(treatment.weight), font_size=font_size, line_height=leading,
        letter_spacing=letter_spacing, text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing,
        orientation=orientation, rotation_degrees=rotation, horizontal_scale=scale,
        font_asset_identity=str(font_metrics.content_identity), collision_region=collision_region,
        collision_domain=collision_domain,
        source_content=source,
        available_inline_start=available_inline_start,
        available_inline_size=available_inline_size,
        slot_id=slot_id or collision_domain.slot,
        semantic_id=semantic_id,
        annotation=annotation,
        lane_row_id=lane_row_id,
        lane_member_id=lane_member_id,
        lane_source_kind=lane_source_kind,
    )
