from decimal import Decimal

import pytest

from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.layout.surface_annotations import (
    _container_radius, _physical_radius_clearance, _radius_aware_box_port,
)
from chrona.presentation.layout.surface_axis import _band_cell, _cell_corner


class _AxisTokens:
    def __init__(self, *, ratio=None, chamfer=None, physical=None):
        self.ratio, self.chamfer, self.physical = ratio, chamfer, physical

    def optional_number(self, _role, prop):
        return {"cellCornerRadius": self.ratio, "cellCornerChamfer": self.chamfer}[prop]

    def optional_token(self, _role, prop, _kind):
        assert prop == "cornerRadius"
        return self.physical


def test_physical_radius_is_pixel_bounded_and_capsule_tracks_the_short_side():
    assert resolve_corner_radius(12, width=80, height=20, legacy_radius=3) == 10
    assert resolve_corner_radius("capsule", width=80, height=20, legacy_radius=3) == 10
    assert resolve_corner_radius(None, width=80, height=20, legacy_radius=3) == 3


def test_annotation_physical_radius_overrides_em_and_leader_stays_on_straight_edge():
    class Container:
        corner_radius = Decimal("0.4")

    assert _container_radius(8, Container(), 20, 80, 24) == 8
    assert _container_radius("capsule", Container(), 20, 80, 24) == 12
    box = LabelRect(0, 0, 80, 24)
    assert _radius_aware_box_port(box, (2, 0), 8) == (8, 0)
    assert _radius_aware_box_port(box, (40, 0), 8) == (40, 0)


def test_capsule_clearance_solves_the_final_short_side_after_insets():
    insets = (2.0, 1.0, 4.0, 3.0)
    clearance = _physical_radius_clearance("capsule", 80, 20, insets)
    width = 80 + max(insets[3], clearance) - insets[3] + max(insets[1], clearance) - insets[1]
    height = 20 + max(insets[0], clearance) - insets[0] + max(insets[2], clearance) - insets[2]
    assert clearance == pytest.approx((1 - 1 / 2**0.5) * min(width, height) / 2)
    assert _physical_radius_clearance(7, 80, 20, insets) == pytest.approx(7 * (1 - 1 / 2**0.5))


def test_axis_physical_radius_clamps_to_cell_and_keeps_reduction_diagnostic():
    corner = _cell_corner(_AxisTokens(physical=18), "axis-band", 0)
    assert corner == ("radius", None, 18)
    diagnostics = []
    cell = _band_cell("cell", 0, 20, Decimal(0), Decimal(24), semantic_id="axisBand",
                      paint_order=1, corner=corner, diagnostics=diagnostics)
    assert cell.corner_radius == 10
    assert diagnostics == ["W_LAYOUT_AXIS_CELL_CORNER_REDUCED:cell"]


def test_axis_physical_radius_overrides_ratio_but_conflicts_with_chamfer():
    assert _cell_corner(_AxisTokens(ratio=Decimal("0.2"), physical=5), "axis-band", 1) == (
        "radius", None, 5)
    with pytest.raises(LayoutError, match="E_PRESENTATION_AXIS_INVALID: cell-corner-both:1"):
        _cell_corner(_AxisTokens(chamfer=Decimal("0.2"), physical=5), "axis-band", 1)
