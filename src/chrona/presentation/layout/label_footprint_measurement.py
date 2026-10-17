"""Measure a complete Layout label footprint before candidate placement."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chrona.presentation.layout.chip_geometry import chip_padding
from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip, measure_label_chip
from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.surface_visuals import measure_candidate_visuals
from chrona.presentation.layout.text import metric_for_role, measure_text_width, wrap_text
from chrona.presentation.model.semantic_registry import label_chip_semantic, semantic_binding
from chrona.presentation.model.theme_tokens import RectangleChipShape


@dataclass(frozen=True)
class LabelFootprintMeasurement:
    """Exact text, visual and chip size used by Layout's label candidate solver."""

    size: tuple[float, float]
    gap: float
    treatment: Any
    metrics: Any
    visuals: tuple[Any, ...]
    leading: float
    trailing: float
    text_width: float
    lines: tuple[str, ...]
    chip_semantic: str
    chip: Any
    chip_padding: tuple[float, float]
    chip_measurement: MeasuredLabelChip | None
    text_insets: tuple[float, float]


def measure_label_footprint(
    placement_id: str,
    content: str,
    typography_role: str,
    semantic_id: str,
    request: Any,
    *,
    wrap: str = "forbid",
    available_inline: float = 1.0,
    lane_measure: Any = None,
    chip_measurement_override: MeasuredLabelChip | None = None,
) -> LabelFootprintMeasurement:
    """Apply the label placer’s exact measurement arithmetic without choosing a rung."""
    treatment = request.theme_tokens.text_treatment(typography_role)
    metrics = metric_for_role(request.theme_tokens, typography_role, request.font_metrics)
    font_size, line_height = treatment.font_size, treatment.line_height
    visuals = (lane_measure.visuals if lane_measure is not None else
               measure_candidate_visuals(placement_id, typography_role, request).visuals)
    leading = geometry_sum(width + gap for visual, _, width, gap in visuals if visual.side == "leading")
    trailing = geometry_sum(width + gap for visual, _, width, gap in visuals if visual.side == "trailing")
    chip_semantic = label_chip_semantic(semantic_id) or ""
    chip_role = semantic_binding(chip_semantic).theme_role if chip_semantic else None
    chip = request.theme_tokens.label_chip(chip_role) if chip_role else None
    nonrect_chip = chip is not None and not isinstance(
        request.theme_tokens.label_chip_shape(chip_role), RectangleChipShape)
    # Legacy rectangular/no-chip paths retain proportional spacing; the newer
    # nonrectangular chip path measures the same declared numeric spacing as Text.
    numeric_spacing = treatment.numeric_spacing if nonrect_chip else "proportional"
    available = max(1.0, available_inline - leading - trailing)
    lines = (lane_measure.lines if lane_measure is not None else
             wrap_text(content, available_inline=available, font_size=float(font_size),
                       font_metrics=metrics, letter_spacing=float(treatment.letter_spacing),
                       text_transform=treatment.transform, numeric_spacing=numeric_spacing)
             if wrap == "allow" else (content,))
    text_width = (lane_measure.text_width if lane_measure is not None else
                  max(measure_text_width(line, font_size=float(font_size), font_metrics=metrics,
                      letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                      numeric_spacing=numeric_spacing) for line in lines))
    text_size = (leading + text_width + trailing,
                 float(font_size) * float(line_height) * len(lines))
    padding = chip_padding(request.theme_tokens, chip_semantic, float(font_size), text_size[1])
    if lane_measure is not None:
        chip_measurement = lane_measure.chip_measurement
    elif chip_measurement_override is not None:
        chip_measurement = chip_measurement_override
    else:
        chip_measurement = measure_label_chip(request.theme_tokens, semantic_id,
            text_inline=text_size[0], text_block=text_size[1], font_size=float(font_size), padding=padding)
    size = (text_size[0] + 2 * padding[0], text_size[1] + 2 * padding[1])
    if lane_measure is not None:
        size, padding = (lane_measure.width, lane_measure.height), lane_measure.chip_padding
    if chip_measurement is not None:
        size = (float(chip_measurement.footprint.inline_size), float(chip_measurement.footprint.block_size))
    text_insets = ((chip_measurement.text_inline_inset, chip_measurement.text_block_inset)
                   if chip_measurement is not None else padding)
    return LabelFootprintMeasurement(
        size=size, gap=(lane_measure.gap if lane_measure is not None
                        else max(1.0, float(font_size) * 0.25)),
        treatment=treatment, metrics=metrics, visuals=visuals, leading=leading, trailing=trailing,
        text_width=text_width, lines=lines, chip_semantic=chip_semantic, chip=chip,
        chip_padding=padding, chip_measurement=chip_measurement, text_insets=text_insets,
    )
