"""Owns scalar Rect/date-to-scale geometry conversions; reads completed Layout values only."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import ScalePlacement

GEOMETRY_TOLERANCE = Decimal("0.000001")
BACKGROUND_PAINT_ORDER = 10
HOSTED_TEXT_PAINT_ORDER = 200


def rect_from_bounds(bounds: tuple[float, float, float, float]) -> Rect:
    """Convert presentation bounds to the canonical Decimal-backed Rect."""
    return Rect(*(Decimal(str(value)) for value in bounds))


def bounds_from_rect(rect: Rect) -> tuple[float, float, float, float]:
    """Expose a completed Rect as scalar presentation bounds."""
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))


def plot_rect(timeline: Rect, rows: Iterable[Rect]) -> Rect:
    """The plot: the timeline slot down to the bottom of its last row, never past the slot (#880).

    A slot is an allocation and the rows are the content, so a surface given more block room than its rows need
    has an empty strip under the last row. The ground (group and row bands) stops at the last row; every overlay
    that runs the height of the plot (gridlines, closed days, the as-of line, a period band) ends there too.
    With no rows the plot is the slot.
    """
    bottoms = [row.block + row.block_size for row in rows]
    if not bottoms:
        return timeline
    slot_bottom = timeline.block + timeline.block_size
    bottom = min(max(bottoms), slot_bottom)
    return Rect(timeline.inline, timeline.block, timeline.inline_size, max(Decimal(0), bottom - timeline.block))


def extend_to_plot_edges(left: float, right: float, *, scale: ScalePlacement, plot: Rect) -> tuple[float, float]:
    """Let a cell whose edge is the window edge reach the plot edge (#880).

    The scale is inset by what point marks protrude (#501), so the window maps to a range narrower than the plot and
    leaves a margin at each end that still belongs to the plot (the axis rule and the row bands cover it, and a mark
    sits in it). A band cell, a closed-day cell or a period band that starts or ends at the window edge reaches the
    plot edge, so band, ground and rule end at the same place. Only that one edge moves, and only when the scale is
    inset: positions inside the window are unchanged, and a scale that fills the plot returns its input.
    """
    tolerance = float(GEOMETRY_TOLERANCE)
    if left <= scale.range_start + tolerance:
        left = min(left, float(plot.inline))
    if right >= scale.range_end - tolerance:
        right = max(right, float(plot.inline + plot.inline_size))
    return left, right


def coordinate_for_date(value: date, scale: ScalePlacement) -> float:
    """Map a date through an already completed temporal scale."""
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio
