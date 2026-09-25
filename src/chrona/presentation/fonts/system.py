"""Draft-only exact system-font discovery behind a host bridge."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess

from fontTools.ttLib import TTFont

from chrona.presentation.fonts.importer import FontImportError, font_metrics_document
from chrona.presentation.model.font_metrics import FontFile, FontMetrics, FontMetricsError, font_metrics_from_document


class SystemFontError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class SystemFontFace:
    requested_family: str
    requested_weight: int
    path: Path
    family: str
    weight: int
    content_identity: str


@dataclass(frozen=True)
class DraftFontResolution:
    """Volatile exact face state, valid only while rendering one Draft."""

    face: SystemFontFace
    metrics: FontMetrics
    font_file: FontFile


def _name(font: TTFont, name_id: int) -> str | None:
    for item in font["name"].names:
        if item.nameID == name_id:
            try:
                return item.toUnicode()
            except Exception:
                continue
    return None


def resolve_system_font(family: str, weight: int, *, runner=subprocess.run) -> SystemFontFace:
    """Resolve one exact fontconfig result; substitutions never become a face."""
    if not family.strip() or not 1 <= weight <= 1000:
        raise SystemFontError("E_FONT_SYSTEM_MISSING", family)
    try:
        result = runner(["fc-match", "--format=%{file}\\n%{family}\\n%{weight}\\n", f"{family}:weight={weight}"],
                        check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise SystemFontError("E_FONT_SYSTEM_UNAVAILABLE", "fontconfig") from error
    except subprocess.CalledProcessError as error:
        raise SystemFontError("E_FONT_SYSTEM_MISSING", family) from error
    fields = result.stdout.splitlines()
    path = Path(fields[0]) if fields else Path()
    if not path.is_file():
        raise SystemFontError("E_FONT_SYSTEM_MISSING", family)
    try:
        font = TTFont(path, recalcTimestamp=False)
        actual_family = _name(font, 1)
        actual_weight = int(font["OS/2"].usWeightClass)
    except Exception as error:
        raise SystemFontError("E_FONT_SYSTEM_MISMATCH", family) from error
    if actual_family is None or actual_family.casefold() != family.casefold() or actual_weight != weight:
        raise SystemFontError("E_FONT_SYSTEM_MISMATCH", family)
    return SystemFontFace(family, weight, path, actual_family, actual_weight,
                          "sha256:" + sha256(path.read_bytes()).hexdigest())


def resolve_draft_font(face: SystemFontFace) -> DraftFontResolution:
    """Measure the exact bytes that the draft PNG renderer will receive."""
    try:
        payload = face.path.read_bytes()
        if "sha256:" + sha256(payload).hexdigest() != face.content_identity:
            raise ValueError("face bytes changed after resolution")
        document = font_metrics_document(TTFont(face.path, recalcTimestamp=False), payload, face.family, face.weight)
        metrics = font_metrics_from_document(document, metrics_path=face.path, family=face.family,
                                             weight=face.weight, source_content_identity=face.content_identity)
    except (OSError, ValueError, FontImportError, FontMetricsError) as error:
        raise SystemFontError("E_FONT_SYSTEM_MISMATCH", face.requested_family) from error
    return DraftFontResolution(face, metrics, FontFile(face.path, face.content_identity, face.family, face.weight))
