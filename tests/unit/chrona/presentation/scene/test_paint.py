from __future__ import annotations

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.paint import PaintFamily, ScenePaintError, resolve_scene_paint


def _tokens(role: dict[str, str], values: dict[str, dict[str, object]] | None = None) -> ThemeTokenView:
    values = values or {
        "fill": {"type": "color", "value": "#112233"},
        "stroke": {"type": "color", "value": "#445566"},
        "width": {"type": "number", "value": 1.5},
        "dash": {"type": "dashPattern", "value": [2, 3]},
        "opacity": {"type": "number", "value": 0.4},
    }
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": {"role": role}, "metrics": {}}})


def test_resolver_completes_mixed_solid_paint_without_adapter_defaults():
    paint = resolve_scene_paint(_tokens({"fill": "fill", "stroke": "stroke", "strokeWidth": "width", "dash": "dash", "opacity": "opacity"}),
                                "role", PaintFamily.SOLID)
    assert (paint.fill, paint.stroke, paint.stroke_width, paint.dash, paint.opacity) == ("#112233", "#445566", 1.5, (2.0, 3.0), 0.4)


def test_resolver_requires_a_width_for_a_stroke_path():
    with pytest.raises(ScenePaintError) as error:
        resolve_scene_paint(_tokens({"stroke": "stroke", "opacity": "opacity"}), "role", PaintFamily.PATH)
    assert (error.value.diagnostic_id, error.value.path) == ("E_THEME_ROLE_REQUIRED", "/body/roles/role/strokeWidth")


def test_resolver_rejects_a_dash_without_a_stroke():
    with pytest.raises(ScenePaintError) as error:
        resolve_scene_paint(_tokens({"fill": "fill", "dash": "dash", "opacity": "opacity"}), "role", PaintFamily.SOLID)
    assert error.value.diagnostic_id == "E_PRESENTATION_PAINT_INVALID"


def test_resolver_completes_absent_opacity_before_adapter_invocation():
    paint = resolve_scene_paint(_tokens({"fill": "fill"}), "role", PaintFamily.TEXT)
    assert paint.opacity == 1.0


def test_resolver_completes_bounded_gradient_shadow_and_stroke_finish():
    values = {"fill": {"type": "color", "value": "#112233"}, "start": {"type": "color", "value": "#112233"}, "end": {"type": "color", "value": "#445566"}, "shadow": {"type": "color", "value": "#000000"}, "angle": {"type": "number", "value": 45}, "x": {"type": "number", "value": 1}, "y": {"type": "number", "value": 2}, "blur": {"type": "number", "value": 3}, "alpha": {"type": "number", "value": 0.4}, "cap": {"type": "lineCap", "value": "round"}, "join": {"type": "lineJoin", "value": "bevel"}}
    role = {"fill": "fill", "gradientStart": "start", "gradientEnd": "end", "shadowColor": "shadow", "gradientAngle": "angle", "shadowOffsetX": "x", "shadowOffsetY": "y", "shadowBlur": "blur", "shadowOpacity": "alpha", "strokeLineCap": "cap", "strokeLineJoin": "join"}
    paint = resolve_scene_paint(_tokens(role, values), "role", PaintFamily.SOLID, gradient_bounds=(0, 0, 10, 10))
    assert paint.gradient and paint.gradient.start == (0, 0)
    assert paint.shadow and paint.shadow.blur == 3
    assert paint.stroke_finish and paint.stroke_finish.line_cap == "round"


def test_baseline_omits_decorative_optional_treatment_during_scene_completion():
    values = {
        "fill": {"type": "color", "value": "#112233"}, "start": {"type": "color", "value": "#112233"},
        "end": {"type": "color", "value": "#445566"}, "angle": {"type": "number", "value": 45},
        "fidelity": {"type": "fidelity", "value": "decorative-optional"},
    }
    role = {"fill": "fill", "gradientStart": "start", "gradientEnd": "end", "gradientAngle": "angle",
            "gradientFidelity": "fidelity"}
    paint = resolve_scene_paint(_tokens(role, values), "role", PaintFamily.SOLID,
                                visual_capabilities=frozenset(), optional_omission=True,
                                gradient_bounds=(0, 0, 10, 10))
    assert paint.gradient is None


@pytest.mark.parametrize(("role", "values", "bounds", "code", "path", "detail"), [
    ({"fill": "fill", "gradientStart": "start"},
     {"fill": {"type": "color", "value": "#112233"}, "start": {"type": "color", "value": "#445566"}},
     None, "E_VISUAL_CAPABILITY_VALUE", "/body/roles/role/gradientAngle", "declared together"),
    ({"fill": "fill", "gradientStart": "start", "gradientEnd": "end", "gradientAngle": "angle", "gradientFidelity": "fidelity"},
     {"fill": {"type": "color", "value": "#112233"}, "start": {"type": "color", "value": "#112233"}, "end": {"type": "color", "value": "#445566"}, "angle": {"type": "number", "value": 45}, "fidelity": {"type": "fidelity", "value": "lossy"}},
     (0, 0, 10, 10), "E_VISUAL_CAPABILITY_FIDELITY", "/body/roles/role/gradientFidelity", "lossy"),
    ({"fill": "fill", "gradientStart": "start", "gradientEnd": "end", "gradientAngle": "angle"},
     {"fill": {"type": "color", "value": "#112233"}, "start": {"type": "color", "value": "#112233"}, "end": {"type": "color", "value": "#445566"}, "angle": {"type": "number", "value": 360}},
     (0, 0, 10, 10), "E_VISUAL_CAPABILITY_LIMIT", "/body/roles/role/gradientAngle", "360"),
])
def test_visual_capability_diagnostics_include_the_path_and_actionable_detail(role, values, bounds, code, path, detail):
    with pytest.raises(ScenePaintError) as error:
        resolve_scene_paint(_tokens(role, values), "role", PaintFamily.SOLID, gradient_bounds=bounds)
    assert (error.value.diagnostic_id, error.value.path) == (code, path)
    assert error.value.detail is not None and detail in error.value.detail and error.value.detail != code


@pytest.mark.parametrize(("property_name", "value", "detail"), [
    ("shadowBlur", 65, "exceeds 64"),
    ("shadowOpacity", 1.1, "[0, 1]"),
])
def test_visual_capability_shadow_limits_name_the_value_and_bound(property_name, value, detail):
    values = {
        "fill": {"type": "color", "value": "#112233"}, "shadow": {"type": "color", "value": "#000000"},
        "x": {"type": "number", "value": 1}, "y": {"type": "number", "value": 2},
        "blur": {"type": "number", "value": 3}, "opacity": {"type": "number", "value": 0.4},
    }
    values["blur" if property_name == "shadowBlur" else "opacity"]["value"] = value
    role = {"fill": "fill", "shadowColor": "shadow", "shadowOffsetX": "x", "shadowOffsetY": "y",
            "shadowBlur": "blur", "shadowOpacity": "opacity"}
    with pytest.raises(ScenePaintError) as error:
        resolve_scene_paint(_tokens(role, values), "role", PaintFamily.SOLID)
    assert (error.value.diagnostic_id, error.value.path) == ("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/role/{property_name}")
    assert error.value.detail is not None and str(value) in error.value.detail and detail in error.value.detail
