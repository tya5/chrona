"""Shared CJK closure: Latin Theme, installed provider/OS faces, all preset targets."""
import pytest
from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.preset_library import list_builtin_presets
from chrona.usecases.table_import import import_table
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_installed_fonts import _parts, _render, _header, _source, renamed, CJK_FONTS
from tests.support.text_treatments import cjk_available

pytestmark = pytest.mark.skipif(not cjk_available(), reason="requires optional Noto CJK provider")


def test_declared_latin_face_closes_mixed_text_with_info_and_exact_runs(tmp_path):
    with use_installed_fonts(InstalledFontIndex([])):
        rendered = _render(tmp_path, _parts("Noto Sans"), title="要件 Team")
    runs = _header(rendered).text_layout.runs[0]
    assert [(run.text, run.family) for run in runs] == [("要件", "Noto Sans JP"), (" Team", "Noto Sans")]
    assert all(run.asset_identity.startswith("sha256:") for run in runs)
    assert not rendered.font_warnings
    assert any(item.code == "I_FONT_GLYPH_SUBSTITUTED" and item.fallback_family == "Noto Sans JP"
               for item in rendered.info_diagnostics)


def test_without_optional_provider_installed_cjk_faces_cover_missing_glyphs(tmp_path, monkeypatch):
    from chrona.presentation.model import font_resources
    from chrona.presentation.model.font_resources import FontProviderUnavailable
    original = font_resources._package_root
    def without_cjk(identity):
        if identity == "chrona-fonts-noto-cjk":
            raise FontProviderUnavailable(identity)
        return original(identity)
    monkeypatch.setattr(font_resources, "_package_root", without_cjk)
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    for weight, name in ((400, "regular"), (700, "bold")):
        renamed(fonts / f"cjk-{weight}.ttf", CJK_FONTS / f"noto-sans-jp-{name}-v1.ttf", "Hiragino Sans", weight)
    run = tmp_path / "run"
    run.mkdir()
    with use_installed_fonts(InstalledFontIndex([fonts])):
        rendered = _render(run, _parts("Noto Sans"), title="要件")
    assert _header(rendered).text_layout.runs[0][0].family == "Hiragino Sans"


@pytest.mark.parametrize("preset", [entry["id"] for entry in list_builtin_presets()])
@pytest.mark.parametrize("target", ["png", "svg", "pdf"])
def test_every_preset_renders_japanese_csv_import(tmp_path, preset, target):
    table = "id,title,type,start,end,actual_start,actual_finish\nrequirements,要件定義,task,2026-10-05,2026-10-10,2026-10-05,2026-10-09\n"
    imported = import_table(table, project_id="jp-import", title="開発計画", as_of="2026-10-12")
    assert imported.ok
    project, actual = tmp_path / "project.yaml", tmp_path / "actual.yaml"
    project.write_bytes(imported.project_yaml)
    actual.write_bytes(imported.actual_yaml)
    with use_installed_fonts(InstalledFontIndex([])):
        if preset == "marquee" and target == "pdf":
            # Existing required-glow refusal, independently reproduced on the
            # untouched Latin baseline. Acceptance disposition is still open.
            with pytest.raises(RenderFailed) as caught:
                render_draft(DraftRenderRequest(project=project, actual=actual, preset=preset, target_kind=target))
            assert caught.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"
            assert caught.value.source_ref == "/body/roles/kicker/glowBlur"
            return
        result = render_draft(DraftRenderRequest(project=project, actual=actual, preset=preset, target_kind=target))
    assert result.artifact.content.startswith({"png": b"\x89PNG", "pdf": b"%PDF", "svg": b"<svg"}[target])
    assert not any(item.get("code") == "W_FONT_GLYPH_SUBSTITUTED" for item in result.notes)
    for item in result.notes:
        if item["code"] == "I_FONT_GLYPH_SUBSTITUTED":
            assert item["severity"] == "info" and item["fallbackFamily"] == "Noto Sans JP"


def test_pdf_embeds_the_measured_japanese_fallback_program(tmp_path):
    from io import BytesIO
    from fontTools.ttLib import TTFont
    from pypdf import PdfReader
    from tests.support import synthetic_review as sr
    parts = _parts("Noto Sans")
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    project = sr._write(tmp_path / "project.yaml", _source("要件 Team"))
    with use_installed_fonts(InstalledFontIndex([])):
        result = render_draft(DraftRenderRequest(project=project, target_kind="pdf", **paths))
    reader = PdfReader(BytesIO(result.artifact.content))
    assert "要件" in reader.pages[0].extract_text()
    programs = []
    for font in reader.pages[0]["/Resources"]["/Font"].values():
        descriptor = font.get_object().get("/FontDescriptor")
        if descriptor is not None and "/FontFile2" in descriptor:
            program = TTFont(BytesIO(descriptor["/FontFile2"].get_data()))
            programs.extend(item.toUnicode() for item in program["name"].names if item.nameID == 1)
    assert any("Noto Sans JP" in name for name in programs)
