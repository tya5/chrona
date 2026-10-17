from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.model.theme_paint import (
    PaintFamily,
    ThemePaintError,
    resolve_theme_paint_inputs,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _tokens(role, values=None):
    values = values or {
        "fill": {"type": "color", "value": "#112233"},
        "stroke": {"type": "color", "value": "#445566"},
        "width": {"type": "number", "value": 1.5},
        "dash": {"type": "dashPattern", "value": [2, 3]},
        "opacity": {"type": "number", "value": 0.4},
    }
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {"values": values, "roles": {"role": role}, "metrics": {}},
    })


def test_resolves_finite_channels_and_keeps_family_values_model_owned():
    result = resolve_theme_paint_inputs(
        _tokens({"fill": "fill", "stroke": "stroke", "strokeWidth": "width",
                "dash": "dash", "opacity": "opacity"}),
        "role", PaintFamily.SOLID,
    )
    assert PaintFamily.TEXT.value == "text"
    assert (result.fill, result.stroke, result.stroke_width, result.dash,
            result.opacity, result.solid_override) == (
                "#112233", "#445566", Decimal("1.5"), (2.0, 3.0), Decimal("0.4"), False)


def test_fill_override_is_only_a_solid_channel_override():
    tokens = _tokens({"stroke": "stroke", "strokeWidth": "width"})
    solid = resolve_theme_paint_inputs(tokens, "role", PaintFamily.SOLID,
                                       fill_override="#abcdef")
    outline = resolve_theme_paint_inputs(tokens, "role", PaintFamily.OUTLINE,
                                         fill_override="#abcdef")
    assert (solid.fill, solid.solid_override) == ("#abcdef", True)
    assert (outline.fill, outline.solid_override) == ("#abcdef", True)


def test_required_channel_diagnostics_keep_scene_pointer_and_code():
    with pytest.raises(ThemePaintError) as error:
        resolve_theme_paint_inputs(_tokens({"stroke": "stroke"}), "role", PaintFamily.SOLID)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_ROLE_REQUIRED", "/body/roles/role/fill")


@pytest.mark.parametrize("family,part_mode,part_color", [
    (PaintFamily.SOLID, "fill", "#fedcba"),
    (PaintFamily.SOLID, "stroke", None),
    (PaintFamily.OUTLINE, "fill", None),
    (PaintFamily.PATH, None, None),
])
def test_encoded_fill_cannot_replace_explicit_parts_or_stroke_channels(family, part_mode, part_color):
    result = resolve_theme_paint_inputs(
        _tokens({"fill": "fill", "stroke": "stroke", "strokeWidth": "width"}),
        "role", family, fill_override="#abcdef", part_mode=part_mode, part_color=part_color,
    )
    assert result.fill == "#112233"
    assert result.stroke == "#445566"
    assert not result.solid_override


def test_ink_only_catalogue_contract_rejects_substrate_but_accepts_ink():
    tokens = _tokens({"stroke": "stroke"})
    accepted = resolve_theme_paint_inputs(
        tokens, "role", PaintFamily.CANVAS, catalog_pattern=True,
        ink_only_pattern=True,
    )
    assert accepted.fill is None and accepted.stroke == "#445566"
    with pytest.raises(ThemePaintError) as error:
        resolve_theme_paint_inputs(
            tokens, "role", PaintFamily.CANVAS, catalog_pattern=True,
            ink_only_pattern=True, pattern_has_substrate=True,
        )
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_PRESENTATION_PAINT_INVALID", "/body/roles/role")


def test_dash_without_stroke_remains_invalid():
    with pytest.raises(ThemePaintError) as error:
        resolve_theme_paint_inputs(
            _tokens({"fill": "fill", "dash": "dash"}), "role", PaintFamily.SOLID)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_PRESENTATION_PAINT_INVALID", "/body/roles/role")
