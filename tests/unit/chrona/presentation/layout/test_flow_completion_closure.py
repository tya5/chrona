"""#1219: wrappers complete Flow at the actual finite inline extent they allocate."""

from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import (
    LayoutSizingContext,
    SourceInlineBudget,
    measure_natural_normal_flow_block,
    solve_layout,
)
from chrona.presentation.layout.model import LayoutError
from tests.unit.chrona.presentation.layout.test_cross_size_stretch import (
    container,
    decisions,
    measurement,
    resolved,
    slot,
)


def _flow(*, inline="fill", block="content", children=None, gap=0, padding=None):
    node = container(
        "flow",
        children or [
            slot("first", inline={"fixed": 50}, block={"fixed": 20}),
            slot("second", inline={"fixed": 50}, block={"fixed": 40}),
        ],
        inline=inline,
        block=block,
        gap=gap,
        itemMinInlineSize=1,
    )
    node["id"] = "flow"
    if padding is not None:
        node["padding"] = padding
    return node


def _profile_for(root, measures):
    return resolved(root, measures)


def _bounds(manifest):
    return decisions(manifest)


def test_two_column_wrappers_complete_the_nested_flow_line_stack_with_gaps_and_padding():
    flow = _flow(inline="fill", gap=5,
                 padding={"inlineStart": 3, "inlineEnd": 3,
                          "blockStart": 3, "blockEnd": 3})
    inner = container("column", [flow], inline="fill", block="content", gap=7, padding=0)
    inner["id"] = "inner"
    outer = container("column", [inner], inline={"fixed": 100}, block="content", padding=0)
    outer["id"] = "outer"
    root = container("column", [outer], inline="fill", block="content", padding=0)
    measures = {
        "first": measurement(preferred_inline=50, preferred_block=20),
        "second": measurement(preferred_inline=50, preferred_block=40),
    }
    profile = _profile_for(root, measures)

    natural = measure_natural_normal_flow_block(profile, viewport_inline=160,
                                                measurements=measures)
    placed = _bounds(solve_layout(profile, viewport_inline=160, viewport_block=200,
                                  measurements=measures))

    # Flow inner width is 94 (100 minus its horizontal padding); its two
    # 50-unit items wrap, with 5 between lines and 6 total vertical padding.
    assert placed["flow"].inline_size == Decimal(100)
    assert placed["flow"].block_size == Decimal(71)
    assert placed["second"].block == Decimal(28)
    assert natural == placed["outer"].block_size == Decimal(71)


@pytest.mark.parametrize("wrapper", ["row", "overlay", "grid"])
def test_noncolumn_wrappers_preserve_a_narrow_fixed_flow_width_and_its_stack(wrapper):
    flow = _flow(inline={"fixed": 90})
    if wrapper == "row":
        parent = container("row", [flow], inline="fill", block="content", padding=0)
    elif wrapper == "overlay":
        flow["place"] = {"inline": "start", "block": "start", "safety": "strict"}
        parent = container("overlay", [flow], inline="fill", block="content", padding=0)
    else:
        flow["cell"] = {"column": 1, "row": 1}
        parent = container("grid", [flow], inline="fill", block="content", padding=0,
                           columnTracks=[{"fixed": 90}, "fill"], rowTracks=["content"])
    parent["id"] = "wrapper"
    root = container("column", [parent], inline={"fixed": 180}, block="content", padding=0)
    root["id"] = "root"
    measures = {
        "first": measurement(preferred_inline=20, preferred_block=20),
        "second": measurement(preferred_inline=20, preferred_block=40),
    }
    profile = _profile_for(root, measures)

    placed = _bounds(solve_layout(profile, viewport_inline=220, viewport_block=200,
                                  measurements=measures, content_sized=True))

    assert placed["root"].inline_size == Decimal(220)
    assert placed["flow"].inline_size == Decimal(90)
    assert placed["flow"].block_size == Decimal(60)
    assert placed["second"].block == placed["first"].block + Decimal(20)


def test_flow_fixed_inline_extent_controls_wrapping_instead_of_measured_composite_width():
    flow = _flow(inline={"fixed": 90})
    root = container("column", [flow], inline="fill", block="content", padding=0)
    measures = {
        "first": measurement(preferred_inline=20, preferred_block=20),
        "second": measurement(preferred_inline=20, preferred_block=40),
    }
    profile = _profile_for(root, measures)

    natural = measure_natural_normal_flow_block(profile, viewport_inline=180,
                                                measurements=measures)
    placed = _bounds(solve_layout(profile, viewport_inline=180, viewport_block=100,
                                  measurements=measures))

    assert natural == Decimal(60)
    assert placed["flow"].inline_size == Decimal(90)
    assert placed["second"].block == Decimal(20)


@pytest.mark.parametrize(
    ("inline_spec", "expected"),
    [
        ({"fixed": 90}, 90),
        ("min-content", 10),
        ("max-content", 80),
        ({"fitContent": 30}, 30),
        ({"minmax": {"min": {"fixed": 15}, "max": {"fixed": 60}}}, 60),
        ({"aspectRatio": 2}, 20),
        ("fill", 40),
        ({"fr": 2}, 40),
    ],
)
def test_flow_item_uses_its_declared_intrinsic_or_bounded_inline_target(inline_spec, expected):
    child = slot("item", inline=inline_spec, block={"fixed": 10})
    flow = _flow(inline={"fixed": 200}, children=[child])
    measures = {"item": measurement(min_inline=10, preferred_inline=40, max_inline=80,
                                     preferred_block=10)}
    profile = _profile_for(flow, measures)

    placed = _bounds(solve_layout(profile, viewport_inline=220, viewport_block=50,
                                  measurements=measures))

    assert placed["item"].inline_size == Decimal(expected)


@pytest.mark.parametrize(
    "inline_spec",
    [
        {"fixed": 10},
        {"minmax": {"min": {"fixed": 0}, "max": {"fixed": 10}}},
    ],
)
def test_item_minimum_cannot_override_a_fixed_target_or_fixed_minmax_ceiling(inline_spec):
    child = slot("item", inline=inline_spec, block={"fixed": 10})
    flow = _flow(inline={"fixed": 100}, children=[child])
    flow["itemMinInlineSize"] = 20
    profile = _profile_for(flow, {"item": measurement(preferred_block=10)})

    with pytest.raises(LayoutError) as caught:
        solve_layout(profile, viewport_inline=100, viewport_block=40,
                     measurements={"item": measurement(preferred_block=10)})

    assert caught.value.diagnostic_id == "E_LAYOUT_CONSTRAINT_CONTRADICTORY"
    assert caught.value.path == "/root/children/0/inlineSize"
    assert caught.value.node_id == "item"


def test_source_budget_floor_failure_keeps_its_typed_overflow_diagnostic():
    child = slot("table", inline={"fixed": 30}, block={"fixed": 10})
    flow = _flow(inline={"fixed": 100}, children=[child])
    flow["itemMinInlineSize"] = 20
    profile = _profile_for(flow, {"table": measurement(preferred_inline=30,
                                                         preferred_block=10)})
    budget = SourceInlineBudget("table", "/root/children/0", Decimal(100), Decimal(10))

    with pytest.raises(LayoutError) as caught:
        solve_layout(profile, viewport_inline=100, viewport_block=40,
                     measurements={"table": measurement(preferred_inline=30,
                                                          preferred_block=10)},
                     sizing=LayoutSizingContext({"table": budget}))

    assert caught.value.diagnostic_id == "E_LAYOUT_TABLE_OVERFLOW"


@pytest.mark.parametrize("host", [
    {"fixed": 40},
    {"minmax": {"min": {"fixed": 20}, "max": {"fixed": 45}}},
])
def test_fixed_or_capped_flow_host_keeps_capacity_and_reports_real_line_stack_overflow(host):
    flow = _flow(inline={"fixed": 90}, block=host)
    root = container("column", [flow], inline={"fixed": 100}, block={"fixed": 100}, padding=0)
    measures = {
        "first": measurement(preferred_inline=20, preferred_block=20),
        "second": measurement(preferred_inline=20, preferred_block=40),
    }
    profile = _profile_for(root, measures)

    placed_manifest = solve_layout(profile, viewport_inline=100, viewport_block=100,
                                   measurements=measures)
    placed = _bounds(placed_manifest)

    assert placed["flow"].block_size == Decimal(40 if host == {"fixed": 40} else 45)
    assert any(warning.placement_id == "flow"
               and warning.required_block >= Decimal(60)
               and warning.available_block == placed["flow"].block_size
               for warning in placed_manifest.fit_warnings)
