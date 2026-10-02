"""Owns named-period band geometry; reads the View-selected periods, the completed scale and the Theme treatment (#582)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.surface_quality import ShapePlacement
from chrona.presentation.model.projection import ReviewPeriod
from chrona.presentation.model.semantic_registry import semantic_binding


@dataclass(frozen=True)
class PeriodBandBatch:
    """Completed band shapes in selection order and the Scene diagnostics for periods that draw nothing."""

    shapes: tuple[ShapePlacement, ...]
    diagnostics: tuple[str, ...]


def compose_period_bands(*, base: SurfaceBaseGeometry, theme_tokens: Any, periods: tuple[ReviewPeriod, ...],
                         window: tuple[Any, Any]) -> PeriodBandBatch:
    """Complete one Rect per drawable selected period across the plot's rows.

    A period is the half-open range ``[start, end)`` clipped to the View window and mapped through the same
    scale that places marks; its block extent is the timeline slot, as the calendar closure's is. A period with
    no extent left after clipping draws nothing and is recorded, never silently dropped. The band is a
    background: it never enters the obstacle index.
    """
    if not periods:
        return PeriodBandBatch((), ())
    treatment, paint_order = theme_tokens.background(semantic_binding("periodBand").scene_role)
    window_start, window_end = window
    plot = base.timeline.bounds
    plot_left, plot_right = float(plot.inline), float(plot.inline + plot.inline_size)
    shapes: list[ShapePlacement] = []
    diagnostics: list[str] = []
    for period in periods:
        start, end = max(period.start, window_start), min(period.end, window_end)
        left = right = 0.0
        if start < end:
            left = max(coordinate_for_date(start, base.scale), plot_left)
            right = min(coordinate_for_date(end, base.scale), plot_right)
        if not left < right:
            diagnostics.append(f"I_LAYOUT_PERIOD_OUTSIDE_WINDOW:{period.period_id}")
            continue
        if treatment == "none":
            continue
        shapes.append(ShapePlacement(
            f"period-band:{period.period_id}", period.period_id, "Rect",
            Rect(Decimal(str(left)), plot.block, Decimal(str(right - left)), plot.block_size),
            slot_id="timeline", paint_order=paint_order, semantic_id="periodBand"))
    return PeriodBandBatch(tuple(shapes), tuple(diagnostics))
