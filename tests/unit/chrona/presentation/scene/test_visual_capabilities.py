from datetime import date

import pytest

from chrona.presentation.scene.model import LinearGradient, ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE,
    RICH_PROFILE,
    VisualCapabilityError,
    resolve_visual_profile,
    validate_surface_visual_profile,
)


def _surface() -> SceneSurface:
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 1, 0, 1)
    paint = ScenePaint("#111111", None, None, (), 1, LinearGradient(0, ((0, "#111111"), (1, "#222222")), "required"))
    return SceneSurface("s", (), (), (), scale, (ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (0, 0, 1, 1), paint=paint),), ScenePaint("#fff", None, None, (), 1))


def test_rich_profile_is_limited_to_svg_route_and_svg_derivatives():
    assert resolve_visual_profile(RICH_PROFILE, "svg").capabilities
    with pytest.raises(VisualCapabilityError, match="E_VISUAL_CAPABILITY_PROFILE"):
        resolve_visual_profile(RICH_PROFILE, "typst")


def test_required_completed_treatment_is_rejected_by_baseline_before_adapter():
    with pytest.raises(VisualCapabilityError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
        validate_surface_visual_profile(_surface(), resolve_visual_profile(BASELINE_PROFILE, "svg"))
