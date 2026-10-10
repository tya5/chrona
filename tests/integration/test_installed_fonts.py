"""Installed fonts on every render path, with a font stack and per-character coverage (#1281).

An injected font directory (renamed copies of the packaged faces, and the optional Noto Sans JP) stands in for the
machine's fonts: no test depends on the host's. The Render Context path and the draft path share one resolver, which
the first test exercises directly with the packaged descriptor.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fontTools.ttLib import TTFont
import pytest

from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.presentation.fonts.resolution import resolve_theme_font_stacks
from chrona.resources import safe_load
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

ROOT = Path(__file__).resolve().parents[2]
PACKAGED = ROOT / "src/chrona/resources/fonts"
CJK_FONTS = ROOT / "packages/chrona-fonts-noto-cjk/src/chrona_fonts_noto_cjk/fonts"
STACK = "Hiragino Sans, Yu Gothic, Noto Sans JP"
needs_cjk = pytest.mark.skipif(not tt.cjk_available(), reason="requires the optional chrona-fonts-noto-cjk package")


def renamed(target: Path, source: Path, family: str, weight: int) -> Path:
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    font = TTFont(source)
    names = font["name"]
    for item in (1, 2, 4, 6, 16, 17):
        names.removeNames(nameID=item)
    names.setName(family, 1, 3, 1, 0x409)
    names.setName(family, 16, 3, 1, 0x409)
    font["OS/2"].usWeightClass = weight
    font.save(target)
    return target


def _parts(family: str = STACK, *, role: str = "groupHeader") -> dict:
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body["values"]["stack.family"] = {"type": "fontFamily", "value": family}
    body["roles"][role]["fontFamily"] = "stack.family"
    return parts


def _source(title: str = "Imaging Team"):
    source = sr.bunched_project(groups=2, per_group=2)
    for group in ("team-0", "team-1"):
        source["entities"][group]["title"] = title
    return source


def _render(tmp_path, parts, title="Imaging Team"):
    return sr.render(tmp_path, _source(title), presentation=parts)


def _header(rendered):
    return next(item for item in rendered.surface.primitives if item.scene_id == "group-header:team-0")


def _notes(rendered, prefix):
    return [item for item in rendered.scene.diagnostics if item.startswith(prefix)]


def test_the_first_installed_family_of_the_stack_is_used_and_the_scene_records_it(tmp_path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    renamed(fonts / "h.ttf", PACKAGED / "noto-sans-regular-v1.ttf", "Hiragino Sans", 400)
    renamed(fonts / "y.ttf", PACKAGED / "noto-sans-regular-v1.ttf", "Yu Gothic", 400)
    (tmp_path / "run").mkdir()
    with use_installed_fonts(InstalledFontIndex([fonts])):
        rendered = _render(tmp_path / "run", _parts())

    assert _header(rendered).text_layout.family == "Hiragino Sans"
    assert any("role=groupHeader" in item and "face=Hiragino Sans" in item and STACK in item
               for item in _notes(rendered, "I_FONT_ROLE_RESOLVED"))
    assert not _notes(rendered, "W_FONT_FALLBACK_PACKAGED")


def test_a_later_family_is_used_when_the_earlier_ones_are_not_installed(tmp_path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    renamed(fonts / "y.ttf", PACKAGED / "noto-sans-regular-v1.ttf", "Yu Gothic", 400)
    (tmp_path / "run").mkdir()
    with use_installed_fonts(InstalledFontIndex([fonts])):
        rendered = _render(tmp_path / "run", _parts())

    assert _header(rendered).text_layout.family == "Yu Gothic"


def test_with_none_of_the_listed_families_the_role_falls_back_to_packaged_noto_sans_with_a_warning(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (tmp_path / "run").mkdir()
    with use_installed_fonts(InstalledFontIndex([empty])):
        rendered = _render(tmp_path / "run", _parts())

    assert _header(rendered).text_layout.family == "Noto Sans"
    warnings = _notes(rendered, "W_FONT_FALLBACK_PACKAGED")
    assert any("role=groupHeader" in item and STACK in item and "face=Noto Sans" in item for item in warnings)


def test_a_declared_single_face_keeps_its_exact_metrics_and_reports_nothing(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (tmp_path / "run").mkdir()
    with use_installed_fonts(InstalledFontIndex([empty])):
        rendered = _render(tmp_path / "run", sr.bundle("executive-light"))

    assert not _notes(rendered, "I_FONT_ROLE_RESOLVED") and not _notes(rendered, "W_FONT_FALLBACK_PACKAGED")


def test_the_resolver_is_shared_by_the_context_path_and_leaves_fully_declared_themes_alone(tmp_path):
    descriptor = safe_load((PACKAGED / "default-font-metrics.yaml").read_bytes())

    def resolved(parts):
        return resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:test")

    declared_only = resolve_theme_font_stacks(resolved(sr.bundle("executive-light")), descriptor, asset_root=PACKAGED,
                                              installed=InstalledFontIndex([]))
    stacked = resolve_theme_font_stacks(resolved(_parts()), descriptor, asset_root=PACKAGED,
                                        installed=InstalledFontIndex([]))

    assert declared_only is None
    assert stacked is not None and any(item.startswith("W_FONT_FALLBACK_PACKAGED") for item in stacked.notes)
    assert {item.family for item in stacked.font_files} >= {"Noto Sans"}


@needs_cjk
def test_a_character_the_first_face_lacks_takes_the_next_face_that_has_it(tmp_path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    renamed(fonts / "h.ttf", PACKAGED / "noto-sans-regular-v1.ttf", "Hiragino Sans", 400)  # Latin only
    for name in ("noto-sans-jp-regular-v1.ttf", "noto-sans-jp-bold-v1.ttf"):
        (fonts / name).write_bytes((CJK_FONTS / name).read_bytes())
    (tmp_path / "run").mkdir()
    with use_installed_fonts(InstalledFontIndex([fonts])):
        rendered = _render(tmp_path / "run", _parts(), title="日本語 Team")
    layout = _header(rendered).text_layout

    assert layout.family == "Hiragino Sans"
    assert layout.bounds[2] > 0


def test_text_no_face_of_the_stack_or_the_package_covers_fails_naming_the_character(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (tmp_path / "run").mkdir()
    with use_installed_fonts(InstalledFontIndex([empty])):
        with pytest.raises(Exception) as caught:
            _render(tmp_path / "run", _parts(), title="日本語")

    message = str(caught.value) + repr(getattr(caught.value, "detail", ""))
    assert "E_FONT_GLYPH_UNAVAILABLE" in message and "U+65E5" in message and "Noto Sans" in message


def test_the_system_font_restriction_to_svg_and_png_is_gone(tmp_path):
    from chrona.presentation.model.closure import resolve_draft_render

    parts = _parts()
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    for target in ("pdf",):
        draft = resolve_draft_render(
            project_path=sr._write(tmp_path / f"project-{target}.yaml", _source()), view_path=paths["view"],
            theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"], target_kind=target)
        assert draft.closure.context.target.kind == target
