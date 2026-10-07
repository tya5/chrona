"""#1150: the axis block size an unbound Theme derives from the axis lanes."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.axis_lanes import derived_axis_block_size, plan_label_lanes
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import SourceInput, derive_axis_metrics
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE


class Tokens:
    """Just the two token reads the lane rule makes; lanes are `{role: laneBlockSize}`."""

    def __init__(self, lanes):
        self.lanes = lanes

    def optional_number(self, role, name):
        assert name == "laneBlockSize"
        value = self.lanes.get(role)
        return None if value is None else Decimal(value)

    def text_treatment(self, role):
        return SimpleNamespace(font_size=Decimal(10), line_height=Decimal("1.5"))


def labels(unit, orientation="horizontal", role=None):
    return SimpleNamespace(role="labels", unit=unit, typography_role=role,
                           label=SimpleNamespace(orientation=orientation, secondary=None))


def band(unit, role=None):
    return SimpleNamespace(role="band", unit=unit, typography_role=role, label=None)


def test_declared_lanes_stack_and_an_undeclared_lane_is_its_line_height():
    tokens = Tokens({"top": 24, "bottom": 22})
    assert plan_label_lanes([labels("quarter", role="top"), labels("month", role="bottom")], tokens, None).total == 46
    undeclared = plan_label_lanes([labels("quarter", role="top"), labels("month")], tokens, None).total
    assert undeclared == pytest.approx(24 + 15 + float(GEOMETRY_TOLERANCE))


def test_the_axis_is_the_lane_sum_and_one_band_or_grid_adds_no_lane():
    tokens = Tokens({"top": 24, "bottom": 22})
    tiers = [band("quarter"), labels("quarter", role="top"), labels("month", role="bottom"),
             SimpleNamespace(role="grid-major", unit="month", typography_role=None, label=None)]
    assert derived_axis_block_size(tiers, tokens, None) == Decimal(46)


def test_several_bands_without_a_label_lane_stack_their_own_and_the_taller_stack_wins():
    tokens = Tokens({"top": 10})
    tiers = [band("year"), band("quarter"), labels("quarter", role="top")]
    bands = 2 * (15 + float(GEOMETRY_TOLERANCE))  # the year band has no label lane, the quarter one shares its
    assert derived_axis_block_size(tiers, Tokens({"top": 10}), None) == Decimal(str(max(10.0, 15 + float(GEOMETRY_TOLERANCE))))
    assert bands > 10


def test_a_rotated_label_tier_or_no_tier_cannot_be_derived():
    tokens = Tokens({})
    assert derived_axis_block_size([labels("day", orientation="rotate-cw")], tokens, None) is None
    assert derived_axis_block_size([], tokens, None) is None
    assert derived_axis_block_size([band("year")], tokens, None) is None


def test_an_unbound_axis_without_derivable_tiers_stays_a_metric_diagnostic():
    theme = {"body": {"metrics": {}, "values": {}}}
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_REQUIRED"):
        derive_axis_metrics({}, theme, {"timeline-axis": SourceInput()}, Tokens({}), None)
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_REQUIRED"):
        derive_axis_metrics({}, theme, {}, Tokens({}), None)
