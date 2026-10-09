"""The block extent reserved under the plot for an as-of chip placed `below-plot` (#1063).

The chip is one line of the `asOfLabel` role (typography role `text`) with its optional chip padding; the gap is the one
the label placer uses between a label and its neighbours. Layout reads this one value both for the content-sized
timeline extent and for row placement, so the legend and footer move by exactly the reserved size.
"""
from __future__ import annotations

from typing import Any

from chrona.presentation.layout.chip_geometry import chip_padding
from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip, measure_label_chip
from chrona.presentation.layout.label_visual_measurement import resolve_label_visual_advances
from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.text import measure_text_width, metric_for_role
from chrona.presentation.model.semantic_registry import label_chip_semantic
from chrona.presentation.model.theme_tokens import RectangleChipShape

AS_OF_LABEL_ROLE = "as-of-label"
BELOW_PLOT = "below-plot"
BELOW_PLOT_FALLBACK = "W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK"


def as_of_label_typography_role(theme_tokens: Any) -> str:
    """The text role that measures and sets the as-of label: `as-of-label` when the Theme gives it a size (#1110), else `text`."""
    return AS_OF_LABEL_ROLE if theme_tokens.declares_text_treatment(AS_OF_LABEL_ROLE) else "text"


def as_of_label_gap(theme_tokens: Any) -> float:
    """The gap between the plot and the chip: a quarter of the label font size, at least one unit."""
    return max(1.0, float(theme_tokens.text_treatment(as_of_label_typography_role(theme_tokens)).font_size) * 0.25)


def measure_as_of_chip(content: Any, *, window: tuple[Any, Any], theme_tokens: Any,
                       font_metrics: Any, visual_requests: tuple[Any, ...] = (),
                       icon_assets: dict[str, Any] | None = None) -> MeasuredLabelChip | None:
    """Close actual nonrect label geometry before content-sized allocation.

    The use case supplies normalized content/closed resources, not geometry.
    Rectangle chips retain their existing arithmetic and reservation path.
    """
    if (content.as_of is None or not content.as_of_label
            or not window[0] <= content.as_of < window[1]
            or theme_tokens.label_chip("as-of-label-chip") is None
            or isinstance(theme_tokens.label_chip_shape("as-of-label-chip"), RectangleChipShape)):
        return None
    role = as_of_label_typography_role(theme_tokens)
    treatment = theme_tokens.text_treatment(role)
    metrics = metric_for_role(theme_tokens, role, font_metrics)
    visuals = resolve_label_visual_advances("as-of-label", role, visual_requests=visual_requests,
        icon_assets=icon_assets or {}, theme_tokens=theme_tokens)
    leading = geometry_sum(width + gap for visual, _, width, gap in visuals if visual.side == "leading")
    trailing = geometry_sum(width + gap for visual, _, width, gap in visuals if visual.side == "trailing")
    text_width = measure_text_width(content.as_of_label, font_size=float(treatment.font_size),
        font_metrics=metrics, letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
        numeric_spacing=treatment.numeric_spacing)
    text_block = float(treatment.font_size) * float(treatment.line_height)
    padding = chip_padding(theme_tokens, label_chip_semantic("asOfLabel"), float(treatment.font_size), text_block)
    return measure_label_chip(theme_tokens, "asOfLabel", text_inline=leading + text_width + trailing,
                              text_block=text_block, font_size=float(treatment.font_size), padding=padding)


def as_of_chip_block_size(theme_tokens: Any, *, chip_measurement: MeasuredLabelChip | None = None) -> float:
    """The chip's block size: one text line plus the chip padding on both sides."""
    if chip_measurement is not None:
        return float(chip_measurement.footprint.block_size)
    treatment = theme_tokens.text_treatment(as_of_label_typography_role(theme_tokens))
    font_size = float(treatment.font_size)
    text_block = font_size * float(treatment.line_height)
    return text_block + 2 * chip_padding(theme_tokens, label_chip_semantic("asOfLabel"), font_size, text_block)[1]


def below_plot_reserve(theme_tokens: Any, *, chip_measurement: MeasuredLabelChip | None = None) -> float:
    """The block extent under the last row: the gap, then the chip."""
    return as_of_label_gap(theme_tokens) + as_of_chip_block_size(theme_tokens, chip_measurement=chip_measurement)
