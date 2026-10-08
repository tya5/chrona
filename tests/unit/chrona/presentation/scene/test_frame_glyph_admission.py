"""Whole-batch target capability admission for Layout frame glyphs (#888)."""
from __future__ import annotations

import pytest
from types import SimpleNamespace

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.paint import (
    PaintFamily, ScenePaintError, resolve_artwork_admission, resolve_scene_paint,
)
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, PNG_PROFILE, SVG_PROFILE, resolve_visual_profile,
)
from chrona.presentation.model.semantic_registry import PrimitiveKind
from chrona.presentation.scene.v05_builder import _paint_family


def _tokens(*, fidelity: str | None = None, role_name: str = "frame-glyph") -> ThemeTokenView:
    values = {}
    role = {}
    if fidelity is not None:
        values["fidelity"] = {"type": "fidelity", "value": fidelity}
        role["artworkFidelity"] = "fidelity"
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": {role_name: role}, "metrics": {}}})


def _profile(identifier: str, target: str = "svg"):
    return resolve_visual_profile(identifier, target)


@pytest.mark.parametrize("mode,family", [("stroke", PaintFamily.PATH), ("fill", PaintFamily.SOLID)])
def test_builder_selects_the_completed_glyph_parts_used_channel(mode, family):
    primitive = SimpleNamespace(pattern=None, kind=PrimitiveKind.SYMBOL, purpose="frame-glyph",
                                visual_role="frame-glyph", glyph_paint_mode=mode)
    assert _paint_family(primitive, _tokens()) == family


def test_builder_keeps_explicit_outline_override_before_glyph_part_channel_selection():
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"outline": {"type": "pattern", "value": {"kind": "outline"}}},
                 "roles": {"ghost": {"pattern": "outline"}}, "metrics": {}},
    })
    primitive = SimpleNamespace(pattern=None, kind=PrimitiveKind.SYMBOL, purpose="planned",
                                visual_role="ghost", glyph_paint_mode="fill")
    assert _paint_family(primitive, tokens) == PaintFamily.OUTLINE


@pytest.mark.parametrize(("target", "profile_id"), [("svg", BASELINE_PROFILE), ("png", BASELINE_PROFILE)])
def test_required_stroke_finish_fails_at_frame_glyph_role_pointer(target, profile_id):
    with pytest.raises(ScenePaintError) as error:
        resolve_artwork_admission(_tokens(), needs_finish=True,
                                  visual_profile=_profile(profile_id, target), role="frame-glyph",
                                  treatment="frame-glyph")
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_UNSUPPORTED", "/body/roles/frame-glyph/artworkFidelity")


@pytest.mark.parametrize(("target", "profile_id", "rich_id"), [
    ("svg", BASELINE_PROFILE, SVG_PROFILE), ("png", BASELINE_PROFILE, PNG_PROFILE),
])
def test_decorative_optional_stroke_finish_omits_the_whole_frame_glyph_batch(target, profile_id, rich_id):
    result = resolve_artwork_admission(_tokens(fidelity="decorative-optional"), needs_finish=True,
                                       visual_profile=_profile(profile_id, target), role="frame-glyph",
                                       treatment="frame-glyph")
    assert not result.admitted
    assert len(result.omissions) == 1
    omission = result.omissions[0]
    assert (omission.role, omission.treatment, omission.source_ref) == (
        "frame-glyph", "frame-glyph", "/body/roles/frame-glyph/artworkFidelity")
    assert omission.scene_diagnostic() == (
        f"I_VISUAL_TREATMENT_OMITTED:role=frame-glyph;treatment=frame-glyph;"
        f"profile={profile_id};paintable={rich_id}")


@pytest.mark.parametrize(("target", "rich_id"), [("svg", SVG_PROFILE), ("png", PNG_PROFILE)])
def test_rich_profile_admits_stroke_and_pure_fill_needs_no_finish_capability(target, rich_id):
    rich = resolve_artwork_admission(_tokens(), needs_finish=True,
                                     visual_profile=_profile(rich_id, target), role="frame-glyph",
                                     treatment="frame-glyph")
    fill_only = resolve_artwork_admission(_tokens(), needs_finish=False,
                                          visual_profile=_profile(BASELINE_PROFILE, target), role="frame-glyph",
                                          treatment="frame-glyph")
    assert rich.admitted and not rich.omissions
    assert fill_only.admitted and not fill_only.omissions


def test_stroke_only_catalogue_part_resolves_on_path_from_catalogue_finish_without_role_fill():
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"stroke": {"type": "color", "value": "#123456"}},
                 "roles": {"frame-glyph": {"stroke": "stroke"}}, "metrics": {}},
    })
    paint = resolve_scene_paint(
        tokens, "frame-glyph", PaintFamily.PATH, part_mode="stroke", part_color="#ABCDEF",
        catalog_glyph_stroke_width=1.75, catalog_glyph_line_cap="round", catalog_glyph_line_join="bevel",
    ).paint
    assert paint.fill is None
    assert (paint.stroke, paint.stroke_width) == ("#ABCDEF", 1.75)
    assert paint.stroke_finish is not None
    assert (paint.stroke_finish.line_cap, paint.stroke_finish.line_join) == ("round", "bevel")


def test_pure_fill_catalogue_part_resolves_on_solid_without_role_stroke():
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"fill": {"type": "color", "value": "#123456"}},
                 "roles": {"frame-glyph": {"fill": "fill"}}, "metrics": {}},
    })
    paint = resolve_scene_paint(tokens, "frame-glyph", PaintFamily.SOLID,
                                part_mode="fill", part_color="#ABCDEF").paint
    assert (paint.fill, paint.stroke, paint.stroke_width) == ("#ABCDEF", None, None)


def test_default_annotation_artwork_omission_identity_is_unchanged():
    result = resolve_artwork_admission(_tokens(fidelity="decorative-optional", role_name="annotation-artwork"), needs_finish=True,
                                       visual_profile=_profile(BASELINE_PROFILE))
    assert not result.admitted
    assert result.omissions[0].treatment == "annotation-artwork"
    assert result.omissions[0].scene_diagnostic().startswith(
        "I_VISUAL_TREATMENT_OMITTED:role=annotation-artwork;treatment=annotation-artwork;")
