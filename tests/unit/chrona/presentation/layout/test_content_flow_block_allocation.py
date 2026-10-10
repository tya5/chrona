"""#1219: a content-sized Flow is allocated the line stack it wraps into at its actual inline width."""

from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import solve_layout
from tests.unit.chrona.presentation.layout.test_cross_size_stretch import container, measurement, resolved, slot


def _solve(*, kind="column", viewport=100, block="content", flow_inline="fill"):
    flow = container("flow", [slot("a", inline={"fixed": 60}, block={"fixed": 20}),
                              slot("b", inline={"fixed": 60}, block={"fixed": 40})],
                     inline=flow_inline, block=block, itemMinInlineSize=1)
    flow["id"] = "foot"
    measures = {"a": measurement(preferred_inline=60, preferred_block=20),
                "b": measurement(preferred_inline=60, preferred_block=40),
                "top": measurement(preferred_inline=10, preferred_block=10)}
    root = container(kind, [slot("top", inline={"fixed": 10}, block={"fixed": 10}), flow], block="fill")
    manifest = solve_layout(resolved(root, measures), viewport_inline=viewport, viewport_block=300, measurements=measures)
    nodes = {item.node_id: item.bounds for item in manifest.decisions}
    return nodes, [(item.placement_id, item.required_block, item.available_block) for item in manifest.fit_warnings]


def test_a_known_inline_width_that_wraps_two_lines_allocates_both_lines_without_a_track_overflow():
    nodes, warnings = _solve(viewport=100)

    assert nodes["foot"].block_size == Decimal(60)  # 20 + 40, one line each
    assert (nodes["a"].block, nodes["b"].block) == (nodes["foot"].block, nodes["foot"].block + 20)
    assert warnings == []


def test_one_line_keeps_the_tallest_child():
    nodes, warnings = _solve(viewport=130)

    assert nodes["foot"].block_size == Decimal(40)
    assert nodes["a"].block == nodes["b"].block and warnings == []


def test_a_fixed_host_that_is_genuinely_too_small_keeps_its_honest_overflow():
    nodes, warnings = _solve(viewport=100, block={"fixed": 40})

    assert nodes["foot"].block_size == Decimal(40)
    assert [item[0] for item in warnings] == ["foot"] and warnings[0][1] > warnings[0][2]


def test_a_fit_content_flow_is_never_allocated_below_its_wrapped_line_stack():
    nodes, warnings = _solve(viewport=100, block={"fitContent": 45})

    assert nodes["foot"].block_size == Decimal(60) and warnings == []


def test_a_flow_in_a_row_takes_its_line_stack_at_the_inline_size_the_row_allocated():
    nodes, warnings = _solve(kind="row", viewport=100, flow_inline={"fixed": 80})

    assert nodes["foot"].inline_size == Decimal(80) and nodes["foot"].block_size == Decimal(60)
    assert warnings == []
