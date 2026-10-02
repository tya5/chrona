"""A Theme-declared glow completes into a canvas-clipped halo and follows the #478 ladder (#587).

Synthetic Themes only: nothing here reads `examples/`.
"""
from __future__ import annotations

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.capabilities import (
    capability_ceiling, theme_role_property_consumer,
)
from chrona.presentation.scene.model import ScenePrimitive
from chrona.presentation.scene.paint import PaintFamily, ScenePaintError, resolve_scene_paint
from chrona.presentation.scene.v05_builder import _visible_extent
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, SVG_PROFILE, resolve_visual_profile,
)

CANVAS = (0.0, 0.0, 400.0, 300.0)
EXTENT = (100.0, 100.0, 20.0, 10.0)
GLOW = {"glowColor": "gold", "glowBlur": "blur", "glowOpacity": "strength"}


def _tokens(**role) -> ThemeTokenView:
    values = {"ink": {"type": "color", "value": "#102030"}, "gold": {"type": "color", "value": "#FFD24A"},
              "blur": {"type": "number", "value": 6}, "strength": {"type": "number", "value": 0.8},
              "huge": {"type": "number", "value": 65}, "zero": {"type": "number", "value": 0},
              "over": {"type": "number", "value": 1.5}, "must": {"type": "fidelity", "value": "required"},
              "soft": {"type": "fidelity", "value": "decorative-optional"},
              "odd": {"type": "fidelity", "value": "sometimes"},
              "offset": {"type": "number", "value": 2}}
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": values, "roles": {"planned": {"fill": "ink", **role}}, "metrics": {}}})


def _resolve(tokens: ThemeTokenView, profile=None, extent=EXTENT, canvas=CANVAS):
    return resolve_scene_paint(tokens, "planned", PaintFamily.SOLID, visual_profile=profile,
                               glow_extent=extent, canvas_bounds=canvas)


def test_a_role_without_glow_properties_has_no_glow_and_no_omission() -> None:
    result = _resolve(_tokens())

    assert result.paint.glow is None and result.omissions == ()


def test_a_declared_glow_is_the_extent_grown_by_three_blur() -> None:
    glow = _resolve(_tokens(**GLOW)).paint.glow

    assert (glow.color, glow.blur, glow.opacity, glow.fidelity) == ("#FFD24A", 6.0, 0.8, "required")
    assert glow.region == (82.0, 82.0, 56.0, 46.0)


def test_the_region_never_leaves_the_canvas() -> None:
    glow = _resolve(_tokens(**GLOW), extent=(390.0, 5.0, 8.0, 8.0)).paint.glow

    assert glow.region == (372.0, 0.0, 28.0, 31.0)


def test_the_glow_changes_neither_the_other_channels_nor_the_extent() -> None:
    paint = _resolve(_tokens(**GLOW)).paint

    assert (paint.fill, paint.shadow, paint.gradient) == ("#102030", None, None)


@pytest.mark.parametrize("missing", ["glowColor", "glowBlur", "glowOpacity"])
def test_colour_blur_and_opacity_are_declared_together(missing) -> None:
    role = {key: value for key, value in GLOW.items() if key != missing}
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**role))

    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_VALUE", "/body/roles/planned/glowBlur")


@pytest.mark.parametrize(("blur", "opacity", "pointer"), [
    ("zero", "strength", "glowBlur"), ("huge", "strength", "glowBlur"), ("blur", "over", "glowOpacity")])
def test_blur_and_opacity_have_finite_limits(blur, opacity, pointer) -> None:
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(glowColor="gold", glowBlur=blur, glowOpacity=opacity))

    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/planned/{pointer}")


def test_an_unknown_fidelity_is_refused() -> None:
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**GLOW, glowFidelity="odd"))

    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_FIDELITY"


def test_a_role_cannot_declare_a_shadow_and_a_glow() -> None:
    shadow = {"shadowColor": "gold", "shadowOffsetX": "offset", "shadowOffsetY": "offset",
              "shadowBlur": "blur", "shadowOpacity": "strength"}
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**GLOW, **shadow))

    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_VALUE", "/body/roles/planned/glowBlur")


def test_the_rich_svg_profile_paints_the_glow() -> None:
    result = _resolve(_tokens(**GLOW), resolve_visual_profile(SVG_PROFILE, "svg"))

    assert result.paint.glow is not None and result.omissions == ()


def test_a_decorative_optional_glow_is_omitted_under_the_baseline_and_names_the_painting_profile() -> None:
    result = _resolve(_tokens(**GLOW, glowFidelity="soft"), resolve_visual_profile(BASELINE_PROFILE, "svg"))

    assert result.paint.glow is None
    (omission,) = result.omissions
    assert (omission.role, omission.treatment, omission.visual_profile, omission.paintable_profile) == (
        "planned", "glow", BASELINE_PROFILE, SVG_PROFILE)
    assert omission.source_ref == "/body/roles/planned/glowBlur"
    assert omission.scene_diagnostic() == (
        f"I_VISUAL_TREATMENT_OMITTED:role=planned;treatment=glow;profile={BASELINE_PROFILE};paintable={SVG_PROFILE}")


def test_a_required_glow_fails_before_serialization_under_the_baseline() -> None:
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**GLOW, glowFidelity="must"), resolve_visual_profile(BASELINE_PROFILE, "svg"))

    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_UNSUPPORTED", "/body/roles/planned/glowBlur")


def test_png_baseline_suggests_the_png_profile() -> None:
    result = _resolve(_tokens(**GLOW, glowFidelity="soft"), resolve_visual_profile(BASELINE_PROFILE, "png"))

    assert result.omissions[0].paintable_profile.endswith("v0.6-png")


@pytest.mark.parametrize("role", ["planned", "milestone", "axis-major", "dependency", "annotation",
                                  "variance-ahead", "member-label-inside-planned"])
def test_glow_is_admitted_where_a_shadow_is(role) -> None:
    for name in ("glowColor", "glowBlur", "glowOpacity", "glowFidelity"):
        assert theme_role_property_consumer(role, name) == theme_role_property_consumer(role, "shadowBlur") is not None


@pytest.mark.parametrize("role", ["background", "text", "icon-mark", "heading", "legend-swatch"])
def test_glow_is_not_admitted_on_canvas_icon_shared_text_or_measurement_roles(role) -> None:
    assert theme_role_property_consumer(role, "glowBlur") is None


def test_the_capability_is_admitted_in_the_closed_ceiling() -> None:
    assert [item.identifier for item in capability_ceiling()].count("effect.glow") == 1


def test_a_paths_extent_is_the_box_of_its_points() -> None:
    path = ScenePrimitive("p", "Path", "r", "relation", "dependency", "dependency", (0, 0, 0, 0),
                          points=((10.0, 40.0), (50.0, 20.0)))
    rect = ScenePrimitive("r", "Rect", "r", "object", "planned", "planned", (1.0, 2.0, 3.0, 4.0))

    assert _visible_extent(path) == (10.0, 20.0, 40.0, 20.0)
    assert _visible_extent(rect) == (1.0, 2.0, 3.0, 4.0)


def _surface(fidelity: str):
    from chrona.presentation.scene.model import Glow, ScenePaint, SceneSurface

    glow = Glow("#FFD24A", 6.0, 0.8, fidelity, (0.0, 0.0, 10.0, 10.0))
    paint = ScenePaint("#102030", None, None, (), 1.0, glow=glow)
    primitive = ScenePrimitive("m", "Rect", "m", "object", "planned", "planned", (1.0, 1.0, 5.0, 5.0), paint=paint)
    return SceneSurface("s", (), (), (), None, (primitive,), canvas_paint=ScenePaint("#FFFFFF", None, None, (), 1.0))


def test_a_completed_glow_is_checked_against_the_profile_before_an_adapter_sees_it() -> None:
    from chrona.presentation.scene.visual_capabilities import VisualCapabilityError, validate_surface_visual_profile

    validate_surface_visual_profile(_surface("required"), resolve_visual_profile(SVG_PROFILE, "svg"))
    with pytest.raises(VisualCapabilityError) as error:
        validate_surface_visual_profile(_surface("required"), resolve_visual_profile(BASELINE_PROFILE, "svg"))
    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED"
