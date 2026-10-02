"""Owns named-period band geometry and label requests; reads the View-selected periods, the completed scale and the Theme treatment (#582)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.surface_quality import CollisionDomain, ShapePlacement
from chrona.presentation.model.projection import ReviewPeriod
from chrona.presentation.model.semantic_registry import semantic_binding

# Label placement to the shared label engine's side, about an anchor on the plot edge or the band itself.
_LABEL_SIDE = {"top": "below", "bottom": "above", "inside": "inside"}


@dataclass(frozen=True)
class PeriodBandBatch:
    """Completed band shapes in selection order, the extent of every period that has one, and the diagnostics.

    ``extents`` holds one ``(period, inline start, inline end)`` per period with a drawable extent, whether or
    not the Theme paints a band for it: a label belongs to the extent, not to the paint.
    """

    shapes: tuple[ShapePlacement, ...]
    diagnostics: tuple[str, ...]
    extents: tuple[tuple[ReviewPeriod, float, float], ...] = ()


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
    plot = base.plot
    plot_left, plot_right = float(plot.inline), float(plot.inline + plot.inline_size)
    shapes: list[ShapePlacement] = []
    extents: list[tuple[ReviewPeriod, float, float]] = []
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
        extents.append((period, left, right))
        if treatment == "none":
            continue
        shapes.append(ShapePlacement(
            f"period-band:{period.period_id}", period.period_id, "Rect",
            Rect(Decimal(str(left)), plot.block, Decimal(str(right - left)), plot.block_size),
            slot_id="timeline", paint_order=paint_order, semantic_id="periodBand"))
    return PeriodBandBatch(tuple(shapes), tuple(diagnostics), tuple(extents))


def period_label_requests(extents: tuple[tuple[ReviewPeriod, float, float], ...],
                          plot: tuple[float, float, float, float]) -> tuple[LabelRequest, ...]:
    """One label request per labelled period, for the shared label engine.

    ``top`` and ``bottom`` anchor a zero-height strip on the plot edge so the engine's ``below`` and ``above``
    geometry centres the label on the band against that edge; ``inside`` anchors the band itself. The engine
    owns the obstacle search, the chip, and the suppression and overflow records.
    """
    left, top, width, height = plot
    requests = []
    for period, band_left, band_right in extents:
        if period.label_placement is None:
            continue
        anchor = LabelRect(band_left, top + (height if period.label_placement == "bottom" else 0.0),
                           band_right - band_left, height if period.label_placement == "inside" else 0.0)
        requests.append(LabelRequest(
            f"period-label:{period.period_id}", period.period_id, period.title, anchor,
            (_LABEL_SIDE[period.label_placement],), "period-label", "period-label",
            CollisionDomain("timeline", "overlay"), period.label_overflow,
            bounds=LabelRect(left, top, width, height), semantic_id="periodLabel"))
    return tuple(requests)
