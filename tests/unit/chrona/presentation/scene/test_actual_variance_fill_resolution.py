"""Completed fill precedence without changing Actual geometry paint."""
from __future__ import annotations

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.paint import PaintFamily, ScenePaintError, resolve_scene_paint
from chrona.presentation.scene.visual_capabilities import BASELINE_PROFILE, SVG_PROFILE, resolve_visual_profile


def _tokens(role: dict[str, str], values: dict[str, dict[str, object]]) -> ThemeTokenView:
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": values, "roles": {"role": role}, "metrics": {}},
    })


def _gradient_tokens(*, fidelity: str | None = None) -> ThemeTokenView:
    values = {
        "fill": {"type": "color", "value": "#112233"},
        "start": {"type": "color", "value": "#112233"},
        "end": {"type": "color", "value": "#445566"},
        "angle": {"type": "number", "value": 45},
    }
    role = {"fill": "fill", "gradientStart": "start", "gradientEnd": "end", "gradientAngle": "angle"}
    if fidelity is not None:
        values["fidelity"] = {"type": "fidelity", "value": fidelity}
        role["gradientFidelity"] = "fidelity"
    return _tokens(role, values)


def test_selected_solid_actual_fill_bypasses_required_gradient_without_omission():
    tokens = _gradient_tokens()
    profile = resolve_visual_profile(BASELINE_PROFILE, "svg")

    with pytest.raises(ScenePaintError) as error:
        resolve_scene_paint(tokens, "role", PaintFamily.SOLID, visual_profile=profile,
                            gradient_bounds=(0, 0, 10, 10))
    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED"

    resolution = resolve_scene_paint(tokens, "role", PaintFamily.SOLID, visual_profile=profile,
                                     fill_override="#CC0000", gradient_bounds=(0, 0, 10, 10))
    assert resolution.paint.fill == "#CC0000"
    assert resolution.paint.gradient is None
    assert resolution.omissions == ()


def test_selected_solid_actual_fill_drops_obsolete_optional_gradient_omission():
    tokens = _gradient_tokens(fidelity="decorative-optional")
    profile = resolve_visual_profile(BASELINE_PROFILE, "svg")

    default = resolve_scene_paint(tokens, "role", PaintFamily.SOLID, visual_profile=profile,
                                  gradient_bounds=(0, 0, 10, 10))
    assert default.paint.gradient is None and len(default.omissions) == 1

    selected = resolve_scene_paint(tokens, "role", PaintFamily.SOLID, visual_profile=profile,
                                    fill_override="#CC0000", gradient_bounds=(0, 0, 10, 10))
    assert selected.paint.fill == "#CC0000"
    assert selected.paint.gradient is None
    assert selected.omissions == ()


def test_default_gradient_resolution_is_unchanged_without_actual_fill_selection():
    tokens = _gradient_tokens()
    resolution = resolve_scene_paint(tokens, "role", PaintFamily.SOLID,
                                     visual_profile=resolve_visual_profile(SVG_PROFILE, "svg"),
                                     gradient_bounds=(0, 0, 10, 10))
    assert resolution.paint.fill == "#112233"
    assert resolution.paint.gradient is not None
    assert resolution.omissions == ()


def test_explicit_glyph_fill_and_stroke_only_parts_ignore_actual_fill_selection():
    tokens = _tokens(
        {"fill": "fill", "stroke": "stroke", "strokeWidth": "width"},
        {"fill": {"type": "color", "value": "#112233"},
         "stroke": {"type": "color", "value": "#445566"},
         "width": {"type": "number", "value": 1.5}},
    )
    explicit_part = resolve_scene_paint(tokens, "role", PaintFamily.SOLID,
                                        fill_override="#CC0000", part_mode="fill",
                                        part_color="#00AA00").paint
    assert explicit_part.fill == "#00AA00"

    stroke_part = resolve_scene_paint(tokens, "role", PaintFamily.SOLID,
                                      fill_override="#CC0000", part_mode="stroke").paint
    assert stroke_part.fill is None
    assert stroke_part.stroke == "#445566"


def test_selected_actual_fill_preserves_pattern_ink_and_stroke():
    tokens = _tokens(
        {"fill": "fill", "stroke": "stroke", "strokeWidth": "width"},
        {"fill": {"type": "color", "value": "#112233"},
         "stroke": {"type": "color", "value": "#445566"},
         "width": {"type": "number", "value": 1.5}},
    )
    paint = resolve_scene_paint(tokens, "role", PaintFamily.SOLID,
                                fill_override="#CC0000", catalog_pattern=True).paint
    assert paint.fill == "#CC0000"
    assert paint.stroke == "#445566"
    assert paint.stroke_width == 1.5
