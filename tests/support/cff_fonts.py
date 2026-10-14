"""Small generated CFF fixtures for PDF adapter tests; no host fonts involved."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from fontTools.ttLib import TTCollection, TTFont


def _font_bytes(*, family: str, outline: str, fs_type: int, os2_version: int,
                a_advance: int, h_advance: int, variable: bool) -> bytes:
    if outline not in {"cff", "cff2"}:
        raise ValueError(f"unsupported synthetic outline kind: {outline}")
    if variable and outline != "cff2":
        raise ValueError("only a CFF2 fixture can be variable")

    builder = FontBuilder(1000, isTTF=False)
    # `zero` is the one positive-advance glyph shared by H and the digits;
    # CFF2's charset-less glyph order keeps this stable across both outlines.
    builder.setupGlyphOrder([".notdef", "space", "A", "zero"])
    cmap = {ord(" "): "space", ord("A"): "A", ord("H"): "zero"}
    cmap.update({ord(str(digit)): "zero" for digit in range(10)})
    builder.setupCharacterMap(cmap)
    builder.setupHorizontalMetrics({".notdef": (500, 0), "space": (300, 0),
                                    "A": (a_advance, 0), "zero": (h_advance, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({
        "familyName": family,
        "styleName": "Regular",
        "uniqueFontIdentifier": f"{family} Regular",
        "fullName": f"{family} Regular",
        "psName": family.replace(" ", "") + "-Regular",
    })
    os2_values = {"version": os2_version, "usWeightClass": 400, "fsType": fs_type,
                  "sTypoAscender": 800, "sTypoDescender": -200, "usWinAscent": 800, "usWinDescent": 200}
    if os2_version >= 2:
        os2_values["sCapHeight"] = 720
    builder.setupOS2(**os2_values)
    builder.setupPost()

    notdef = T2CharString(program=[0, 0, "rmoveto", "endchar"] if outline == "cff" else [0, 0, "rmoveto"])
    a_program: list[object] = [100, 0, "rmoveto"]
    if variable:
        # One CFF2 blend region changes the first curve control point away from
        # the default axis location.  Instancing at the default must recover
        # the same base outline as the corresponding static fixture.
        a_program.extend([0, 500, 200, 300, 300, 0, 0, 120, 0, 0, 0, 0, 6, "blend", "rrcurveto"])
    else:
        a_program.extend([0, 500, 200, 300, 300, 0, "rrcurveto"])
    a_program.extend([0, -300, -200, -200, -300, 0, "rrcurveto", 0, -300, "rlineto"])
    if outline == "cff":
        a_program.append("endchar")
    h_program: list[object] = [50, 0, "rmoveto", 0, 550, 450, 0, "rlineto", 0, -550, -450, 0, "rlineto"]
    if outline == "cff":
        h_program.append("endchar")
    char_strings = {
        ".notdef": notdef,
        "space": T2CharString(program=["endchar"] if outline == "cff" else []),
        "A": T2CharString(program=a_program),
        "zero": T2CharString(program=h_program),
    }

    if outline == "cff":
        builder.setupCFF(
            family.replace(" ", "") + "-Regular",
            {"FullName": f"{family} Regular", "FamilyName": family, "Weight": "Regular"},
            char_strings,
            {},
        )
    else:
        if variable:
            builder.setupFvar([("wght", 100, 400, 900, "Weight")], [])
            builder.setupCFF2(char_strings, regions=[{"wght": (0, 1, 1)}])
        else:
            builder.setupCFF2(char_strings)
    builder.font["maxp"].numGlyphs = 4
    output = BytesIO()
    builder.font.save(output)
    return output.getvalue()


def write_cff_font(path: Path, *, family: str = "Synthetic CFF", outline: str = "cff",
                   fs_type: int = 0, os2_version: int = 4, a_advance: int = 700,
                   h_advance: int = 620, variable: bool = False) -> Path:
    """Write one generated OpenType CFF/CFF2 face with distinctive A/H outlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_font_bytes(family=family, outline=outline, fs_type=fs_type,
                                 os2_version=os2_version, a_advance=a_advance,
                                 h_advance=h_advance, variable=variable))
    return path


def write_cff_collection(path: Path) -> Path:
    """Write a two-face CFF collection whose second face has a different A advance."""
    faces = [
        TTFont(BytesIO(_font_bytes(family="Synthetic First", outline="cff", fs_type=0,
                                   os2_version=4, a_advance=510, h_advance=520, variable=False))),
        TTFont(BytesIO(_font_bytes(family="CFF Proof", outline="cff", fs_type=0,
                                   os2_version=4, a_advance=790, h_advance=680, variable=False))),
    ]
    collection = TTCollection()
    collection.fonts = faces
    path.parent.mkdir(parents=True, exist_ok=True)
    collection.save(path)
    return path
