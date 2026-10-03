"""The block extent reserved under the plot for an as-of chip placed `below-plot` (#1063).

The chip is one line of the `asOfLabel` role (typography role `text`) with its optional chip padding; the gap is the one
the label placer uses between a label and its neighbours. Layout reads this one value both for the content-sized
timeline extent and for row placement, so the legend and footer move by exactly the reserved size.
"""
from __future__ import annotations

from typing import Any

from chrona.presentation.model.semantic_registry import label_chip_semantic, semantic_binding

AS_OF_LABEL_TYPOGRAPHY_ROLE = "text"
BELOW_PLOT = "below-plot"
BELOW_PLOT_FALLBACK = "W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK"


def as_of_label_gap(theme_tokens: Any) -> float:
    """The gap between the plot and the chip: a quarter of the label font size, at least one unit."""
    return max(1.0, float(theme_tokens.text_treatment(AS_OF_LABEL_TYPOGRAPHY_ROLE).font_size) * 0.25)


def as_of_chip_block_size(theme_tokens: Any) -> float:
    """The chip's block size: one text line plus the chip padding on both sides."""
    treatment = theme_tokens.text_treatment(AS_OF_LABEL_TYPOGRAPHY_ROLE)
    font_size = float(treatment.font_size)
    chip = theme_tokens.label_chip(semantic_binding(label_chip_semantic("asOfLabel") or "").theme_role)
    padding = float(chip[0]) * font_size / 2 if chip is not None else 0.0
    return font_size * float(treatment.line_height) + 2 * padding


def below_plot_reserve(theme_tokens: Any) -> float:
    """The block extent under the last row: the gap, then the chip."""
    return as_of_label_gap(theme_tokens) + as_of_chip_block_size(theme_tokens)
