"""Whole-batch target capability admission for Layout frame glyphs (#888)."""
from __future__ import annotations

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.paint import ScenePaintError, resolve_artwork_admission
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, SVG_PROFILE, resolve_visual_profile,
)


def _tokens(*, fidelity: str | None = None, role_name: str = "frame-glyph") -> ThemeTokenView:
    values = {}
    role = {}
    if fidelity is not None:
        values["fidelity"] = {"type": "fidelity", "value": fidelity}
        role["artworkFidelity"] = "fidelity"
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": {role_name: role}, "metrics": {}}})


def _profile(identifier: str):
    return resolve_visual_profile(identifier, "svg")


def test_required_stroke_finish_fails_at_frame_glyph_role_pointer():
    with pytest.raises(ScenePaintError) as error:
        resolve_artwork_admission(_tokens(), needs_finish=True,
                                  visual_profile=_profile(BASELINE_PROFILE), role="frame-glyph")
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_UNSUPPORTED", "/body/roles/frame-glyph/artworkFidelity")


def test_decorative_optional_stroke_finish_omits_the_whole_frame_glyph_batch():
    result = resolve_artwork_admission(_tokens(fidelity="decorative-optional"), needs_finish=True,
                                       visual_profile=_profile(BASELINE_PROFILE), role="frame-glyph",
                                       treatment="frame-glyph")
    assert not result.admitted
    assert len(result.omissions) == 1
    omission = result.omissions[0]
    assert (omission.role, omission.treatment, omission.source_ref) == (
        "frame-glyph", "frame-glyph", "/body/roles/frame-glyph/artworkFidelity")
    assert omission.scene_diagnostic() == (
        f"I_VISUAL_TREATMENT_OMITTED:role=frame-glyph;treatment=frame-glyph;"
        f"profile={BASELINE_PROFILE};paintable={SVG_PROFILE}")


def test_rich_profile_admits_stroke_and_pure_fill_needs_no_finish_capability():
    rich = resolve_artwork_admission(_tokens(), needs_finish=True,
                                     visual_profile=_profile(SVG_PROFILE), role="frame-glyph",
                                     treatment="frame-glyph")
    fill_only = resolve_artwork_admission(_tokens(), needs_finish=False,
                                          visual_profile=_profile(BASELINE_PROFILE), role="frame-glyph",
                                          treatment="frame-glyph")
    assert rich.admitted and not rich.omissions
    assert fill_only.admitted and not fill_only.omissions


def test_default_annotation_artwork_omission_identity_is_unchanged():
    result = resolve_artwork_admission(_tokens(fidelity="decorative-optional", role_name="annotation-artwork"), needs_finish=True,
                                       visual_profile=_profile(BASELINE_PROFILE))
    assert not result.admitted
    assert result.omissions[0].treatment == "annotation-artwork"
    assert result.omissions[0].scene_diagnostic().startswith(
        "I_VISUAL_TREATMENT_OMITTED:role=annotation-artwork;treatment=annotation-artwork;")
