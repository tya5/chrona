"""Deterministic local font ingestion for declared-metrics-v3 descriptors."""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from typing import Any

import yaml
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from chrona.resources import safe_load


class FontImportError(ValueError):
    def __init__(self, code: str, source_ref: str = "/", detail: str | None = None) -> None:
        super().__init__(code)
        self.code, self.source_ref, self._detail = code, source_ref, detail

    @property
    def detail(self) -> str:
        return f"{self.code} source={self.source_ref}" + (f"; {self._detail}" if self._detail else "")


def _shown(value: object) -> str:
    """Bound scalar descriptor operands in diagnostics."""
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 320:
        return f"<int bits={value.bit_length()}>"
    if value is None or isinstance(value, (str, int, float, bool)):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    return f"<{type(value).__name__}>"


def _axes(assignments: tuple[str, ...]) -> dict[str, float]:
    result: dict[str, float] = {}
    for assignment in assignments:
        try:
            tag, raw_value = assignment.split("=", 1)
            value = float(raw_value)
        except ValueError as error:
            raise FontImportError("E_FONT_IMPORT_AXIS", "/axis", f"assignment={assignment[:96]!r}; expected four-character axis tag=value") from error
        if len(tag) != 4 or not tag.isascii() or not math.isfinite(value) or tag in result:
            raise FontImportError("E_FONT_IMPORT_AXIS", "/axis", f"tag={_shown(tag)}, finiteValue={math.isfinite(value)}, duplicate={tag in result}; expected unique four-character ASCII axis tag and finite value")
        result[tag] = value
    return result


def _slug(family: str, weight: int) -> str:
    normalized = unicodedata.normalize("NFKD", family).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "font"
    return f"{stem[:180]}-{weight}"


def _numeric_advances(font: TTFont, cmap: dict[int, str], hmtx: dict[str, tuple[int, int]],
                      *, allow_partial: bool = False) -> dict[str, dict[str, int]]:
    """Extract the exact pnum/tnum digit glyph advances from one selected face."""
    features: dict[str, dict[str, str]] = {"proportional": {}, "tabular": {}}
    tags = {"pnum": "proportional", "tnum": "tabular"}
    try:
        records = font["GSUB"].table.FeatureList.FeatureRecord
        lookups = font["GSUB"].table.LookupList.Lookup
    except (AttributeError, KeyError):
        records, lookups = (), ()
    for record in records:
        mode = tags.get(record.FeatureTag)
        if mode is None:
            continue
        for index in record.Feature.LookupListIndex:
            for table in lookups[index].SubTable:
                mapping = getattr(table, "mapping", {})
                if isinstance(mapping, dict):
                    features[mode].update(mapping)
    result: dict[str, dict[str, int]] = {}
    for mode, substitutions in features.items():
        advances: dict[str, int] = {}
        for codepoint in range(ord("0"), ord("9") + 1):
            glyph = cmap.get(codepoint)
            target = substitutions.get(glyph, glyph)
            advance = hmtx.get(target or "", (None,))[0]
            if not isinstance(advance, int) or advance <= 0:
                raise FontImportError("E_FONT_IMPORT_FORMAT", "/numericAdvances", f"mode={mode!r}, codepoint=U+{codepoint:04X}, glyphPresent={glyph is not None}, advanceType={type(advance).__name__}; expected positive integer advance")
            advances[str(codepoint)] = advance
        result[mode] = advances
    if len(set(result["tabular"].values())) != 1:
        if not allow_partial:
            advances = result["tabular"].values()
            raise FontImportError("E_FONT_IMPORT_FORMAT", "/numericAdvances/tabular", f"digitAdvanceCount={len(result['tabular'])}, distinctAdvanceCount={len(set(advances))}; expected one shared tabular advance")
        del result["tabular"]
    return result


def _outline_cap_height(font: TTFont, cmap: dict[int, str], units: int) -> int:
    """Measure the exact face's uppercase H when a volatile host lacks OS/2 data."""
    glyph_name = cmap.get(ord("H"))
    if glyph_name is None:
        raise FontImportError("E_FONT_CAP_HEIGHT_REQUIRED", "/cmap/H", "uppercase H has no cmap glyph; expected one outline glyph to measure cap height")
    try:
        glyphs = font.getGlyphSet()
        pen = BoundsPen(glyphs)
        glyphs[glyph_name].draw(pen)
        top = pen.bounds[3] if pen.bounds is not None else None
    except (KeyError, TypeError, ValueError) as error:
        raise FontImportError("E_FONT_CAP_HEIGHT_REQUIRED", "/cmap/H", f"glyph={_shown(glyph_name)}, outlineError={type(error).__name__}; expected measurable H outline") from error
    if top is None or not 0 < top <= units:
        raise FontImportError("E_FONT_CAP_HEIGHT_REQUIRED", "/cmap/H", f"glyph={_shown(glyph_name)}, top={_shown(top)}, unitsPerEm={units}; expected cap-height bounds in (0, unitsPerEm]")
    return int(round(top))


def font_metrics_document(font: TTFont, payload: bytes, family: str, weight: int,
                          *, allow_partial_numeric: bool = False,
                          allow_outline_cap_height: bool = False) -> bytes:
    """Build the canonical v3 metrics document for exactly ``payload``.

    Both local import and draft system discovery use this function.  Keeping
    the extraction here ensures that a system face has the very same glyph and
    numeric-feature contract as a declared face.
    """
    try:
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"].metrics
        units = int(font["head"].unitsPerEm)
        cap_height = int(getattr(font["OS/2"], "sCapHeight", 0))
        ascent, descent = int(font["hhea"].ascent), int(font["hhea"].descent)
    except KeyError as error:
        raise FontImportError("E_FONT_IMPORT_FORMAT", "/font/tables", f"missing required font table={error.args[0] if error.args else 'unknown'!r}") from error
    if cap_height <= 0 and allow_outline_cap_height:
        cap_height = _outline_cap_height(font, cmap, units)
    if cap_height <= 0:
        raise FontImportError("E_FONT_CAP_HEIGHT_REQUIRED", "/OS/2/sCapHeight", f"capHeight={cap_height}, allowOutlineFallback={allow_outline_cap_height}; expected positive cap height")
    table = {
        "version": "chrona/font-metrics/v3", "family": family, "weight": weight,
        "sourceContentIdentity": "sha256:" + sha256(payload).hexdigest(),
        "unitsPerEm": units, "ascent": ascent, "descent": descent, "capHeight": cap_height,
        "defaultAdvance": int(hmtx.get(".notdef", (units, 0))[0]),
        "advances": {str(code): int(hmtx[name][0]) for code, name in sorted(cmap.items()) if name in hmtx},
        "numericAdvances": _numeric_advances(font, cmap, hmtx, allow_partial=allow_partial_numeric),
    }
    return (json.dumps(table, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_atomic(destination: Path, payload: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _descriptor(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"algorithm": "declared-metrics-v3", "missingFont": "diagnose", "assets": []}
    try:
        value = safe_load(path.read_bytes())
    except (OSError, yaml.YAMLError) as error:
        raise FontImportError("E_FONT_IMPORT_DESCRIPTOR", "/font-metrics.yaml", f"readOrParseError={type(error).__name__}; expected declared-metrics-v3 descriptor mapping") from error
    if (not isinstance(value, dict) or value.get("algorithm") != "declared-metrics-v3"
            or value.get("missingFont") != "diagnose" or not isinstance(value.get("assets"), list)):
        raise FontImportError("E_FONT_IMPORT_DESCRIPTOR", "/font-metrics.yaml", f"descriptorType={type(value).__name__}, algorithm={_shown(value.get('algorithm') if isinstance(value, dict) else None)}, missingFont={_shown(value.get('missingFont') if isinstance(value, dict) else None)}, assetsType={type(value.get('assets')).__name__ if isinstance(value, dict) else 'n/a'}; expected declared-metrics-v3, diagnose, asset list")
    return value


def import_font(source: Path, output: Path, *, family: str, weight: int,
                index: int = 0, axis: tuple[str, ...] = ()) -> dict[str, object]:
    """Import one face without allowing it to affect package/provider resolution."""
    if not family.strip() or not (1 <= weight <= 1000) or index < 0:
        raise FontImportError("E_FONT_IMPORT_ARGUMENT", "/family|weight|index", f"familyPresent={bool(family.strip())}, weight={_shown(weight)}, collectionIndex={_shown(index)}; expected nonblank family, weight 1..1000, nonnegative index")
    axes = _axes(axis)
    try:
        source_bytes = source.read_bytes()
        font = TTFont(source, fontNumber=index, recalcTimestamp=False)
    except (OSError, IndexError) as error:
        raise FontImportError("E_FONT_IMPORT_INPUT", "/source", f"sourceReadOrFaceSelectionError={type(error).__name__}, collectionIndex={index}; expected readable font face") from error
    except Exception as error:
        raise FontImportError("E_FONT_IMPORT_FORMAT", "/source", f"fontParserError={type(error).__name__}; expected supported TrueType/OpenType font") from error
    # A raw single-face font can remain byte-identical.  TTC extraction and
    # variable instances must be serialized as their selected static face.
    suffix = source.suffix.lower() if source.suffix.lower() in {".ttf", ".otf"} else ".ttf"
    needs_serialization = source.suffix.lower() == ".ttc" or bool(axes)
    if axes:
        try:
            font = instantiateVariableFont(font, axes, inplace=False)
        except Exception as error:
            axis_tags = tuple(item.split("=", 1)[0][:4] for item in axis[:8])
            raise FontImportError("E_FONT_IMPORT_AXIS", "/axis", f"axisCount={len(axis)}, axisTags={axis_tags!r}; expected valid variable-font axis coordinates") from error
    if needs_serialization:
        font.recalcTimestamp = False
        from io import BytesIO
        stream = BytesIO(); font.save(stream, reorderTables=True)
        font_bytes = stream.getvalue()
    else:
        font_bytes = source_bytes
    # Parse exactly the persisted bytes: metrics and source identity can never
    # accidentally describe a pre-instantiation input.
    try:
        persisted = TTFont(__import__("io").BytesIO(font_bytes), recalcTimestamp=False)
    except Exception as error:  # pragma: no cover - defensive against fontTools regressions
        raise FontImportError("E_FONT_IMPORT_FORMAT", "/font/serializedFace", f"persistedFaceParserError={type(error).__name__}; expected importable selected static face") from error
    metric_bytes = font_metrics_document(persisted, font_bytes, family, weight)
    slug = _slug(family, weight)
    font_name, metric_name = f"{slug}{suffix}", f"{slug}.metrics.json"
    descriptor_path = output / "font-metrics.yaml"
    if output.exists() and not output.is_dir():
        raise FontImportError("E_FONT_IMPORT_OUTPUT", "/output", f"outputExists=True, outputIsDirectory=False; expected directory path")
    descriptor = _descriptor(descriptor_path)
    if any(isinstance(item, dict) and item.get("family") == family and item.get("weight") == weight
           for item in descriptor["assets"]):
        raise FontImportError("E_FONT_IMPORT_DUPLICATE", "/assets", f"family={family[:96]!r}, weight={weight}; expected unique family/weight face")
    if (output / font_name).exists() or (output / metric_name).exists():
        raise FontImportError("E_FONT_IMPORT_COLLISION", "/output", f"fontName={_shown(font_name)}, metricsName={_shown(metric_name)}; expected both generated paths unused")
    font_identity, metric_identity = ("sha256:" + sha256(value).hexdigest() for value in (font_bytes, metric_bytes))
    descriptor["assets"].append({
        "family": family, "weight": weight,
        "metrics": {"locator": {"provider": "context", "address": metric_name}, "contentIdentity": metric_identity},
        "font": {"locator": {"provider": "context", "address": font_name}, "contentIdentity": font_identity},
    })
    descriptor["assets"].sort(key=lambda item: (str(item["family"]), int(item["weight"])))
    descriptor_bytes = yaml.safe_dump(descriptor, allow_unicode=True, sort_keys=False).encode("utf-8")
    # All validations occur before touching the output.  Each replacement is
    # atomic; descriptor comes last, so renderers never observe a descriptor
    # naming an incomplete pair.
    _write_atomic(output / font_name, font_bytes)
    _write_atomic(output / metric_name, metric_bytes)
    _write_atomic(descriptor_path, descriptor_bytes)
    return {"family": family, "weight": weight, "font": font_name, "metrics": metric_name,
            "fontContentIdentity": font_identity, "metricsContentIdentity": metric_identity}
