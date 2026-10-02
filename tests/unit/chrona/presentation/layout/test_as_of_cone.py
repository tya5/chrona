"""The as-of light cone is completed by Layout from the as-of x and the plot (#890).

Synthetic Themes and plots only: nothing here reads `examples/`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.as_of_cone import (
    AS_OF_CONE_PAINT_ORDER, AS_OF_CONE_PLACEMENT_ID, complete_as_of_cone,
)
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_geometry import BACKGROUND_PAINT_ORDER
from chrona.presentation.layout.surface_marks import MARK_PAINT_ORDER_BASE
from chrona.presentation.model.theme_tokens import ThemeTokenView

PLOT = Rect(Decimal(100), Decimal(50), Decimal(400), Decimal(200))


def _tokens(*, spread=0.25, extent=1, **extra) -> ThemeTokenView:
    values = {"spread": {"type": "number", "value": spread}, "extent": {"type": "number", "value": extent},
              "ink": {"type": "color", "value": "#FFD24A"}}
    role = {"fill": "ink", "coneSpread": "spread", "coneExtent": "extent", **extra}
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": values, "roles": {"as-of-cone": role}, "metrics": {}}})


def _bare() -> ThemeTokenView:
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {}, "roles": {"text": {}}, "metrics": {}}})


def _points(cone):
    return tuple(cone.points)


def test_a_theme_without_the_role_has_no_cone() -> None:
    assert complete_as_of_cone(_bare(), PLOT, 300.0) is None


def test_the_apex_is_the_top_of_the_line_and_the_foot_is_extent_times_the_plot_height() -> None:
    cone = complete_as_of_cone(_tokens(spread=0.25, extent=0.5), PLOT, 300.0)

    assert cone.placement_id == AS_OF_CONE_PLACEMENT_ID and cone.kind == "Polygon" and cone.semantic_id == "asOfCone"
    assert _points(cone) == ((300.0, 50.0), (325.0, 150.0), (275.0, 150.0))
    assert (cone.bounds.inline, cone.bounds.block, cone.bounds.inline_size, cone.bounds.block_size) == (
        Decimal("275.0"), Decimal("50.0"), Decimal("50.0"), Decimal("100.0"))


def test_the_foot_of_a_full_extent_cone_is_the_last_row_of_the_plot() -> None:
    cone = complete_as_of_cone(_tokens(spread=0.1, extent=1), PLOT, 300.0)

    assert max(y for _, y in cone.points) == 250.0
    assert cone.bounds.block + cone.bounds.block_size == PLOT.block + PLOT.block_size


def test_a_shorter_plot_ends_the_cone_with_it() -> None:
    short = Rect(Decimal(100), Decimal(50), Decimal(400), Decimal(80))  # #880: the plot stops at the last row

    cone = complete_as_of_cone(_tokens(spread=0.5, extent=1), short, 300.0)

    assert max(y for _, y in cone.points) == 130.0 and max(abs(x - 300.0) for x, _ in cone.points) == 40.0


def test_spread_is_the_half_width_per_unit_of_depth() -> None:
    narrow = complete_as_of_cone(_tokens(spread=0.1), PLOT, 300.0)
    wide = complete_as_of_cone(_tokens(spread=1.0), PLOT, 300.0)

    assert (narrow.bounds.inline_size, wide.bounds.inline_size) == (Decimal("40.0"), Decimal("400.0"))


def test_the_cone_is_clipped_to_the_plot_on_both_sides() -> None:
    left = complete_as_of_cone(_tokens(spread=1.0), PLOT, 150.0)
    right = complete_as_of_cone(_tokens(spread=1.0), PLOT, 480.0)

    for cone in (left, right):
        assert all(100.0 <= x <= 500.0 for x, _ in cone.points)
    assert left.bounds.inline == Decimal(100) and right.bounds.inline + right.bounds.inline_size == Decimal(500)
    # The clipped polygon keeps its apex and stays convex with the cut edge on the plot side.
    assert _points(left)[0] == (150.0, 50.0) and (100.0, 100.0) in _points(left)


def test_a_cone_that_the_clip_leaves_no_area_gives_nothing() -> None:
    assert complete_as_of_cone(_tokens(spread=0.5), Rect(Decimal(100), Decimal(50), Decimal(400), Decimal(0)), 300.0) is None


def test_the_cone_is_painted_above_the_bands_and_below_the_marks() -> None:
    cone = complete_as_of_cone(_tokens(), PLOT, 300.0)

    assert BACKGROUND_PAINT_ORDER + 2 < cone.paint_order < MARK_PAINT_ORDER_BASE
    assert cone.paint_order == AS_OF_CONE_PAINT_ORDER


def test_the_path_commands_are_the_closed_polygon() -> None:
    cone = complete_as_of_cone(_tokens(), PLOT, 300.0)

    assert [command.kind for command in cone.path_commands] == ["move", "line", "line", "line"]
    assert cone.path_commands[0].points == cone.path_commands[-1].points == (cone.points[0],)


def test_two_completions_are_equal() -> None:
    assert complete_as_of_cone(_tokens(spread=0.37, extent=0.8), PLOT, 301.3) == complete_as_of_cone(
        _tokens(spread=0.37, extent=0.8), PLOT, 301.3)


@pytest.mark.parametrize("spread, extent, pointer", [
    (0, 1, "coneSpread"), (4.5, 1, "coneSpread"), (-1, 1, "coneSpread"),
    (0.3, 0, "coneExtent"), (0.3, 1.5, "coneExtent")])
def test_a_value_out_of_range_fails_at_its_exact_pointer(spread, extent, pointer) -> None:
    with pytest.raises(LayoutError) as caught:
        complete_as_of_cone(_tokens(spread=spread, extent=extent), PLOT, 300.0)

    assert caught.value.diagnostic_id == "E_VISUAL_CAPABILITY_LIMIT"
    assert caught.value.path == f"/body/roles/as-of-cone/{pointer}"


def test_a_spread_without_an_extent_is_refused() -> None:
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"spread": {"type": "number", "value": 0.3}},
        "roles": {"as-of-cone": {"coneSpread": "spread"}}, "metrics": {}}})

    with pytest.raises(LayoutError) as caught:
        complete_as_of_cone(tokens, PLOT, 300.0)

    assert (caught.value.diagnostic_id, caught.value.path) == ("E_THEME_ROLE_REQUIRED", "/body/roles/as-of-cone/coneExtent")
