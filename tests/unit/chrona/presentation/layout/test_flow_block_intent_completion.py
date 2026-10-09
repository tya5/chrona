"""#1170: flow line measurement and arrangement complete each child's block-size intent."""

from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import _flow_lines, measure_natural_normal_flow_block, solve_layout
from tests.unit.chrona.presentation.layout.test_cross_size_stretch import (
    container,
    decisions,
    measurement,
    resolved,
    slot,
)


def _profile_and_measures(root, measures):
    return resolved(root, measures)


@pytest.mark.parametrize("alignment", ["start", "stretch"])
def test_flow_fixed_block_size_is_used_when_preferred_measurement_differs(alignment):
    measures = {"fixed": measurement(preferred_block=30)}
    root = container(
        "flow",
        [slot("fixed", block={"fixed": 50}, place={"block": alignment})],
        block="content",
        itemMinInlineSize=1,
    )
    profile = _profile_and_measures(root, measures)

    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=100, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)

    assert natural == Decimal(50)
    assert decisions(manifest)["fixed"].block_size == Decimal(50)


def test_content_parent_grows_for_fixed_child_but_fixed_parent_keeps_its_capacity():
    measures = {"fixed": measurement(preferred_block=30)}
    child = slot("fixed", block={"fixed": 50})
    content_profile = _profile_and_measures(
        container("flow", [child], block="content", itemMinInlineSize=1), measures
    )
    fixed_profile = _profile_and_measures(
        container("flow", [child], block={"fixed": 120}, itemMinInlineSize=1), measures
    )

    assert measure_natural_normal_flow_block(
        content_profile, viewport_inline=100, measurements=measures
    ) == Decimal(50)
    assert measure_natural_normal_flow_block(
        fixed_profile, viewport_inline=100, measurements=measures
    ) == Decimal(120)
    fixed_manifest = solve_layout(
        fixed_profile, viewport_inline=100, viewport_block=120, measurements=measures
    )
    assert decisions(fixed_manifest)["root"].block_size == Decimal(120)
    assert decisions(fixed_manifest)["fixed"].block_size == Decimal(50)


def test_wrapped_fixed_children_share_line_height_between_natural_measurement_and_arrangement():
    measures = {
        "first": measurement(preferred_inline=60, preferred_block=15),
        "second": measurement(preferred_inline=60, preferred_block=35),
        "third": measurement(preferred_inline=30, preferred_block=20),
    }
    children = [
        slot("first", block={"fixed": 40}, place={"block": "start"}),
        slot("second", block={"fixed": 20}, place={"block": "start"}),
        slot("third", block={"fixed": 30}, place={"block": "start"}),
    ]
    profile = _profile_and_measures(
        container("flow", children, block="content", itemMinInlineSize=1), measures
    )

    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=100, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)
    bounds = decisions(manifest)

    assert natural == Decimal(70)
    assert bounds["first"].block == Decimal(0)
    assert bounds["first"].block_size == Decimal(40)
    assert bounds["second"].block == Decimal(40)
    assert bounds["second"].block_size == Decimal(20)
    assert bounds["third"].block == Decimal(40)
    assert bounds["third"].block_size == Decimal(30)


def test_wrapped_bounded_composite_reserves_its_declared_target_before_next_line():
    bounded = container(
        "column",
        [
            slot("inner-first", inline={"fixed": 20}, block="content"),
            slot("inner-second", inline={"fixed": 20}, block="content"),
        ],
        inline={"fixed": 20},
        block={"minmax": {"min": {"fixed": 90}, "max": {"fixed": 100}}},
    )
    bounded["id"] = "bounded"
    measures = {
        "inner-first": measurement(preferred_inline=20, preferred_block=30),
        "inner-second": measurement(preferred_inline=20, preferred_block=40),
        "peer": measurement(preferred_inline=20, preferred_block=15),
    }
    root = container(
        "flow", [bounded, slot("peer", inline={"fixed": 20}, block="content")],
        block="content", itemMinInlineSize=1,
    )
    profile = _profile_and_measures(root, measures)

    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=20, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=20, viewport_block=120, measurements=measures)
    bounds = decisions(manifest)

    assert natural == Decimal(115)
    assert bounds["bounded"].block_size == Decimal(100)
    assert bounds["peer"].block == Decimal(100)
    assert bounds["peer"].block_size == Decimal(15)


def test_flexible_flow_children_stretch_to_fixed_sibling_line_height():
    measures = {
        "fixed": measurement(preferred_inline=20, preferred_block=30),
        "fill": measurement(preferred_inline=20, preferred_block=15),
        "fractional": measurement(preferred_inline=20, preferred_block=10),
    }
    root = container(
        "flow",
        [slot("fixed", block={"fixed": 50}), slot("fill"), slot("fractional", block={"fr": 2})],
        block="content",
        itemMinInlineSize=1,
    )
    profile = _profile_and_measures(root, measures)
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)
    bounds = decisions(manifest)

    assert bounds["fixed"].block_size == Decimal(50)
    assert bounds["fill"].block_size == Decimal(50)
    assert bounds["fractional"].block_size == Decimal(50)


def test_flow_flexible_minmax_child_preserves_its_minimum_floor():
    measures = {
        "fixed": measurement(preferred_inline=20, preferred_block=30),
        "flex-floor": measurement(preferred_inline=20, preferred_block=15),
    }
    root = container(
        "flow",
        [
            slot("fixed", block={"fixed": 50}),
            slot("flex-floor", block={"minmax": {"min": {"fixed": 60}, "max": "fill"}}),
        ],
        block="content",
        itemMinInlineSize=1,
    )
    profile = _profile_and_measures(root, measures)
    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=100, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)
    bounds = decisions(manifest)

    assert natural == Decimal(60)
    assert bounds["fixed"].block_size == Decimal(50)
    assert bounds["flex-floor"].block_size == Decimal(60)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("content", 30),
        ("min-content", 10),
        ("max-content", 60),
        ({"fitContent": 15}, 15),
        ({"minmax": {"min": {"fixed": 30}, "max": {"fixed": 50}}}, 50),
    ],
)
def test_flow_completes_intrinsic_and_bounded_block_intents(spec, expected):
    measures = {"child": measurement(min_block=10, preferred_block=30, max_block=60)}
    profile = _profile_and_measures(
        container(
            "flow", [slot("child", block=spec, place={"block": "start"})],
            block="content", itemMinInlineSize=1,
        ),
        measures,
    )

    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=100, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)

    assert natural == Decimal(expected)
    assert decisions(manifest)["child"].block_size == Decimal(expected)


def test_content_sized_flow_child_keeps_width_dependent_natural_height_callback():
    measures = {"child": measurement(preferred_inline=120, preferred_block=30, max_block=60)}
    root = container(
        "flow", [slot("child", block="content")],
        block="content", itemMinInlineSize=1,
    )
    profile = _profile_and_measures(root, measures)
    resolved_root = profile.profile["root"]

    def line_height(inline_size):
        seen = []

        def height(_child, _path, available_inline):
            seen.append(available_inline)
            return Decimal(60) if available_inline < Decimal(110) else Decimal(40)

        lines = _flow_lines(resolved_root, "/root", measures, profile, Decimal(inline_size), height)
        # The callback gets the extent the child is arranged at, whatever the line bound (#1206, Spec 33 section 13).
        assert seen == [lines[0][0][3]] == [Decimal(120)]
        return lines[0][0][4]

    assert line_height(100) == Decimal(40)
    assert line_height(200) == Decimal(40)


def test_flow_aspect_ratio_keeps_its_existing_block_geometry():
    measures = {"child": measurement(preferred_inline=20, preferred_block=30)}
    profile = _profile_and_measures(
        container(
            "flow", [slot("child", inline={"fixed": 20}, block={"aspectRatio": 2})],
            block="content", itemMinInlineSize=1,
        ),
        measures,
    )

    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=100, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)

    assert natural == Decimal(10)
    assert decisions(manifest)["child"].block_size == Decimal(10)


def test_flow_fixed_block_and_inline_aspect_ratio_derive_the_inline_extent():
    measures = {"child": measurement(preferred_inline=20, preferred_block=30)}
    profile = _profile_and_measures(
        container(
            "flow",
            [slot("child", inline={"aspectRatio": 2}, block={"fixed": 50})],
            block="content",
            itemMinInlineSize=1,
        ),
        measures,
    )

    natural = measure_natural_normal_flow_block(
        profile, viewport_inline=200, measurements=measures
    )
    manifest = solve_layout(profile, viewport_inline=200, viewport_block=100, measurements=measures)
    child = decisions(manifest)["child"]

    assert natural == Decimal(50)
    assert child.block_size == Decimal(50)
    assert child.inline_size == Decimal(100)


def test_fixed_flow_child_shortage_keeps_finite_visible_placement_and_warning():
    measures = {"child": measurement(preferred_block=30)}
    profile = _profile_and_measures(
        container(
            "flow", [slot("child", block={"fixed": 50})],
            block={"fixed": 30}, itemMinInlineSize=1,
        ),
        measures,
    )

    manifest = solve_layout(profile, viewport_inline=100, viewport_block=30, measurements=measures)
    bounds = decisions(manifest)

    assert all(value.block.is_finite() and value.block_size.is_finite() for value in bounds.values())
    assert bounds["child"].block_size == Decimal(50)
    assert any(
        warning.code == "W_LAYOUT_VISIBLE_OVERFLOW"
        and warning.placement_id == "root"
        and warning.required_block > warning.available_block
        for warning in manifest.fit_warnings
    )
