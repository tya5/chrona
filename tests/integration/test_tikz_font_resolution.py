"""TikZ names the font by file, following the Theme family list like SVG and draft measurement (#1553).

The three outcomes are driven through the render use case with an injected installed-font index; no test reads the
host's fonts. The opt-in compile test needs CHRONA_TECTONIC (the typesetter-compile workflow).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.render_review import RenderFailed
from tests.support import text_treatments as tt
from tests.support import synthetic_review as sr
from tests.support import typeset_compile as tc

HALCYON = Path(__file__).resolve().parents[2] / "examples" / "halcyon-1"
NO_FONTS = InstalledFontIndex((), files=())
needs_cjk = pytest.mark.skipif(not tt.cjk_available(), reason="requires the chrona-fonts-noto-cjk package")


def _tikz(preset: str = "yuya", *, project: Path | None = None) -> str:
    rendered = render_draft(DraftRenderRequest(
        project=project or HALCYON / "project.yaml",
        actual=HALCYON / "actual.yaml" if project is None else None,
        target_kind="tikz", preset=preset,
        visual_profile="chrona-output/visual/v0.5-baseline", typesetter_engine="tectonic", typesetter_version="0.17.0",
        typesetter_adapter_grammar="chrona-tikz/v0.1"))
    return rendered.artifact.content.decode("utf-8")


def _neutral_japanese_project(tmp_path: Path) -> Path:
    """Use Japanese text with no annotations, keeping font-resolution tests out of artwork policy."""
    source = sr.project({"work": sr.span("work", date(2026, 1, 5), 5, title="日本語の計画")})
    source["project"]["title"] = "日本語のプロジェクト"
    project = tmp_path / "project.yaml"
    project.write_text(yaml.safe_dump(source, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return project


@needs_cjk
def test_with_the_provider_the_packaged_cjk_face_is_named_by_file(tmp_path):
    project = _neutral_japanese_project(tmp_path)
    with use_installed_fonts(NO_FONTS):
        source = _tikz(project=project)
    assert "noto-sans-jp-regular-v1.ttf}" in source and "noto-sans-jp-bold-v1.ttf}" in source
    assert "{Noto Sans JP}" not in source


@needs_cjk
def test_without_the_provider_the_next_installed_family_is_named_by_file(tmp_path, monkeypatch):
    from chrona.presentation.model import font_resources
    from tests.integration.test_installed_fonts import CJK_FONTS, renamed

    monkeypatch.setattr(font_resources, "entry_points", lambda **_kwargs: ())
    project = _neutral_japanese_project(tmp_path)
    for weight, name in ((400, "regular"), (700, "bold")):
        renamed(tmp_path / f"hira{weight}.ttf", CJK_FONTS / f"noto-sans-jp-{name}-v1.ttf", "Hiragino Sans", weight)
    with use_installed_fonts(InstalledFontIndex([tmp_path])):
        source = _tikz(project=project)
    assert f"Path=\\detokenize{{{tmp_path.as_posix()}/}}" in source and "{hira400.ttf}" in source
    assert "noto-sans-jp" not in source


def test_default_preset_names_the_packaged_face_by_file():
    with use_installed_fonts(NO_FONTS):
        source = _tikz("editorial")
    assert "{noto-sans-regular-v1.ttf}" in source and "{Noto Sans}" not in source


@needs_cjk
def test_compiled_yuya_slide_loads_the_noto_sans_jp_face(tmp_path):
    tc.engine("tikz")
    project = _neutral_japanese_project(tmp_path)
    with use_installed_fonts(NO_FONTS):
        source = _tikz(project=project)
    image, _compiled = tc.compile_to_image("tikz", source, tmp_path, "yuya", (1595, 861))
    assert image.getbbox() is not None


@needs_cjk
def test_yuya_tikz_still_refuses_required_halcyon_annotation_artwork():
    with use_installed_fonts(NO_FONTS), pytest.raises(RenderFailed) as caught:
        _tikz()
    assert caught.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"
    assert caught.value.source_ref == "/body/roles/annotation-artwork/artworkFidelity"
