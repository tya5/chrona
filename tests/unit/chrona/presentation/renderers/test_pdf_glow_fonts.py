"""Native, exact-face font aliases used only by the PDF glow raster pass."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
import pytest
import resvg_py

from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.pdf_fonts import (
    PDF_RASTER_FONT_GRAMMAR,
    PdfFontConversionError,
    pdf_raster_font_bytes,
)
from tests.support.cff_fonts import write_cff_collection, write_cff_font


ROOT = Path(__file__).resolve().parents[5]
LATIN = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
MONO = ROOT / "src/chrona/resources/fonts/noto-sans-mono-regular-v1.ttf"


def _item(path: Path, family: str = "Test Face", *, index: int = 0) -> FontFile:
    return FontFile(path, "sha256:" + sha256(path.read_bytes()).hexdigest(), family, 400, index)


def _renamed(item: FontFile, alias: str, path: Path) -> TTFont:
    path.write_bytes(pdf_raster_font_bytes(item, alias))
    return TTFont(path, recalcTimestamp=False)


def _outline(font: TTFont, codepoint: int):
    glyph_name = font.getBestCmap()[codepoint]
    pen = RecordingPen()
    font.getGlyphSet()[glyph_name].draw(pen)
    return tuple(pen.value)


def _raster(svg: str, fonts: list[Path]):
    from PIL import Image

    payload = bytes(resvg_py.svg_to_bytes(svg_string=svg, dpi=96,
                                          font_files=[str(path) for path in fonts],
                                          skip_system_fonts=True))
    return Image.open(BytesIO(payload)).convert("RGBA")


def test_native_alias_is_deterministic_preserves_face_data_and_uses_bounded_ps_name(tmp_path):
    source_bytes = LATIN.read_bytes()
    item = _item(LATIN, "Noto Sans")
    alias = "ChronaClosedFace-" + "a" * 64  # CSS family aliases may exceed the PS-name limit.
    first = pdf_raster_font_bytes(item, alias)
    second = pdf_raster_font_bytes(item, alias)
    assert PDF_RASTER_FONT_GRAMMAR == "pdf-native-raster-face-alias-v1"
    assert first == second
    assert LATIN.read_bytes() == source_bytes

    original = TTFont(BytesIO(source_bytes), recalcTimestamp=False)
    renamed = TTFont(BytesIO(first), recalcTimestamp=False)
    try:
        names = renamed["name"]
        assert {names.getDebugName(name_id) for name_id in (1, 4, 16)} == {alias}
        ps_names = {record.toUnicode() for record in names.names if record.nameID == 6}
        expected_ps = "ChronaHalo-" + sha256(alias.encode()).hexdigest()[:52]
        assert ps_names == {expected_ps} and len(expected_ps) <= 63
        for name_id in (2, 17, 13, 14):
            assert {record.toUnicode() for record in names.names if record.nameID == name_id} == {
                record.toUnicode() for record in original["name"].names if record.nameID == name_id
            }
        assert set(renamed.keys()) == set(original.keys())
        assert renamed.getBestCmap() == original.getBestCmap()
        assert renamed["hmtx"].metrics == original["hmtx"].metrics
        assert renamed["OS/2"].usWeightClass == original["OS/2"].usWeightClass
        assert renamed["OS/2"].fsType == original["OS/2"].fsType
        assert (renamed["head"].created, renamed["head"].modified) == (
            original["head"].created, original["head"].modified)
        for codepoint in (ord("A"), ord("W"), ord("g")):
            assert _outline(renamed, codepoint) == _outline(original, codepoint)
        for tag in ("GDEF", "GPOS", "GSUB"):
            assert tag in renamed and tag in original
    finally:
        original.close()
        renamed.close()


def test_native_alias_extracts_exact_collection_face_without_converting_cff(tmp_path):
    collection = write_cff_collection(tmp_path / "faces.ttc")
    item = _item(collection, "CFF Proof", index=1)
    before = collection.read_bytes()
    font = _renamed(item, "ChronaClosedFace-second-face", tmp_path / "selected.otf")
    try:
        assert "CFF " in font
        assert "glyf" not in font
        assert font["name"].getDebugName(1) == "ChronaClosedFace-second-face"
        assert font["hmtx"].metrics["A"] == (790, 0)
        assert collection.read_bytes() == before
    finally:
        font.close()


def test_native_alias_checks_source_identity_index_and_embedding_permissions(tmp_path):
    source = write_cff_font(tmp_path / "restricted.otf", family="Restricted", fs_type=0x0002)
    item = _item(source, "Restricted")
    with pytest.raises(PdfFontConversionError, match="restricted-license"):
        pdf_raster_font_bytes(item, "ChronaClosedFace-restricted")

    wrong_identity = FontFile(source, "sha256:" + "0" * 64, "Restricted", 400)
    with pytest.raises(PdfFontConversionError, match="bytes changed after face resolution"):
        pdf_raster_font_bytes(wrong_identity, "ChronaClosedFace-wrong")

    collection = write_cff_collection(tmp_path / "indexed.ttc")
    out_of_range = _item(collection, "CFF Proof", index=2)
    with pytest.raises(PdfFontConversionError, match="cannot open selected collection face 2"):
        pdf_raster_font_bytes(out_of_range, "ChronaClosedFace-missing")


def test_same_family_weight_aliases_render_each_exact_asset_with_no_host_fallback(tmp_path):
    primary, override = _item(LATIN, "Shared Face"), _item(MONO, "Shared Face")
    aliases = [
        "ChronaClosedFace-" + sha256((item.content_identity + str(item.index)).encode()).hexdigest()
        for item in (primary, override)
    ]
    paths = [tmp_path / "primary.ttf", tmp_path / "override.ttf"]
    fonts = [pdf_raster_font_bytes(item, alias) for item, alias in zip((primary, override), aliases)]
    for path, payload in zip(paths, fonts):
        path.write_bytes(payload)

    combined_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="70" viewBox="0 0 260 70">'
        f'<text x="8" y="48" font-size="34" font-weight="400" font-family="{aliases[0]}">'
        f'<tspan>WWWW</tspan><tspan x="130" font-family="{aliases[1]}">WWWW</tspan>'
        '</text></svg>'
    )
    # The control spells each selected source family explicitly while keeping
    # the same mixed-tspan shape/layout; each original file is still the only
    # supplied face for that family and system discovery remains disabled.
    source_face_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="70" viewBox="0 0 260 70">'
        '<text x="8" y="48" font-size="34" font-weight="400" font-family="Noto Sans">'
        '<tspan>WWWW</tspan><tspan x="130" font-family="Noto Sans Mono">WWWW</tspan>'
        '</text></svg>'
    )
    actual = _raster(combined_svg, paths).getchannel("A")
    expected = _raster(source_face_svg, [LATIN, MONO]).getchannel("A")
    assert expected.getbbox() is not None
    assert actual.tobytes() == expected.tobytes()
