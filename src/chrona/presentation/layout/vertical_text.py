"""Vertical writing mode for one short label: a single column read top to bottom (#585, Specification 07).

Layout completes every segment as its own measured `TextPlacement` in the existing Scene vocabulary: an upright
character is a horizontal Text, a sideways run is a quarter turn clockwise. No adapter shapes vertical text, so SVG,
PNG, Typst and TikZ draw it as they draw any horizontal or quarter-turn Text.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import Rect, geometry_sum
from chrona.presentation.layout.surface_quality import CollisionDomain, TextPlacement
from chrona.presentation.layout.text import measure_text_width, metric_for_role, paint_text, place_text

# Vertical forms of these glyphs are the horizontal glyph turned a quarter turn, so they belong to a sideways run.
_ROTATED = frozenset("ー〜～―—…‥（）［］｛｝「」『』【】〈〉《》〔〕()[]{}")
_UPRIGHT_RANGES = ((0x3000, 0x303F), (0x3041, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xAC00, 0xD7AF),
                   (0xF900, 0xFAFF), (0xFF01, 0xFF60))


def is_upright(character: str) -> bool:
    """True for kana, ideographs, Hangul and CJK/fullwidth forms that stand upright in a vertical column."""
    if character in _ROTATED:
        return False
    codepoint = ord(character)
    return any(low <= codepoint <= high for low, high in _UPRIGHT_RANGES)


def segment_vertical(text: str) -> tuple[tuple[str, str], ...]:
    """Split into ('upright', one character) and ('sideways', maximal run) segments, in reading order."""
    result: list[tuple[str, str]] = []
    for character in text:
        if is_upright(character):
            result.append(("upright", character))
        elif result and result[-1][0] == "sideways":
            result[-1] = ("sideways", result[-1][1] + character)
        else:
            result.append(("sideways", character))
    return tuple(result)


@dataclass(frozen=True)
class VerticalLabel:
    """The placements of one vertical label and what it needed against what it had (#981)."""

    placements: tuple[TextPlacement, ...]
    required_block: float   # the natural extent of the whole label
    available_block: float  # the room between the two clear-space insets


def place_vertical_label(**kwargs: Any) -> tuple[TextPlacement, ...]:
    """Place `label` as one column centred in `column_size`, from `block_start`, cut to `available_block`."""
    return place_vertical_label_fit(**kwargs).placements


def place_vertical_label_fit(*, label: str, placement_prefix: str, source_ref: str, column_inline: float,
                             column_size: float, block_start: float, available_block: float, typography_role: str,
                             theme_tokens: Any, font_metrics: Any, collision_region: str,
                             collision_domain: CollisionDomain, semantic_id: str,
                             align: str = "start") -> VerticalLabel:
    """Place `label` as one column; `align` (start, center or end) sets where a label shorter than its room stands."""
    treatment = theme_tokens.text_treatment(typography_role)
    metric = metric_for_role(theme_tokens, typography_role, font_metrics)
    size, spacing = float(treatment.font_size), float(treatment.letter_spacing)
    line_box = size * float(treatment.line_height)
    painted = paint_text(label, text_transform=treatment.transform)
    # The centre of the em box above the baseline, from the face's own ascent and descent.
    centre_above_baseline = (metric.ascent + metric.descent) / 2 / metric.units_per_em * size

    def advance(segment: tuple[str, str]) -> float:
        if segment[0] == "upright":
            return size
        return measure_text_width(segment[1], font_size=size, font_metrics=metric, letter_spacing=spacing,
                                  numeric_spacing=treatment.numeric_spacing)

    def extent(segments: tuple[tuple[str, str], ...]) -> float:
        return geometry_sum(advance(item) for item in segments) + spacing * max(0, len(segments) - 1)

    # Half an em of clear space at each end keeps the tags of neighbouring groups apart.
    inset = size / 2
    block_start, available_block = block_start + inset, available_block - 2 * inset
    segments = segment_vertical(painted)
    overflow = "fit"
    required = extent(segments)
    if required <= available_block and align != "start":
        # A label that fits stands at the start, middle or end of the room the clear space leaves (#981).
        block_start += (available_block - required) / (2 if align == "center" else 1)
    if required > available_block:
        marker = segment_vertical("…")
        prefix = painted
        while prefix and extent(segment_vertical(prefix) + marker) > available_block:
            prefix = prefix[:-1]
        if extent(marker) > available_block:
            overflow = "visible-overflow"  # not even the marker fits: show the whole label and say so
        else:
            segments, overflow = segment_vertical(prefix) + marker, "ellipsized"
    centre = column_inline + column_size / 2
    placements: list[TextPlacement] = []
    cursor = block_start
    for index, (kind, content) in enumerate(segments):
        common = dict(placement_id=f"{placement_prefix}:{index}", source_ref=source_ref, content=content,
                      typography_role=typography_role, theme_tokens=theme_tokens, font_metrics=font_metrics,
                      overflow=overflow, collision_region=collision_region, collision_domain=collision_domain,
                      semantic_id=semantic_id, available_inline_start=column_inline,
                      available_inline_size=column_size, source_content=label if overflow == "ellipsized" else None)
        step = advance((kind, content))
        if kind == "upright":
            width = measure_text_width(content, font_size=size, font_metrics=metric, letter_spacing=0,
                                       numeric_spacing=treatment.numeric_spacing)
            placed = place_text(inline=centre - width / 2, baseline_block=cursor + size / 2 + centre_above_baseline,
                                **common)
            bounds = Rect(Decimal(str(centre - width / 2)), Decimal(str(cursor)), Decimal(str(width)),
                          Decimal(str(size)))
        else:
            # Quarter turn clockwise: the baseline runs down, the tops of the letters point right.
            placed = place_text(inline=centre - centre_above_baseline, baseline_block=cursor,
                                orientation="rotate-cw", **common)
            bounds = Rect(Decimal(str(centre - line_box / 2)), Decimal(str(cursor)), Decimal(str(line_box)),
                          Decimal(str(step)))
        placements.append(replace(placed, bounds=bounds))
        cursor += step + spacing
    return VerticalLabel(tuple(placements), required, available_block)
