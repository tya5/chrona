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
