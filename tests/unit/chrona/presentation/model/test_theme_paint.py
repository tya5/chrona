from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.model.theme_paint import (
    PaintFamily,
    ThemePaintError,
    choose_fill_override,
    resolve_theme_paint_inputs,
    resolve_theme_paint_witness,
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


def test_witness_retains_admitted_gradient_identity_without_geometry():
    tokens = _tokens({"fill": "fill", "gradientStart": "start", "gradientEnd": "end",
                      "gradientAngle": "angle", "gradientFidelity": "fidelity"}, {
        "fill": {"type": "color", "value": "#112233"},
        "start": {"type": "color", "value": "#112233"},
        "end": {"type": "color", "value": "#445566"},
        "angle": {"type": "number", "value": 45},
        "fidelity": {"type": "fidelity", "value": "required"},
    })

    witness = resolve_theme_paint_witness(tokens, "role", PaintFamily.SOLID)

    assert witness.gradient is not None and witness.gradient.admitted
    assert witness.gradient.identity == ("#112233", "#445566", Decimal("45"), "required")
    assert witness.identity[0] == ("gradient", witness.gradient.identity)


def test_witness_optional_omission_uses_solid_identity_and_solid_override_replaces_gradient():
    tokens = _tokens({"fill": "fill", "gradientStart": "start", "gradientEnd": "end",
                      "gradientAngle": "angle", "gradientFidelity": "fidelity"}, {
        "fill": {"type": "color", "value": "#112233"},
        "start": {"type": "color", "value": "#112233"},
        "end": {"type": "color", "value": "#445566"},
        "angle": {"type": "number", "value": 45},
        "fidelity": {"type": "fidelity", "value": "decorative-optional"},
    })

    omitted = resolve_theme_paint_witness(
        tokens, "role", PaintFamily.SOLID,
        gradient_supported=False, optional_gradient_omission=True,
    )
    replaced = resolve_theme_paint_witness(
        tokens, "role", PaintFamily.SOLID,
        gradient_supported=False, optional_gradient_omission=True,
        fill_override="#abcdef",
    )

    assert omitted.gradient is not None and not omitted.gradient.admitted
    assert omitted.identity == (("solid", "#112233"), None, None, (), Decimal(1))
    assert replaced.channels.fill == "#abcdef" and replaced.channels.solid_override
    assert replaced.gradient is None


@pytest.mark.parametrize(("style", "legend", "eligible", "actual", "expected"), [
    ("style", "legend", True, "actual", "legend"),
    (None, "legend", True, "actual", "legend"),
    (None, None, True, "actual", "actual"),
    (None, None, False, "actual", None),
])
def test_fill_override_precedence_is_shared(style, legend, eligible, actual, expected):
    assert choose_fill_override(style_fill=style, legend_fill=legend,
                                actual_eligible=eligible, actual_fill=actual) == expected


def test_witness_identity_uses_effective_glyph_channels_not_replaced_role_channels():
    tokens = _tokens({"fill": "fill", "stroke": "stroke", "strokeWidth": "width"})
    filled = resolve_theme_paint_witness(tokens, "role", PaintFamily.SOLID,
                                         fill_override="#abcdef", part_mode="fill",
                                         part_color="#fedcba")
    outlined = resolve_theme_paint_witness(tokens, "role", PaintFamily.OUTLINE,
                                           part_mode="fill", part_color="#fedcba")

    assert filled.effective_channels.fill == "#fedcba"
    assert filled.effective_channels.stroke is None
    assert filled.identity[0] == ("solid", "#FEDCBA")
    assert outlined.effective_channels.fill is None


def test_witness_identity_retains_pattern_and_paint_family():
    base_values = {
        "fill": {"type": "color", "value": "#112233"},
        "stroke": {"type": "color", "value": "#445566"},
        "width": {"type": "number", "value": 1.5},
    }
    common = {"fill": "fill", "stroke": "stroke", "strokeWidth": "width"}
    outline_tokens = _tokens({**common, "pattern": "pattern"}, {
        **base_values,
        "pattern": {"type": "pattern", "value": {"kind": "outline", "gap": 3}},
    })
    hatch_tokens = _tokens({**common, "pattern": "pattern"}, {
        **base_values,
        "pattern": {"type": "pattern", "value": {"kind": "diagonal-hatch", "angle": 45}},
    })

    outline = resolve_theme_paint_witness(outline_tokens, "role", PaintFamily.SOLID)
    hatch = resolve_theme_paint_witness(hatch_tokens, "role", PaintFamily.SOLID)
    family = resolve_theme_paint_witness(hatch_tokens, "role", PaintFamily.OUTLINE,
                                         fill_override="#abcdef")
    solid = resolve_theme_paint_witness(hatch_tokens, "role", PaintFamily.SOLID,
                                        fill_override="#abcdef")

    assert outline.identity == hatch.identity
    assert solid.identity == family.identity
    assert outline.pattern_identity == (("gap", (3,)), ("kind", ("outline",)))


def test_witness_normalizes_hex_case_and_omitted_opacity():
    upper = resolve_theme_paint_witness(
        _tokens({"fill": "fill"}, {"fill": {"type": "color", "value": "#AABBCC"}}),
        "role", PaintFamily.SOLID,
    )
    lower = resolve_theme_paint_witness(
        _tokens({"fill": "fill"}, {"fill": {"type": "color", "value": "#aabbcc"}}),
        "role", PaintFamily.SOLID,
    )

    assert upper.identity == lower.identity == (("solid", "#AABBCC"), None, None, (), Decimal(1))
