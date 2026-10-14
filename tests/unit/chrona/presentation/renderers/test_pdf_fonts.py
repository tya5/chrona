"""PDF's CFF-to-glyf adapter translation uses only the exact selected face."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from fontTools.ttLib import TTCollection, TTFont

from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.pdf_fonts import (
    CONVERSION_GRAMMAR,
    PdfFontConversionError,
    pdf_embedding_bytes,
    pdf_font_bytes,
)
from tests.support.cff_fonts import write_cff_collection, write_cff_font


ROOT = Path(__file__).resolve().parents[5]
CHARACTERS = frozenset({ord(" "), ord("A"), ord("H"), *(ord(str(digit)) for digit in range(10))})


def _font_file(path: Path, family: str, *, index: int = 0) -> FontFile:
    return FontFile(path, "sha256:" + sha256(path.read_bytes()).hexdigest(), family, 400, index)


def _converted(path: Path, family: str = "CFF Proof", *, index: int = 0) -> tuple[bytes, TTFont]:
    payload = pdf_font_bytes(_font_file(path, family, index=index), CHARACTERS)
    assert payload is not None
    return payload, TTFont(BytesIO(payload), recalcTimestamp=False)


def _points(font: TTFont, name: str) -> tuple[tuple[tuple[int, int], ...], tuple[int, ...]]:
    glyph = font["glyf"][name]
    return tuple((int(x), int(y)) for x, y in glyph.coordinates), tuple(int(flag) for flag in glyph.flags)


@pytest.mark.parametrize("outline", ["cff", "cff2"])
def test_cff_conversion_is_deterministic_and_preserves_selected_face_tables(tmp_path, outline):
    source = write_cff_font(tmp_path / f"selected-{outline}.otf", family="CFF Proof", outline=outline)
    first, font = _converted(source)
    second = pdf_font_bytes(_font_file(source, "CFF Proof"), CHARACTERS)

    assert CONVERSION_GRAMMAR == "cff-cu2qu-v1"
    assert first == second
    assert {"glyf", "loca"} <= set(font.keys())
    assert "CFF " not in font and "CFF2" not in font
    cmap = font.getBestCmap()
    assert set(cmap.values()) == {"space", "A", "zero"}
    assert all(cmap[ord(str(digit))] == cmap[ord("H")] for digit in range(10))
    assert font["hmtx"].metrics["A"] == (700, 0)
    assert font["hmtx"].metrics["zero"] == (620, 0)
    assert font["head"].unitsPerEm == 1000
    assert (font["hhea"].ascent, font["hhea"].descent) == (800, -200)
    assert font["OS/2"].usWeightClass == 400
    assert font["OS/2"].sTypoAscender == 800
    assert font["OS/2"].sTypoDescender == -200
    assert font["OS/2"].sCapHeight == 720
    assert font["name"].getDebugName(1) == "CFF Proof"
    coordinates, flags = _points(font, "A")
    assert coordinates and any(not (flag & 1) for flag in flags), (
        "the curved CFF outline must survive as quadratic points"
    )


def test_cff2_variable_face_uses_default_axis_instance(tmp_path):
    variable = write_cff_font(tmp_path / "variable.otf", family="CFF Proof", outline="cff2", variable=True)
    default_static = write_cff_font(tmp_path / "default-static.otf", family="CFF Proof", outline="cff2")

    _variable_bytes, variable_font = _converted(variable)
    _static_bytes, static_font = _converted(default_static)

    assert variable_font["hmtx"].metrics == static_font["hmtx"].metrics
    assert _points(variable_font, "A") == _points(static_font, "A")
    assert "fvar" not in variable_font  # conversion is one static default-axis instance


def test_ttc_conversion_uses_the_selected_nonzero_collection_face(tmp_path):
    collection = write_cff_collection(tmp_path / "two-faces.ttc")
    _payload, selected = _converted(collection, "CFF Proof", index=1)

    assert selected["name"].getDebugName(1) == "CFF Proof"
    assert selected["hmtx"].metrics["A"] == (790, 0)
    assert "glyf" in selected and "CFF " not in selected


def test_embedding_namespace_is_deterministic_and_preserves_human_face_data(tmp_path):
    source = write_cff_font(tmp_path / "same-family.otf", family="CFF Proof")
    source_before = source.read_bytes()
    item = _font_file(source, "CFF Proof")
    converted = pdf_font_bytes(item, CHARACTERS)
    assert converted is not None

    first_bytes, alias = pdf_embedding_bytes(item, converted)
    second_bytes, second_alias = pdf_embedding_bytes(item, converted)
    first = TTFont(BytesIO(first_bytes), recalcTimestamp=False)
    original = TTFont(BytesIO(converted), recalcTimestamp=False)
    try:
        expected_alias = "ChronaPDF-" + sha256(converted).hexdigest()[:48]
        assert alias == second_alias == expected_alias
        assert first_bytes == second_bytes
        assert first["name"].getDebugName(6) == alias
        assert {
            record.toUnicode() for record in first["name"].names if record.nameID == 6
        } == {alias}
        for name_id in (1, 2, 4, 16, 17):
            assert first["name"].getDebugName(name_id) == original["name"].getDebugName(name_id)
        assert first.getBestCmap() == original.getBestCmap()
        assert first["hmtx"].metrics == original["hmtx"].metrics
        assert source.read_bytes() == source_before
    finally:
        first.close()
        original.close()


def test_embedding_names_distinguish_same_family_subsets_and_selected_faces(tmp_path):
    source = write_cff_font(tmp_path / "same-family.otf", family="CFF Proof")
    item = _font_file(source, "CFF Proof")
    all_chars = pdf_font_bytes(item, CHARACTERS)
    smaller_subset = pdf_font_bytes(item, frozenset({ord("A")}))
    assert all_chars is not None and smaller_subset is not None
    _all_bytes, all_alias = pdf_embedding_bytes(item, all_chars)
    _small_bytes, small_alias = pdf_embedding_bytes(item, smaller_subset)
    assert all_alias != small_alias

    other_face_path = write_cff_font(
        tmp_path / "different-face.otf", family="CFF Proof", a_advance=701
    )
    other_item = _font_file(other_face_path, "CFF Proof")
    other_face = pdf_font_bytes(other_item, CHARACTERS)
    assert other_face is not None
    _other_bytes, other_alias = pdf_embedding_bytes(other_item, other_face)
    assert all_alias != other_alias


def test_embedding_extracts_original_selected_ttc_face_and_checks_its_permissions(tmp_path):
    allowed = write_cff_font(tmp_path / "allowed.otf", family="CFF Proof", a_advance=790)
    restricted = write_cff_font(
        tmp_path / "restricted.otf", family="Other Face", fs_type=0x0002
    )
    collection_path = tmp_path / "permission-faces.ttc"
    collection = TTCollection()
    collection.fonts = [
        TTFont(str(restricted), recalcTimestamp=False),
        TTFont(str(allowed), recalcTimestamp=False),
    ]
    collection.save(collection_path)
    for face in collection.fonts:
        face.close()

    # Only the exact selected indexed face controls permission. A restricted
    # sibling must not block an otherwise permitted face.
    item = _font_file(collection_path, "CFF Proof", index=1)
    converted = pdf_font_bytes(item, CHARACTERS)
    assert converted is not None
    embedded, _alias = pdf_embedding_bytes(item, converted)
    embedded_font = TTFont(BytesIO(embedded), recalcTimestamp=False)
    try:
        assert embedded_font["name"].getDebugName(1) == "CFF Proof"
        assert embedded_font["hmtx"].metrics["A"] == (790, 0)
    finally:
        embedded_font.close()

    # Conversely, an allowed sibling cannot authorize the selected restricted
    # face.
    inverse_path = tmp_path / "selected-restricted.ttc"
    inverse = TTCollection()
    inverse.fonts = [
        TTFont(str(allowed), recalcTimestamp=False),
        TTFont(str(restricted), recalcTimestamp=False),
    ]
    inverse.save(inverse_path)
    for face in inverse.fonts:
        face.close()
    restricted_item = _font_file(inverse_path, "Other Face", index=1)
    with pytest.raises(PdfFontConversionError, match="restricted-license"):
        pdf_font_bytes(restricted_item, CHARACTERS)

    # With both collection faces permitted, the embedding bytes and retained
    # human names must come from the requested nonzero face, not face zero.
    permitted_path = tmp_path / "permitted-faces.ttc"
    first = write_cff_font(tmp_path / "first.otf", family="First Face", a_advance=510)
    second = write_cff_font(tmp_path / "second.otf", family="CFF Proof", a_advance=790)
    permitted = TTCollection()
    permitted.fonts = [TTFont(str(first), recalcTimestamp=False), TTFont(str(second), recalcTimestamp=False)]
    permitted.save(permitted_path)
    for face in permitted.fonts:
        face.close()
    permitted_item = _font_file(permitted_path, "CFF Proof", index=1)
    converted = pdf_font_bytes(permitted_item, CHARACTERS)
    assert converted is not None
    embedded, _alias = pdf_embedding_bytes(permitted_item, converted)
    embedded_font = TTFont(BytesIO(embedded), recalcTimestamp=False)
    try:
        assert embedded_font["name"].getDebugName(1) == "CFF Proof"
        assert embedded_font["hmtx"].metrics["A"] == (790, 0)
    finally:
        embedded_font.close()


def test_non_cff_embedding_extracts_exact_indexed_ttc_face(tmp_path):
    source = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
    original_bytes = source.read_bytes()
    first = TTFont(BytesIO(original_bytes), recalcTimestamp=False)
    second = TTFont(BytesIO(original_bytes), recalcTimestamp=False)
    for record in first["name"].names:
        if record.nameID in {1, 4, 6, 16}:
            record.string = "FirstFace-Regular".encode(record.getEncoding())
    collection = TTCollection()
    collection.fonts = [first, second]
    collection_path = tmp_path / "ttf-faces.ttc"
    collection.save(collection_path)
    for face in collection.fonts:
        face.close()

    item = _font_file(collection_path, "Noto Sans", index=1)
    before = collection_path.read_bytes()
    embedded, alias = pdf_embedding_bytes(item, None)
    selected = TTFont(BytesIO(embedded), recalcTimestamp=False)
    try:
        assert selected["name"].getDebugName(1) == "Noto Sans"
        assert selected["name"].getDebugName(6) == alias
        assert collection_path.read_bytes() == before
        assert source.read_bytes() == original_bytes
    finally:
        selected.close()


def test_missing_requested_unicode_character_fails_without_notdef_substitution(tmp_path):
    source = write_cff_font(tmp_path / "missing-glyph.otf")
    with pytest.raises(PdfFontConversionError, match="U\\+005A"):
        pdf_font_bytes(_font_file(source, "Synthetic CFF"), frozenset({ord("Z")}))


@pytest.mark.parametrize("fs_type", [0x0000, 0x0004, 0x0008])
def test_installable_preview_print_and_editable_permissions_are_admitted(tmp_path, fs_type):
    source = write_cff_font(tmp_path / f"allowed-{fs_type:04x}.otf", fs_type=fs_type)
    assert pdf_font_bytes(_font_file(source, "Synthetic CFF"), CHARACTERS) is not None


@pytest.mark.parametrize(
    ("fs_type", "version", "reason"),
    [
        (0x0002, 4, "restricted-license"),
        (0x0200, 4, "bitmap-only"),
        (0x0100, 4, "no-subsetting"),
        (0x0001, 4, "reserved fsType usage bit"),
        (0x0010, 4, "reserved fsType bits"),
        (0x0006, 4, "multiple fsType permissions"),
    ],
)
def test_forbidden_or_invalid_embedding_permissions_fail_closed(tmp_path, fs_type, version, reason):
    source = write_cff_font(tmp_path / f"invalid-{version}-{fs_type:04x}.otf",
                            fs_type=fs_type, os2_version=version)
    with pytest.raises(PdfFontConversionError, match=reason):
        pdf_font_bytes(_font_file(source, "Synthetic CFF"), CHARACTERS)


@pytest.mark.parametrize(
    ("version", "fs_type"),
    [
        (0, 0x0100),  # high bits were undefined in this version
        (1, 0x0200),  # bitmap-only was not yet a defined bit
        (1, 0x000A),  # legacy overlapping permissions: editable is least restrictive
        (2, 0x0006),  # through version 2, preview/print wins over restricted
    ],
)
def test_legacy_permission_versions_use_their_defined_least_restrictive_rules(tmp_path, version, fs_type):
    source = write_cff_font(tmp_path / f"legacy-{version}-{fs_type:04x}.otf",
                            fs_type=fs_type, os2_version=version)
    assert pdf_font_bytes(_font_file(source, "Synthetic CFF"), CHARACTERS) is not None


def test_true_type_face_takes_unchanged_non_conversion_path_and_identity_is_checked():
    source = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
    item = _font_file(source, "Noto Sans")
    assert pdf_font_bytes(item, CHARACTERS) is None

    wrong_identity = FontFile(source, "sha256:" + "0" * 64, "Noto Sans", 400)
    with pytest.raises(PdfFontConversionError, match="bytes changed after face resolution"):
        pdf_font_bytes(wrong_identity, CHARACTERS)
    with pytest.raises(PdfFontConversionError, match="bytes changed after face resolution"):
        pdf_embedding_bytes(wrong_identity, None)


def test_non_cff_embedding_rejects_selected_face_restricted_permissions(tmp_path):
    source = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
    font = TTFont(str(source), recalcTimestamp=False)
    font["OS/2"].fsType = 0x0002
    restricted_path = tmp_path / "restricted-noto.ttf"
    font.save(restricted_path)
    font.close()

    item = _font_file(restricted_path, "Noto Sans")
    with pytest.raises(PdfFontConversionError, match="restricted-license"):
        pdf_embedding_bytes(item, None)
