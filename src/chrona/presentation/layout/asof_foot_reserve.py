"""The block extent reserved under the plot for an as-of chip placed `below-plot` (#1063).

The chip is one line of the `asOfLabel` role (typography role `text`) with its optional chip padding; the gap is the one
the label placer uses between a label and its neighbours. Layout reads this one value both for the content-sized
timeline extent and for row placement, so the legend and footer move by exactly the reserved size.
"""
from __future__ import annotations

from typing import Any

from chrona.presentation.layout.chip_geometry import chip_padding
from chrona.presentation.model.semantic_registry import label_chip_semantic

AS_OF_LABEL_ROLE = "as-of-label"
BELOW_PLOT = "below-plot"
BELOW_PLOT_FALLBACK = "W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK"


def as_of_label_typography_role(theme_tokens: Any) -> str:
    """The text role that measures and sets the as-of label: `as-of-label` when the Theme gives it a size (#1110), else `text`."""
    return AS_OF_LABEL_ROLE if theme_tokens.declares_text_treatment(AS_OF_LABEL_ROLE) else "text"


def as_of_label_gap(theme_tokens: Any) -> float:
    """The gap between the plot and the chip: a quarter of the label font size, at least one unit."""
    return max(1.0, float(theme_tokens.text_treatment(as_of_label_typography_role(theme_tokens)).font_size) * 0.25)


def as_of_chip_block_size(theme_tokens: Any) -> float:
    """The chip's block size: one text line plus the chip padding on both sides."""
    treatment = theme_tokens.text_treatment(as_of_label_typography_role(theme_tokens))
    font_size = float(treatment.font_size)
    text_block = font_size * float(treatment.line_height)
    return text_block + 2 * chip_padding(theme_tokens, label_chip_semantic("asOfLabel"), font_size, text_block)[1]


def below_plot_reserve(theme_tokens: Any) -> float:
    """The block extent under the last row: the gap, then the chip."""
    return as_of_label_gap(theme_tokens) + as_of_chip_block_size(theme_tokens)
