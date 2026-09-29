from datetime import date
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_geometry import (
    bounds_from_rect, coordinate_for_date, rect_from_bounds,
)
from chrona.presentation.layout.surface_quality import ScalePlacement


def test_rect_conversions_preserve_decimal_string_geometry():
    bounds = (0.1, 2.25, 30.5, 4.75)
    rect = rect_from_bounds(bounds)
    assert rect == Rect(Decimal("0.1"), Decimal("2.25"), Decimal("30.5"), Decimal("4.75"))
    assert bounds_from_rect(rect) == bounds


def test_date_coordinate_uses_completed_scale_origin_and_unit_ratio():
    scale = ScalePlacement("timeline", "primary", date(2026, 1, 1), date(2026, 1, 11),
                           4.0, 14.0, 4.0, 1.0)
    assert coordinate_for_date(date(2026, 1, 4), scale) == 7.0
