"""Axis cell corners (#491): a Theme band role declares a radius or a chamfer for its cells.

Synthetic input only: nothing here reads `examples/`. Every expected outline is computed from the cell's own drawn
bounds (the Scene's own scale and the declared gap), so the tests do not repeat the geometry code under test.
"""
from __future__ import annotations

import pytest

from chrona.presentation.model.surface_content import AxisTier
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.capabilities import theme_role_contract
from chrona.presentation.scene.v05_builder import SceneBuildError
from tests.unit.chrona.presentation.scene.test_v05_builder import _axis_tiers_scene, _theme

SLOT_BLOCK, SLOT_HEIGHT = 0.0, 48.0  # the synthetic manifest's axis slot spans block 0..48
BAND = "axis-band-decoration"


def _theme_with(role=BAND, *, radius=None, chamfer=None, gap=None, pattern=None):
    theme = _theme()
    body = theme["body"]
    for name, value in (("cellCornerRadius", radius), ("cellCornerChamfer", chamfer), ("cellGap", gap)):
        if value is not None:
            body["values"][f"v-{name}"] = {"type": "number", "value": value}
            body["roles"][role] = {**body["roles"][role], name: f"v-{name}"}
    if pattern is not None:
        body["roles"][role] = {**body["roles"][role], "pattern": pattern}
    return theme


def _cells(surface, tier=0):
    return sorted((node for node in surface.primitives if node.scene_id.startswith(f"axis-band-rect:{tier}:")),
                  key=lambda node: int(node.scene_id.rsplit(":", 1)[1]))


def _outline(node):
    return [(command.kind, command.points[0]) for command in node.symbol.outline]


def _expected_chamfer(bounds, cut):
    x, y, width, height = bounds
    right, bottom = x + width, y + height
    points = [(x + cut, y), (right - cut, y), (right, y + cut), (right, bottom - cut),
              (right - cut, bottom), (x + cut, bottom), (x, bottom - cut), (x, y + cut)]
    return [("move", points[0]), *(("line", point) for point in points[1:]), ("line", points[0])]


MONTH = (AxisTier("month", 1, "band"),)
WEEK = (AxisTier("week", 1, "band"),)


def test_without_a_declaration_every_cell_is_a_square_rect():
    cells = _cells(_axis_tiers_scene(MONTH))

    assert len(cells) == 12
    assert {(node.kind, node.corner_radius, node.symbol) for node in cells} == {("Rect", None, None)}


def test_a_radius_rounds_every_cell_by_its_ratio_of_the_cell_block_size_and_moves_nothing_else():
    plain = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(gap=4)))
    rounded = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(radius=0.25, gap=4)))

    assert [(node.scene_id, node.bounds, node.paint_order, node.visual_role, node.purpose) for node in rounded] == \
           [(node.scene_id, node.bounds, node.paint_order, node.visual_role, node.purpose) for node in plain]
    assert {node.kind for node in rounded} == {"Rect"}
    assert {node.corner_radius for node in rounded} == {0.25 * SLOT_HEIGHT}


def test_a_chamfer_is_a_closed_eight_point_polygon_inside_the_cell_in_every_cell():
    cells = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(chamfer=0.25, gap=4)))

    assert len(cells) == 12
    for node in cells:
        assert node.kind == "Symbol"
        assert _outline(node) == _expected_chamfer(node.bounds, 0.25 * SLOT_HEIGHT)
        x, y, width, height = node.bounds
        for _, (px, py) in _outline(node):
            assert x <= px <= x + width and y <= py <= y + height
            assert SLOT_BLOCK <= py <= SLOT_BLOCK + SLOT_HEIGHT


def test_a_chamfered_cell_keeps_identity_paint_and_role_of_its_square_cell():
    plain = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(gap=4)))
    cut = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(chamfer=0.25, gap=4)))

    assert [(n.scene_id, n.bounds, n.paint_order, n.visual_role, n.purpose, n.paint) for n in cut] == \
           [(n.scene_id, n.bounds, n.paint_order, n.visual_role, n.purpose, n.paint) for n in plain]


def test_the_first_and_last_cell_round_their_outer_corners_like_any_other_and_gaps_separate_the_rest():
    cells = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(chamfer=0.125, gap=4)))

    first, second, last = cells[0], cells[1], cells[-1]
    cut = 0.125 * SLOT_HEIGHT
    assert _outline(first) == _expected_chamfer(first.bounds, cut)
    assert _outline(last) == _expected_chamfer(last.bounds, cut)
    # the gap lies between cells: the second cell starts half a gap inside its interval, the first reaches the plot edge
    assert second.bounds[0] - (first.bounds[0] + first.bounds[2]) == pytest.approx(4.0)


def test_abutting_cells_each_take_their_own_corners_and_leave_a_notch_at_the_shared_edge():
    cells = _cells(_axis_tiers_scene(MONTH, theme=_theme_with(radius=0.25)))

    for left, right in zip(cells, cells[1:]):
        assert left.bounds[0] + left.bounds[2] == pytest.approx(right.bounds[0])  # the shared edge
        assert left.corner_radius == right.corner_radius == 0.25 * SLOT_HEIGHT    # neither knows the other


def test_a_corner_is_measured_against_the_lane_of_its_own_tier():
    surface = _axis_tiers_scene((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")),
                                theme=_theme_with(BAND, radius=0.5))

    quarter = _cells(surface, 0)
    month = _cells(surface, 1)
    assert {node.corner_radius for node in quarter} == {node.bounds[3] / 2 for node in quarter}
    assert {node.corner_radius for node in month} == {None}  # the second band role declares none


def test_each_band_role_has_its_own_corner():
    theme = _theme_with(BAND, chamfer=0.25)
    other = _theme_with("axis-band-decoration2", radius=0.125)
    theme["body"]["values"].update(other["body"]["values"])
    theme["body"]["roles"]["axis-band-decoration2"] = other["body"]["roles"]["axis-band-decoration2"]
    surface = _axis_tiers_scene((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")), theme=theme)

    assert {node.kind for node in _cells(surface, 0)} == {"Symbol"}
    assert {node.kind for node in _cells(surface, 1)} == {"Rect"}


@pytest.mark.parametrize("shape", ["radius", "chamfer"])
def test_a_corner_above_half_the_cell_is_diagnosed_not_clamped(shape):
    with pytest.raises(SceneBuildError) as error:
        _axis_tiers_scene(MONTH, theme=_theme_with(**{shape: 0.51}))

    assert (error.value.diagnostic_id, error.value.detail) == ("E_PRESENTATION_AXIS_INVALID", "cell-corner:0")


@pytest.mark.parametrize("shape", ["radius", "chamfer"])
@pytest.mark.parametrize("ratio", [0, -0.1])
def test_a_non_positive_corner_is_diagnosed(shape, ratio):
    with pytest.raises(SceneBuildError) as error:
        _axis_tiers_scene(MONTH, theme=_theme_with(**{shape: ratio}))

    assert (error.value.diagnostic_id, error.value.detail) == ("E_PRESENTATION_AXIS_INVALID", "cell-corner:0")


def test_half_the_block_size_is_allowed():
    cells = _cells(_axis_tiers_scene((AxisTier("quarter", 1, "band"),), theme=_theme_with(radius=0.5, gap=2)))

    assert {node.corner_radius for node in cells} == {SLOT_HEIGHT / 2}


def test_both_shapes_on_one_role_are_diagnosed():
    with pytest.raises(SceneBuildError) as error:
        _axis_tiers_scene(MONTH, theme=_theme_with(radius=0.25, chamfer=0.25))

    assert (error.value.diagnostic_id, error.value.detail) == ("E_PRESENTATION_AXIS_INVALID", "cell-corner-both:0")


def test_a_chamfer_with_a_pattern_on_the_same_role_is_diagnosed():
    pattern = {"kind": "outline"}
    theme = _theme_with(chamfer=0.25, pattern="cell-pattern")
    theme["body"]["values"]["cell-pattern"] = {"type": "pattern", "value": pattern}
    with pytest.raises(SceneBuildError) as error:
        _axis_tiers_scene(MONTH, theme=theme)
    assert (error.value.diagnostic_id, error.value.detail) == ("E_PRESENTATION_AXIS_INVALID", "cell-chamfer-pattern:0")


def test_a_corner_on_a_role_whose_tier_is_not_declared_is_ignored():
    surface = _axis_tiers_scene((AxisTier("month", 1, "grid-major"),), theme=_theme_with(radius=2.0))

    assert not _cells(surface)


def test_a_cell_narrower_than_twice_the_corner_is_reduced_to_half_its_width_and_recorded():
    surface = _axis_tiers_scene(WEEK, theme=_theme_with(radius=0.5, gap=0))

    cells = _cells(surface)
    assert len(cells) >= 52
    for node in cells:
        width = node.bounds[2]
        assert width < SLOT_HEIGHT  # a week is narrower than the 24px corner on this scale
        assert node.corner_radius == pytest.approx(width / 2)
        assert f"W_LAYOUT_AXIS_CELL_CORNER_REDUCED:{node.scene_id}" in surface.diagnostics


def test_a_chamfer_in_a_narrow_cell_is_reduced_the_same_way_and_stays_inside_the_cell():
    surface = _axis_tiers_scene(WEEK, theme=_theme_with(chamfer=0.5))

    for node in _cells(surface):
        assert _outline(node) == _expected_chamfer(node.bounds, node.bounds[2] / 2)
        assert f"W_LAYOUT_AXIS_CELL_CORNER_REDUCED:{node.scene_id}" in surface.diagnostics


def test_a_cell_wide_enough_for_its_corner_records_no_reduction():
    surface = _axis_tiers_scene(MONTH, theme=_theme_with(radius=0.125, gap=4))

    assert not [item for item in surface.diagnostics if "CELL_CORNER" in item]


def test_role_admission_admits_both_properties_on_the_band_roles_only():
    for role in ("axis-band-decoration", "axis-band-decoration2"):
        for name in ("cellCornerRadius", "cellCornerChamfer"):
            assert name in theme_role_contract(role).properties
        assert {"Rect", "Symbol"} <= set(theme_role_contract(role).scene_kinds)
    for role in ("axis-rule", "axis-cell-separator", "axis", "period-band", "row-band", "planned"):
        assert "cellCornerRadius" not in theme_role_contract(role).properties


# --- the other adapters ------------------------------------------------------------------------------------


def test_typst_draws_a_radius_and_a_chamfer_as_its_polygon():
    rounded = _axis_tiers_scene(MONTH, theme=_theme_with(radius=0.25, gap=4))
    cell = _cells(rounded)[1]

    assert f"radius: {cell.corner_radius:g}pt" in render_v05_typst(rounded)
    cut = _axis_tiers_scene(MONTH, theme=_theme_with(chamfer=0.25, gap=4))
    drawn = render_v05_typst(cut)
    assert drawn.count("curve.close()") >= len(_cells(cut))


def test_tikz_draws_a_radius_as_rounded_corners_and_a_chamfer_as_its_polygon():
    rounded = _axis_tiers_scene(MONTH, theme=_theme_with(radius=0.25, gap=4))
    cut = _axis_tiers_scene(MONTH, theme=_theme_with(chamfer=0.25, gap=4))

    assert f"rounded corners={_cells(rounded)[1].corner_radius:g}pt" in render_v05_tikz(rounded)
    def number(value):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    path = " -- ".join(f"({number(px)},{number(py)})" for _, (px, py) in _outline(_cells(cut)[1]))
    assert path in render_v05_tikz(cut)
