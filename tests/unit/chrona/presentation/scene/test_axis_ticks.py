"""Axis ticks at interval starts (#492): a Theme-declared length on the grid roles.

Synthetic input only: nothing here reads `examples/`.
"""
from __future__ import annotations

import pytest

from chrona.presentation.model.surface_content import AxisTier
from chrona.presentation.scene.capabilities import theme_role_contract, theme_role_property_consumer
from chrona.presentation.scene.v05_builder import SceneBuildError
from tests.unit.chrona.presentation.scene.test_v05_builder import _axis_tiers_scene, _theme

AXIS_BOTTOM = 48.0  # the synthetic manifest's axis slot spans block 0..48; the plot starts at 48


def _theme_with(**lengths):
    """A Theme whose named grid roles declare `tickLength` (role name -> px)."""
    theme = _theme()
    for role, length in lengths.items():
        role = role.replace("_", "-")
        theme["body"]["values"][f"{role}-tick"] = {"type": "number", "value": length}
        theme["body"]["roles"][role] = {**theme["body"]["roles"][role], "tickLength": f"{role}-tick"}
    return theme


def _grid(surface, tier):
    return [node for node in surface.primitives if node.scene_id.startswith(f"axis-grid:{tier}:")]


TIERS = (AxisTier("month", 1, "grid-major"), AxisTier("week", 1, "grid-minor"))


def test_a_week_tier_draws_ticks_of_the_theme_length_standing_on_the_axis_rule():
    surface = _axis_tiers_scene(TIERS, theme=_theme_with(axis_minor=6))

    ticks = _grid(surface, 1)
    assert len(ticks) >= 52
    for node in ticks:
        (x0, y0), (x1, y1) = node.points
        assert x0 == x1
        assert (y0, y1) == (AXIS_BOTTOM - 6, AXIS_BOTTOM)
        assert node.visual_role == "axis-minor"


def test_a_tier_whose_role_declares_no_length_keeps_the_full_height_line():
    surface = _axis_tiers_scene(TIERS, theme=_theme_with(axis_minor=6))

    for node in _grid(surface, 0):
        (_, y0), (_, y1) = node.points
        assert (y0, y1) == (AXIS_BOTTOM, 1000.0)


def test_the_major_role_draws_ticks_too_and_each_role_has_its_own_length():
    surface = _axis_tiers_scene(TIERS, theme=_theme_with(axis_major=10, axis_minor=4))

    assert {(node.points[0][1], node.points[1][1]) for node in _grid(surface, 0)} == {(AXIS_BOTTOM - 10, AXIS_BOTTOM)}
    assert {(node.points[0][1], node.points[1][1]) for node in _grid(surface, 1)} == {(AXIS_BOTTOM - 4, AXIS_BOTTOM)}


def test_ticks_stand_at_exactly_the_interval_starts_of_the_full_height_line():
    full = _axis_tiers_scene(TIERS)
    ticked = _axis_tiers_scene(TIERS, theme=_theme_with(axis_minor=6))

    assert [(node.scene_id, node.points[0][0]) for node in _grid(ticked, 1)] == \
           [(node.scene_id, node.points[0][0]) for node in _grid(full, 1)]
    assert [node.paint_order for node in _grid(ticked, 1)] == [node.paint_order for node in _grid(full, 1)]
    # The untouched tier is identical primitive for primitive.
    assert _grid(ticked, 0) == _grid(full, 0)


def test_a_length_equal_to_the_axis_slot_is_allowed():
    surface = _axis_tiers_scene(TIERS, theme=_theme_with(axis_minor=48))

    assert all(node.points[0][1] == 0.0 for node in _grid(surface, 1))


@pytest.mark.parametrize("length, code", [(0, "E_PRESENTATION_AXIS_INVALID"), (-3, "E_PRESENTATION_AXIS_INVALID"),
                                          (49, "E_PRESENTATION_AXIS_OVERFLOW")])
def test_an_invalid_or_oversized_length_is_diagnosed_not_clamped(length, code):
    with pytest.raises(SceneBuildError) as error:
        _axis_tiers_scene(TIERS, theme=_theme_with(axis_minor=length))

    assert error.value.diagnostic_id == code
    assert error.value.detail == "tick-length:axis-minor"


def test_a_length_is_ignored_when_the_view_declares_no_grid_tier_for_the_role():
    surface = _axis_tiers_scene((AxisTier("month", 1, "grid-major"),), theme=_theme_with(axis_minor=500))

    assert all(node.points[1][1] == 1000.0 for node in _grid(surface, 0))


def test_role_admission_admits_tick_length_on_the_two_grid_roles_only():
    for role in ("axis-major", "axis-minor"):
        assert "tickLength" in theme_role_contract(role).properties
        assert theme_role_property_consumer(role, "tickLength") == "Layout axis grid or tick and Scene Path"
        assert theme_role_contract(role).owner_of("tickLength") == "Layout/Scene completed geometry"
    for role in ("axis-rule", "axis-cell-separator", "axis", "axis-band-decoration", "dependency", "as-of"):
        assert theme_role_property_consumer(role, "tickLength") is None
