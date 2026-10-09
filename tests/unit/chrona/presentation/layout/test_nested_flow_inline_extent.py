"""#1206: a nested content-sized flow is measured at the inline extent it is arranged at (Spec 33 section 13)."""

from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import measure_natural_normal_flow_block, solve_layout
from tests.unit.chrona.presentation.layout.test_cross_size_stretch import container, measurement, resolved, slot


def _profile(*, first=(60, 20), second=(60, 40), outer_block="content"):
    inner = container("flow", [slot("a", inline={"fixed": first[0]}, block={"fixed": first[1]}),
                               slot("b", inline={"fixed": second[0]}, block={"fixed": second[1]})],
                      inline="content", block="content", itemMinInlineSize=1)
    inner["id"] = "inner"
    measures = {"a": measurement(preferred_inline=first[0], preferred_block=first[1]),
                "b": measurement(preferred_inline=second[0], preferred_block=second[1])}
    return resolved(container("flow", [inner], block=outer_block, itemMinInlineSize=1), measures), measures


def _arranged(profile, measures, viewport):
    decisions = solve_layout(profile, viewport_inline=viewport, viewport_block=200, measurements=measures).decisions
    return {item.node_id: (item.bounds.inline_size, item.bounds.block_size) for item in decisions}


@pytest.mark.parametrize("viewport", [100, 119, 120, 200])
def test_natural_measurement_and_arrangement_agree_on_the_nested_flow_block_extent(viewport):
    profile, measures = _profile()

    natural = measure_natural_normal_flow_block(profile, viewport_inline=viewport, measurements=measures)
    arranged = _arranged(profile, measures, viewport)

    assert natural == arranged["inner"][1] == Decimal(40)
    assert arranged["inner"][0] == Decimal(120)  # the declared natural width is kept, never shrunk


def test_the_inner_flow_keeps_both_children_on_one_line_when_the_bound_is_narrower():
    profile, measures = _profile()

    arranged = _arranged(profile, measures, 100)

    assert arranged["a"][1] == Decimal(20) and arranged["b"][1] == Decimal(40)


def test_a_flat_flow_still_wraps_at_the_bounded_inline_extent():
    flat = container("flow", [slot("a", inline={"fixed": 60}, block={"fixed": 20}),
                              slot("b", inline={"fixed": 60}, block={"fixed": 40})], block="content", itemMinInlineSize=1)
    measures = {"a": measurement(preferred_inline=60, preferred_block=20),
                "b": measurement(preferred_inline=60, preferred_block=40)}
    profile = resolved(flat, measures)

    assert measure_natural_normal_flow_block(profile, viewport_inline=100, measurements=measures) == Decimal(60)
    assert measure_natural_normal_flow_block(profile, viewport_inline=120, measurements=measures) == Decimal(40)
