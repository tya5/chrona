"""Deterministic CFF-to-glyf translation for the PDF adapter."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from typing import Any

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

from chrona.presentation.model.font_metrics import FontFile


CONVERSION_GRAMMAR = "cff-cu2qu-v1"
EMBEDDING_GRAMMAR = "pdf-closed-face-v1"
PDF_RASTER_FONT_GRAMMAR = "pdf-native-raster-face-alias-v1"
_OUTLINE_TOLERANCE_EM = 0.001


class PdfFontConversionError(ValueError):
    """A selected font cannot be safely translated for PDF output."""


def _failure(item: FontFile, detail: str) -> PdfFontConversionError:
    return PdfFontConversionError(
        f"{item.family}/{item.weight} from {item.path.name}: {detail}"
    )


def _invalid_fs_type(version: int, fs_type: int) -> str | None:
    """Return a refusal reason under the OS/2 version-specific fsType rules."""
    if version not in range(6):
        return f"unsupported OS/2 version {version} for embedding permissions"

    # Bit zero is reserved in every specified version. Versions 0 and 1
    # assign no semantics to bits 4..15; later versions reserve 4..7 and 10..15.
    if fs_type & 0x0001:
        return f"invalid reserved fsType usage bit (0x{fs_type:04X})"
    if version <= 1:
        permissions = fs_type & 0x000E
    else:
        if fs_type & 0xFCF0:
            return f"invalid reserved fsType bits (0x{fs_type:04X})"
        permissions = fs_type & 0x000E

    if version >= 3 and permissions & (permissions - 1):
        return f"invalid multiple fsType permissions for OS/2 version {version} (0x{fs_type:04X})"

    # Versions 0..2 allowed multiple permission bits and specified that the
    # least restrictive permission wins. Editable is less restrictive than
    # preview/print, which is less restrictive than restricted.
    effective_permission = next(
        (permission for permission in (0x0008, 0x0004, 0x0002) if permissions & permission),
        0,
    )
    if effective_permission == 0x0002:
        return "restricted-license embedding is not permitted"

    if version >= 2:
        if fs_type & 0x0200:
            return "bitmap-only embedding does not permit outline embedding"
        if fs_type & 0x0100:
            return "no-subsetting fonts cannot be embedded by the current PDF adapter"
    return None


def _check_embedding_permissions(item: FontFile, font: TTFont) -> None:
    if "OS/2" not in font:
        raise _failure(item, "OS/2 embedding permissions are missing")
    table = font["OS/2"]
    version, fs_type = getattr(table, "version", None), getattr(table, "fsType", None)
    if (isinstance(version, bool) or not isinstance(version, int)
            or isinstance(fs_type, bool) or not isinstance(fs_type, int)
            or not 0 <= fs_type <= 0xFFFF):
        raise _failure(item, "OS/2 embedding permission metadata is invalid")
    reason = _invalid_fs_type(version, fs_type)
    if reason is not None:
        raise _failure(item, reason)


def pdf_raster_font_bytes(item: FontFile, alias: str) -> bytes:
    """Extract and privately rename the exact native face used for PDF glow rasterization.

    Unlike :func:`pdf_font_bytes`, this payload remains in its source outline
    format: resvg consumes the aliased native face to paint the completed glow
    source alpha. Only the family/full/typographic-family labels and the
    deterministic PostScript name are changed.
    """
    if not isinstance(alias, str) or not alias or "\x00" in alias:
        raise _failure(item, "private raster font alias must be a non-empty string without NUL")
    try:
        source_bytes = item.path.read_bytes()
    except OSError as error:
        raise _failure(item, f"cannot read selected font bytes ({type(error).__name__})") from error
    source_identity = "sha256:" + sha256(source_bytes).hexdigest()
    if source_identity != item.content_identity:
        raise _failure(item, "selected font bytes changed after face resolution")

    try:
        font = TTFont(BytesIO(source_bytes), fontNumber=item.index, recalcTimestamp=False)
    except Exception as error:
        raise _failure(item, f"cannot open selected collection face {item.index} ({type(error).__name__})") from error
    try:
        _check_embedding_permissions(item, font)
        if "name" not in font:
            raise _failure(item, "selected face has no name table for private raster aliasing")

        names = font["name"]
        # The long CSS alias remains the family/full/typographic-family name.
        # PostScript names have a 63-character limit, so derive a stable short
        # identifier without changing the shared CSS family alias contract.
        ps_alias = "ChronaHalo-" + sha256(alias.encode("utf-8")).hexdigest()[:52]
        for name_id, value in ((1, alias), (4, alias), (16, alias), (6, ps_alias)):
            records = [record for record in names.names if record.nameID == name_id]
            if records:
                for record in records:
                    names.setName(value, name_id, record.platformID,
                                  record.platEncID, record.langID)
            else:
                names.setName(value, name_id, 3, 1, 0x0409)

        font.recalcTimestamp = False
        output = BytesIO()
        font.save(output, reorderTables=True)
        return output.getvalue()
    except PdfFontConversionError:
        raise
    except Exception as error:
        raise _failure(item, f"native raster font alias serialization failed ({type(error).__name__})") from error
    finally:
        font.close()


def _table_values(table: Any) -> dict[str, Any]:
    """Copy a parsed table's declared fields for FontBuilder initialization."""
    return {name: value for name, value in vars(table).items() if not name.startswith("_")}


def _converted_font(font: TTFont, item: FontFile, characters: frozenset[int]) -> bytes:
    try:
        source_cmap = font.getBestCmap() or {}
        invalid = sorted(
            codepoint for codepoint in characters
            if isinstance(codepoint, bool) or not isinstance(codepoint, int)
            or not 0 <= codepoint <= 0x10FFFF
            or 0xD800 <= codepoint <= 0xDFFF
        )
        if invalid:
            raise _failure(item, f"requested text contains invalid Unicode codepoints {invalid[:8]!r}")
        missing = sorted(codepoint for codepoint in characters if codepoint not in source_cmap)
        if missing:
            shown = ",".join(f"U+{codepoint:04X}" for codepoint in missing[:8])
            raise _failure(item, f"requested glyphs are missing from the selected face: {shown}")

        subset_characters = characters
        if not subset_characters:
            # ReportLab requires at least one cmap entry when registering a
            # dynamic font, even if completed SVG text never selects this face.
            # Retain one real source mapping solely as its encoding anchor; no
            # output text references or substitutes this codepoint.
            valid_source_codepoints = sorted(
                codepoint for codepoint, glyph_name in source_cmap.items()
                if isinstance(codepoint, int) and not isinstance(codepoint, bool)
                and 0 <= codepoint <= 0x10FFFF
                and not 0xD800 <= codepoint <= 0xDFFF
                and glyph_name != ".notdef"
            )
            if not valid_source_codepoints:
                raise _failure(item, "selected face has no usable cmap encoding for PDF registration")
            subset_characters = frozenset({valid_source_codepoints[0]})

        options = Options()
        options.name_IDs = ["*"]
        options.name_legacy = True
        options.name_languages = ["*"]
        options.layout_features = ["*"]
        subsetter = Subsetter(options=options)
        subsetter.populate(unicodes=sorted(subset_characters))
        subsetter.subset(font)

        glyph_order = font.getGlyphOrder()
        cmap = font.getBestCmap() or {}
        missing = sorted(codepoint for codepoint in characters if codepoint not in cmap)
        if missing:
            shown = ",".join(f"U+{codepoint:04X}" for codepoint in missing[:8])
            raise _failure(item, f"font subsetting lost requested glyph mappings: {shown}")
        glyph_names = set(glyph_order)
        if any(name not in glyph_names for name in cmap.values()):
            raise _failure(item, "font subsetting left cmap references outside the retained glyph set")

        units_per_em = int(font["head"].unitsPerEm)
        if units_per_em <= 0:
            raise _failure(item, "selected face has an invalid unitsPerEm value")
        glyph_set = font.getGlyphSet(location=None)
        glyphs = {}
        max_error = units_per_em * _OUTLINE_TOLERANCE_EM
        for glyph_name in glyph_order:
            pen = TTGlyphPen(glyph_set)
            glyph_set[glyph_name].draw(Cu2QuPen(pen, max_err=max_error, all_quadratic=True))
            glyphs[glyph_name] = pen.glyph()

        builder = FontBuilder(unitsPerEm=units_per_em, isTTF=True, glyphDataFormat=0)
        builder.setupGlyphOrder(glyph_order)

        head_values = _table_values(font["head"])
        head_values["indexToLocFormat"] = 1
        head_values["glyphDataFormat"] = 0
        builder.setupHead(**head_values)

        builder.setupCharacterMap(cmap, allowFallback=True)
        builder.setupGlyf(glyphs)
        builder.setupHorizontalMetrics({
            name: font["hmtx"].metrics[name] for name in glyph_order
            if name in font["hmtx"].metrics
        })
        builder.setupHorizontalHeader(**_table_values(font["hhea"]))
        builder.setupMaxp()
        builder.setupPost(keepGlyphNames=True)

        # Keep the selected/subset face's localized names and all OS/2 fields;
        # the subsetter has already pruned cmap, layout and name references.
        builder.font["cmap"] = deepcopy(font["cmap"])
        builder.font["name"] = deepcopy(font["name"])
        builder.font["OS/2"] = deepcopy(font["OS/2"])
        for tag in ("GDEF", "GPOS", "GSUB", "BASE", "kern"):
            if tag in font:
                builder.font[tag] = deepcopy(font[tag])

        builder.font.recalcTimestamp = False
        stream = BytesIO()
        builder.font.save(stream, reorderTables=True)
        return stream.getvalue()
    except PdfFontConversionError:
        raise
    except Exception as error:
        raise _failure(item, f"CFF outline translation failed ({type(error).__name__})") from error


def pdf_font_bytes(item: FontFile, characters: frozenset[int]) -> bytes | None:
    """Return a deterministic TrueType conversion for one exact selected CFF face.

    ``None`` means the selected face is already a TrueType-outline face and
    must follow the renderer's unchanged registration path.
    """
    try:
        source_bytes = item.path.read_bytes()
    except OSError as error:
        raise _failure(item, f"cannot read selected font bytes ({type(error).__name__})") from error
    source_identity = "sha256:" + sha256(source_bytes).hexdigest()
    if source_identity != item.content_identity:
        raise _failure(item, "selected font bytes changed after face resolution")

    try:
        font = TTFont(BytesIO(source_bytes), fontNumber=item.index, recalcTimestamp=False)
    except Exception as error:
        raise _failure(item, f"cannot open selected collection face {item.index} ({type(error).__name__})") from error
    try:
        if "CFF " not in font and "CFF2" not in font:
            return None
        _check_embedding_permissions(item, font)
        return _converted_font(font, item, characters)
    finally:
        font.close()


def pdf_embedding_bytes(item: FontFile, converted: bytes | None) -> tuple[bytes, str]:
    """Return a namespaced, deterministic payload for one selected PDF face.

    ``converted`` is the subsetted glyf payload returned by
    :func:`pdf_font_bytes` for CFF sources, and ``None`` for an already-glyf
    source. This path checks the exact selected source face's embedding
    permissions, serializes a deterministic pre-name payload, then derives a
    unique PostScript name from that payload so ReportLab cannot reuse another
    face's dynamic-font cache entry. TrueType input is extracted unchanged
    except for its internal PostScript name; CFF input uses the converted glyf
    payload.
    """
    try:
        source_bytes = item.path.read_bytes()
    except OSError as error:
        raise _failure(item, f"cannot read selected font bytes ({type(error).__name__})") from error
    source_identity = "sha256:" + sha256(source_bytes).hexdigest()
    if source_identity != item.content_identity:
        raise _failure(item, "selected font bytes changed after face resolution")

    try:
        source = TTFont(BytesIO(source_bytes), fontNumber=item.index, recalcTimestamp=False)
    except Exception as error:
        raise _failure(item, f"cannot open selected collection face {item.index} ({type(error).__name__})") from error
    try:
        _check_embedding_permissions(item, source)
        source_is_cff = "CFF " in source or "CFF2" in source
        if source_is_cff and converted is None:
            raise _failure(item, "CFF face was not converted to glyf for PDF embedding")
        if not source_is_cff and converted is not None:
            raise _failure(item, "unexpected converted payload for a non-CFF selected face")
    finally:
        source.close()

    payload = converted if converted is not None else source_bytes
    try:
        # A collection's exact indexed face must be made standalone. For a
        # standalone non-CFF source, reload via its selected index above but
        # serialize the face below through the same canonical path.
        embedding = TTFont(BytesIO(payload), fontNumber=0 if converted is not None else item.index,
                           recalcTimestamp=False)
    except Exception as error:
        raise _failure(item, f"cannot open selected PDF embedding face ({type(error).__name__})") from error
    try:
        _check_embedding_permissions(item, embedding)
        if "CFF " in embedding or "CFF2" in embedding:
            raise _failure(item, "PDF embedding payload still contains CFF outlines")

        # ReportLab caches TTFont faces by the PostScript name parsed from the
        # embedded table. Hash the complete deterministic payload before its
        # name is changed, so distinct subsets receive distinct cache keys.
        embedding.recalcTimestamp = False
        pre_name = BytesIO()
        embedding.save(pre_name, reorderTables=True)
        canonical_payload = pre_name.getvalue()
        alias = "ChronaPDF-" + sha256(canonical_payload).hexdigest()[:48]

        name_table = embedding["name"] if "name" in embedding else None
        if name_table is None:
            raise _failure(item, "PDF embedding face has no name table for PostScript namespacing")
        records = [record for record in name_table.names if record.nameID == 6]
        if records:
            for record in records:
                name_table.setName(alias, 6, record.platformID, record.platEncID, record.langID)
        else:
            # Name ID 6 is required for usable OpenType fonts; repair only that
            # missing internal name, leaving every human-facing name intact.
            name_table.setName(alias, 6, 3, 1, 0x0409)

        output = BytesIO()
        embedding.save(output, reorderTables=True)
        return output.getvalue(), alias
    except PdfFontConversionError:
        raise
    except Exception as error:
        raise _failure(item, f"PDF embedding face serialization failed ({type(error).__name__})") from error
    finally:
        embedding.close()
