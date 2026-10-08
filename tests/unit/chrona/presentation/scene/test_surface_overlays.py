from decimal import Decimal

import pytest

from chrona.presentation.layout.canvas_overlays import complete_canvas_overlays
from chrona.presentation.layout.model import Rect
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface
from chrona.presentation.scene.paint import (
    PaintFamily, ScenePaintError, resolve_scene_paint, resolve_surface_pattern_admission,
)
from chrona.presentation.scene.surface_overlays import project_canvas_overlays
from chrona.presentation.scene.v05_builder import _complete_surface_paint
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, PNG_PROFILE, SVG_ICON_PROFILE, SVG_PROFILE, resolve_visual_profile,
    validate_surface_visual_profile,
)


def _tokens(*, fidelity="required", radial=True, pattern=True):
    values = {
        "background": {"type": "color", "value": "#ffffff"},
        "ink": {"type": "color", "value": "#102030"},
        "alpha": {"type": "number", "value": 0.25},
        "fidelity": {"type": "fidelity", "value": fidelity},
        "pattern": {"type": "pattern", "value": {
            "kind": "seeded", "algorithm": "splitmix64-v1", "motif": "grain", "seed": 7,
            "tile": {"inlineSize": 32, "blockSize": 32}, "count": 2, "radius": 0.5}},
    }
    roles = {"background": {"fill": "background"}, "planned": {"fill": "ink"}}
    if pattern:
        roles["canvas-overlay"] = {"pattern": "pattern", "stroke": "ink", "opacity": "alpha",
                                    "textureFidelity": "fidelity"}
    if radial:
        role = {"fill": "ink", "opacity": "alpha", "gradientFidelity": "fidelity"}
        for name, value in {
            "radialCenterInline": 0.5, "radialCenterBlock": 0.45, "radialRadiusInline": 0.75,
            "radialRadiusBlock": 0.8, "radialInnerStop": 0.55,
        }.items():
            values[name] = {"type": "number", "value": value}
            role[name] = name
        roles["canvas-overlay-gradient"] = role
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": roles, "metrics": {}}})


def _surface():
    content = ScenePrimitive("content", "Rect", "object", "object", "planned", "planned",
                             (10, 20, 50, 30), paint_order=900)
    return SceneSurface("table-timeline", (), (), (), None, (content,),
                        canvas_bounds=(-8, 4, 160, 90))


@pytest.mark.parametrize("profile_id,target", [(SVG_PROFILE, "svg"), (PNG_PROFILE, "png"),
                                                (SVG_ICON_PROFILE, "svg")])
def test_projection_copies_layout_geometry_and_places_radial_then_ink_after_content(profile_id, target):
    tokens = _tokens()
    placements = complete_canvas_overlays(tokens, Rect(Decimal(-8), Decimal(4), Decimal(160), Decimal(90)))
    profile = resolve_visual_profile(profile_id, target)
    projected = project_canvas_overlays(_surface(), placements, tokens, profile)
    surface = _complete_surface_paint(projected, tokens, profile, (160, 90))
    assert [item.scene_id for item in surface.primitives] == [
        "content", "canvas-overlay-gradient", "canvas-overlay"]
    assert [item.paint_order for item in surface.primitives] == [900, 901, 902]
    radial, sparse = surface.primitives[1:]
    assert radial.bounds == sparse.bounds == (-8, 4, 160, 90)
    assert radial.paint.radial_gradient.center == (72, 44.5)
    assert radial.paint.radial_gradient.radii == (120, 72)
    assert [(s.offset, s.color, s.opacity) for s in radial.paint.radial_gradient.stops] == [
        (0, "#102030", 0), (0.55, "#102030", 0), (1, "#102030", 1)]
    assert radial.paint.opacity == sparse.paint.opacity == 0.25
    assert sparse.paint.fill is None and sparse.paint.stroke == "#102030"
    assert sparse.pattern.origin == (-8, 4)
    assert surface.primitives[0].bounds == _surface().primitives[0].bounds
    validate_surface_visual_profile(surface, profile)


def test_absent_overlays_return_the_same_completed_surface():
    surface = _surface()
    tokens = _tokens(radial=False, pattern=False)
    assert project_canvas_overlays(surface, None, tokens, None) is surface
    placements = complete_canvas_overlays(tokens, Rect(Decimal(0), Decimal(0), Decimal(160), Decimal(90)))
    assert project_canvas_overlays(surface, placements, tokens, None) is surface


def test_baseline_omits_optional_radial_whole_without_flat_ink_replacement():
    tokens = _tokens(fidelity="decorative-optional", pattern=False)
    placements = complete_canvas_overlays(tokens, Rect(Decimal(0), Decimal(0), Decimal(160), Decimal(90)))
    surface = project_canvas_overlays(_surface(), placements, tokens, resolve_visual_profile(BASELINE_PROFILE, "svg"))
    assert surface.primitives == _surface().primitives
    assert len(surface.info_diagnostics) == 1
    assert surface.info_diagnostics[0].treatment == "canvas-overlay-gradient"


def test_baseline_required_radial_fails_at_its_fidelity_binding():
    tokens = _tokens(pattern=False)
    placements = complete_canvas_overlays(tokens, Rect(Decimal(0), Decimal(0), Decimal(160), Decimal(90)))
    with pytest.raises(ScenePaintError) as error:
        project_canvas_overlays(_surface(), placements, tokens, resolve_visual_profile(BASELINE_PROFILE, "svg"))
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_UNSUPPORTED", "/body/roles/canvas-overlay-gradient/gradientFidelity")


@pytest.mark.parametrize("target", ["typst", "tikz", "pdf"])
def test_transparent_patterns_omit_whole_or_fail_before_unsupported_adapter(target):
    profile = resolve_visual_profile(BASELINE_PROFILE, target)
    optional = resolve_surface_pattern_admission(_tokens(fidelity="decorative-optional"), "canvas-overlay",
                                                 visual_profile=profile)
    assert not optional.admitted and optional.omissions[0].treatment == "canvas-overlay"
    with pytest.raises(ScenePaintError) as error:
        resolve_surface_pattern_admission(_tokens(), "canvas-overlay", visual_profile=profile)
    assert error.value.path == "/body/roles/canvas-overlay/textureFidelity"


def test_ink_only_pattern_paint_never_invents_a_substrate_and_legacy_stays_strict():
    tokens = _tokens(radial=False)
    paint = resolve_scene_paint(tokens, "canvas-overlay", PaintFamily.SOLID,
                                catalog_pattern=True, ink_only_pattern=True).paint
    assert paint == ScenePaint(None, "#102030", None, (), 0.25)
    with pytest.raises(ScenePaintError) as error:
        resolve_scene_paint(tokens, "canvas-overlay", PaintFamily.SOLID, catalog_pattern=True)
    assert error.value.path == "/body/roles/canvas-overlay/fill"
