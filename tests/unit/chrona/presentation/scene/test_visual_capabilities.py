from datetime import date

import pytest

from chrona.presentation.scene.model import LinearGradient, ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE,
    PNG_PROFILE,
    SVG_PROFILE,
    SVG_ICON_PROFILE,
    VisualCapabilityError,
    resolve_visual_profile,
    validate_surface_visual_profile,
)


def _surface() -> SceneSurface:
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 1, 0, 1)
    paint = ScenePaint("#111111", None, None, (), 1, LinearGradient((0, 0), (1, 0), ((0, "#111111"), (1, "#222222")), "required"))
    return SceneSurface("s", (), (), (), scale, (ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (0, 0, 1, 1), paint=paint,
                                                                   visual_capability_source_ref="/body/roles/planned/gradientAngle"),), ScenePaint("#fff", None, None, (), 1))


def test_rich_profiles_are_exact_target_contracts():
    assert resolve_visual_profile(SVG_PROFILE, "svg").capabilities
    assert resolve_visual_profile(PNG_PROFILE, "png").capabilities
    with pytest.raises(VisualCapabilityError, match="E_VISUAL_CAPABILITY_PROFILE"):
        resolve_visual_profile(SVG_PROFILE, "pdf")


def test_required_completed_treatment_is_rejected_by_baseline_before_adapter():
    with pytest.raises(VisualCapabilityError, match="E_VISUAL_CAPABILITY_UNSUPPORTED") as error:
        validate_surface_visual_profile(_surface(), resolve_visual_profile(BASELINE_PROFILE, "svg"))
    assert error.value.path == "/body/roles/planned/gradientAngle"
    assert error.value.message != error.value.diagnostic_id


def test_icon_requires_exact_v07_profile_before_adapter():
    icon = ScenePrimitive("i", "Icon", "risk", "object", "icon-mark", "planned", (0, 0, 1, 1),
                          paint=ScenePaint("#111111", None, None, (), 1), icon_kind="vector",
                          icon_asset_identity="sha256:" + "a" * 64,
                          visual_capability_source_ref="/body/iconBindings/0")
    surface = SceneSurface("s", (), (), (), None, (icon,), ScenePaint("#fff", None, None, (), 1))
    with pytest.raises(VisualCapabilityError, match="E_VISUAL_CAPABILITY_UNSUPPORTED") as error:
        validate_surface_visual_profile(surface, resolve_visual_profile(BASELINE_PROFILE, "svg"))
    assert error.value.path == "/body/iconBindings/0"
    assert "icon.vector" in error.value.message
    validate_surface_visual_profile(surface, resolve_visual_profile(SVG_ICON_PROFILE, "svg"))
