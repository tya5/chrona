"""Owns scalar Rect/date-to-scale geometry conversions; reads completed Layout values only."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import ScalePlacement


def rect_from_bounds(bounds: tuple[float, float, float, float]) -> Rect:
    """Convert presentation bounds to the canonical Decimal-backed Rect."""
    return Rect(*(Decimal(str(value)) for value in bounds))


def bounds_from_rect(rect: Rect) -> tuple[float, float, float, float]:
    """Expose a completed Rect as scalar presentation bounds."""
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))


def coordinate_for_date(value: date, scale: ScalePlacement) -> float:
    """Map a date through an already completed temporal scale."""
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio
