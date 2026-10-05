"""Cross-axis stretch must respect each child's declared used-size constraints."""

from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import measure_natural_normal_flow_block, solve_layout
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.profile import resolve_layout_profile


ZERO = Decimal(0)
TOKEN_VALUES = {"spacing.none": {"type": "number", "value": 0}}


def measurement(*, min_inline=10, preferred_inline=20, max_inline=40,
                min_block=10, preferred_block=20, max_block=40):
    return Measurement(*(Decimal(value) for value in (
        min_inline, preferred_inline, max_inline,
        min_block, preferred_block, max_block,
    )))


def slot(node_id, *, inline="fill", block="fill", place=None):
    return {
        "id": node_id, "kind": "slot", "source": "title",
        "inlineSize": inline, "blockSize": block,
        "place": {"inline": "stretch", "block": "stretch", "safety": "strict", **(place or {})},
        "priority": "required", "overflow": "visible-overflow",
    }


def container(kind, children, *, inline="fill", block="fill", align="stretch", **extra):
    node = {
        "id": "root", "kind": kind, "inlineSize": inline, "blockSize": block,
        "padding": {"token": "spacing.none"}, "children": children,
    }
    if kind != "overlay":
        node.update(gap={"token": "spacing.none"}, alignItems=align, justifyContent="start")
    node.update(extra)
    return node


def resolved(root, sources):
    raw = {
        "version": "chrona/layout-profile/v0.10", "id": "cross-stretch",
        "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal",
        "requiredThemeTokens": ["spacing.none"],
        "reviewSurface": {
            "rowDistribution": "pack",
            "backgroundExtents": {"rowBand": "table", "groupBand": "timeline",
                                  "groupHeaderBand": "both", "calendarClosed": "timeline"},
            "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2},
        },
        "root": root,
    }
    return resolve_layout_profile(raw, available_sources={"title"},
                                  theme={"body": {"values": TOKEN_VALUES}})


def decisions(manifest):
    return {item.node_id: item.bounds for item in manifest.decisions}


def solve(root, measures, *, inline=200, block=120):
    profile = resolved(root, measures)
    return profile, solve_layout(profile, viewport_inline=inline, viewport_block=block,
                                 measurements=measures)


def test_column_stretch_preserves_fixed_and_still_expands_fill_with_start_unchanged():
    fixed, filled, fr_filled, started = slot("fixed", inline={"fixed": 42}), slot("filled"), \
        slot("fr-filled", inline={"fr": 2}), \
        slot("started", inline={"fixed": 42}, place={"inline": "start"})
    _, manifest = solve(container("column", [fixed, filled, fr_filled, started]),
                        {name: measurement() for name in ("fixed", "filled", "fr-filled", "started")})

    bounds = decisions(manifest)
    assert bounds["fixed"].inline_size == Decimal(42)
    assert bounds["filled"].inline_size == Decimal(200)
    assert bounds["fr-filled"].inline_size == Decimal(200)
    assert bounds["started"].inline == ZERO
    assert bounds["started"].inline_size == Decimal(42)


def test_parent_stretch_applies_to_fixed_container_child_without_slot_override():
    child = container("row", [slot("leaf")], inline={"fixed": 42}, block="fill", align="start")
    child["id"] = "row"
    _, manifest = solve(container("column", [child]), {"leaf": measurement()})

    assert decisions(manifest)["root"].inline_size == Decimal(200)
    assert decisions(manifest)["row"].inline_size == Decimal(42)


def test_fixed_cross_size_above_available_overflows_visibly_without_shrinking():
    _, manifest = solve(container("column", [slot("child", inline={"fixed": 120})]),
                        {"child": measurement()}, inline=100, block=100)

    assert decisions(manifest)["child"].inline_size == Decimal(120)
    assert any(warning.placement_id == "child"
               and warning.required_inline == 120 and warning.available_inline == 100
               for warning in manifest.fit_warnings)


def test_container_start_and_explicit_slot_start_keep_the_characterized_geometry():
    _, manifest = solve(container("column", [
        slot("child", inline={"fixed": 42}, place={"inline": "start"}),
    ], align="start"), {"child": measurement()}, inline=200, block=120)

    bounds = decisions(manifest)["child"]
    assert bounds.inline == ZERO
    assert bounds.inline_size == Decimal(42)


def test_row_stretch_preserves_fixed_block_size_and_expands_fill():
    _, manifest = solve(container("row", [
        slot("fixed", block={"fixed": 36}), slot("filled"),
    ]), {"fixed": measurement(), "filled": measurement()}, inline=200, block=120)

    bounds = decisions(manifest)
    assert bounds["fixed"].block_size == Decimal(36)
    assert bounds["filled"].block_size == Decimal(120)


@pytest.mark.parametrize(("spec", "expected"), [
    ("content", 20), ("min-content", 10), ("max-content", 40),
    ({"fitContent": 15}, 15),
    ({"aspectRatio": 2}, 40),
    ({"minmax": {"min": {"fixed": 30}, "max": {"fixed": 50}}}, 50),
])
def test_column_stretch_retains_intrinsic_ratio_and_bounded_cross_size(spec, expected):
    measure = measurement(preferred_block=20)
    _, manifest = solve(container("column", [slot("child", inline=spec, block={"fixed": 20})]),
                        {"child": measure}, inline=100, block=100)

    assert decisions(manifest)["child"].inline_size == Decimal(expected)


def test_minmax_fixed_target_is_not_replaced_by_cross_stretch():
    spec = {"minmax": {"min": {"fixed": 30}, "max": {"fixed": 50}}}
    too_small, _ = solve(container("column", [slot("child", inline=spec, block="fill")]),
                         {"child": measurement()}, inline=20, block=100)
    too_large, _ = solve(container("column", [slot("child", inline=spec, block="fill")]),
                         {"child": measurement()}, inline=80, block=100)

    small_manifest = solve_layout(too_small, viewport_inline=20, viewport_block=100,
                                  measurements={"child": measurement()})
    assert decisions(small_manifest)["child"].inline_size == Decimal(50)
    assert any(warning.placement_id == "child" for warning in small_manifest.fit_warnings)
    assert decisions(solve_layout(too_large, viewport_inline=80, viewport_block=100,
                                  measurements={"child": measurement()}))["child"].inline_size == Decimal(50)


def test_minmax_content_minimum_above_available_is_preserved_and_warns():
    spec = {"minmax": {"min": "content", "max": "fill"}}
    _, manifest = solve(container("column", [slot("child", inline=spec)]),
                        {"child": measurement(min_inline=120, preferred_inline=140, max_inline=160)},
                        inline=100, block=100)

    assert decisions(manifest)["child"].inline_size == Decimal(120)
    assert any(warning.placement_id == "child" for warning in manifest.fit_warnings)


def test_overlay_child_place_stretch_uses_the_same_fixed_and_fill_rules():
    fixed_inline = slot("fixed-inline", inline={"fixed": 42}, block="fill")
    fixed_block = slot("fixed-block", inline="fill", block={"fixed": 36})
    _, manifest = solve(container("overlay", [fixed_inline, fixed_block]),
                        {"fixed-inline": measurement(), "fixed-block": measurement()},
                        inline=200, block=120)

    bounds = decisions(manifest)
    assert (bounds["fixed-inline"].inline_size, bounds["fixed-inline"].block_size) == (Decimal(42), Decimal(120))
    assert (bounds["fixed-block"].inline_size, bounds["fixed-block"].block_size) == (Decimal(200), Decimal(36))


def test_flow_cross_axis_fill_stretches_to_line_height_but_fixed_and_content_do_not():
    children = [
        slot("flow-fill", block="fill"),
        slot("flow-fixed", block={"fixed": 50}),
        slot("flow-content", block="content"),
        slot("flow-tall", block="content"),
    ]
    measures = {
        "flow-fill": measurement(preferred_inline=20, preferred_block=15),
        "flow-fixed": measurement(preferred_inline=20, preferred_block=50, max_block=80),
        "flow-content": measurement(preferred_inline=20, preferred_block=30),
        "flow-tall": measurement(preferred_inline=20, preferred_block=80, max_block=100),
    }
    profile = resolved(container("flow", children, block="content", itemMinInlineSize=1), measures)
    natural = measure_natural_normal_flow_block(profile, viewport_inline=100, measurements=measures)
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=100, measurements=measures)

    bounds = decisions(manifest)
    assert natural == Decimal(80)
    assert bounds["flow-fill"].block_size == Decimal(80)
    assert bounds["flow-fixed"].block_size == Decimal(50)
    assert bounds["flow-content"].block_size == Decimal(30)


@pytest.mark.parametrize("kind", ["column", "row", "overlay"])
@pytest.mark.parametrize(("spec", "expected"), [
    ("fill", 100), ({"fr": 2}, 100), ({"fixed": 42}, 42),
    ("content", 20), ({"fitContent": 15}, 15),
    ({"minmax": {"min": {"fixed": 30}, "max": {"fixed": 50}}}, 50),
])
def test_start_alignment_keeps_existing_cross_sizes_in_each_caller(kind, spec, expected):
    child = slot("child", inline={"fixed": 20} if kind == "row" else spec,
                 block=spec if kind == "row" else {"fixed": 20},
                 place={"inline": "start", "block": "start"})
    _, manifest = solve(container(kind, [child], align="start"),
                        {"child": measurement()}, inline=100, block=100)
    bounds = decisions(manifest)["child"]
    assert (bounds.block if kind == "row" else bounds.inline) == ZERO
    assert (bounds.block_size if kind == "row" else bounds.inline_size) == Decimal(expected)


def test_flow_start_keeps_natural_fill_height_instead_of_stretching_it():
    children = [slot("fill", block="fill", place={"block": "start"}),
                slot("fixed", block={"fixed": 50}, place={"block": "start"})]
    _, manifest = solve(container("flow", children, align="start", itemMinInlineSize=1),
                        {"fill": measurement(preferred_block=15),
                         "fixed": measurement(preferred_block=50)})
    bounds = decisions(manifest)
    assert bounds["fill"].block_size == Decimal(15)
    assert bounds["fixed"].block_size == Decimal(50)
