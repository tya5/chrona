"""Layout completes one canvas texture from a Theme-declared catalogue pattern (#587).

Synthetic Theme and canvas only: nothing here reads `examples/`.
"""
from decimal import Decimal

import pytest

from chrona.presentation.layout.canvas_texture import (
    CANVAS_SLOT_ID, CANVAS_TEXTURE_PLACEMENT_ID, complete_canvas_texture,
)
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.model.theme_tokens import ThemeTokenView

ENTRY = {"tile": {"inlineSize": 12, "blockSize": 21}, "angle": 0, "densityBasisPoints": 1455,
         "primitives": [{"kind": "path", "paint": "stroke", "strokeWidth": 0.9, "lineCap": "round",
                         "lineJoin": "round",
                         "commands": [{"kind": "move", "points": [0, 0]}, {"kind": "line", "points": [6, 3.5]}]}]}


def _tokens(roles: dict | None = None, values: dict | None = None) -> ThemeTokenView:
    base_values = {"texture": {"type": "pattern", "value": {"kind": "catalog", "ref": "local:lattice"}},
                   "ground": {"type": "color", "value": "#101820"}, "ink": {"type": "color", "value": "#243447"}}
    base_roles = {"canvas-texture": {"pattern": "texture", "fill": "ground", "stroke": "ink"}}
    theme = {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {**base_values, **(values or {})},
        "roles": base_roles if roles is None else roles,
        "metrics": {}, "catalogAssets": {"glyphs": {}, "patterns": {"local:lattice": ENTRY}}}}
    return ThemeTokenView(theme)


def _canvas() -> Rect:
    return Rect(Decimal("-8"), Decimal("4"), Decimal("1600"), Decimal("900"))


def test_a_theme_without_the_role_has_no_texture() -> None:
    assert complete_canvas_texture(_tokens(roles={}), _canvas()) is None


def test_a_role_that_names_no_pattern_has_no_texture() -> None:
    assert complete_canvas_texture(_tokens(roles={"canvas-texture": {"fill": "ground", "stroke": "ink"}}), _canvas()) is None


def test_tokens_that_cannot_declare_roles_have_no_texture() -> None:
    assert complete_canvas_texture(None, _canvas()) is None


def test_a_declared_texture_is_one_rect_over_the_whole_canvas_below_every_paint_order() -> None:
    canvas = _canvas()
    texture = complete_canvas_texture(_tokens(), canvas)

    assert texture is not None
    assert (texture.shape.placement_id, texture.shape.kind, texture.shape.semantic_id) == (
        CANVAS_TEXTURE_PLACEMENT_ID, "Rect", "canvasTexture")
    assert texture.shape.bounds == canvas
    assert texture.shape.paint_order == 0
    assert texture.shape.slot_id == texture.slot.slot_id == CANVAS_SLOT_ID
    assert texture.slot.bounds == canvas


def test_the_tile_phase_is_the_canvas_top_left_not_the_viewport_origin() -> None:
    canvas = _canvas()
    pattern = complete_canvas_texture(_tokens(), canvas).pattern

    assert pattern.placement_id == CANVAS_TEXTURE_PLACEMENT_ID
    assert pattern.pattern.origin == (-8.0, 4.0)
    assert pattern.pattern.region == canvas and pattern.pattern.clip == canvas
    assert (pattern.pattern.tile_inline_size, pattern.pattern.tile_block_size) == (12.0, 21.0)
    assert pattern.pattern.density_basis_points == 1455
    assert [item.kind for item in pattern.pattern.primitives] == ["path"]


def test_the_same_theme_and_canvas_always_complete_the_same_texture() -> None:
    first = complete_canvas_texture(_tokens(), _canvas())
    second = complete_canvas_texture(_tokens(), _canvas())

    assert first == second


def test_an_inline_pattern_cannot_be_a_texture() -> None:
    inline = {"hatch": {"type": "pattern", "value": {"kind": "diagonal-hatch", "tileInlineSize": 6,
                                                     "tileBlockSize": 6, "angle": 45, "strokeWidth": 1}}}
    tokens = _tokens(roles={"canvas-texture": {"pattern": "hatch"}}, values=inline)

    with pytest.raises(LayoutError) as error:
        complete_canvas_texture(tokens, _canvas())

    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.path == "/body/roles/canvas-texture/pattern"
