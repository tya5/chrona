"""Draft-only exact system-font discovery behind a host bridge."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Iterable, Protocol

from fontTools.ttLib import TTFont

from chrona.presentation.fonts.importer import FontImportError, font_metrics_document
from chrona.presentation.model.font_metrics import FontFile, FontMetrics, FontMetricsCatalog, FontMetricsError, font_metrics_from_document


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
    index: int = 0


class SystemFontResolver(Protocol):
    """Host bridge used only by explicit draft ingress."""

    def __call__(self, family: str, weight: int) -> SystemFontFace: ...


@dataclass(frozen=True)
class DraftFontResolution:
    """Volatile exact face catalog, valid only while rendering one Draft."""

    faces: tuple[SystemFontFace, ...]
    metrics: FontMetricsCatalog
    font_files: tuple[FontFile, ...]


def _names(font: TTFont) -> tuple[str, ...]:
    """Prefer English typographic names without assuming name-table order."""
    entries = font["name"].names
    selected = sorted((item for item in entries if item.nameID in {1, 16}),
                      key=lambda item: (item.nameID != 16, item.platformID != 3,
                                        item.langID != 0x409))
    names: list[str] = []
    for item in selected:
        try:
            names.append(item.toUnicode())
        except Exception:
            continue
    return tuple(names)


def _fontconfig_weight(weight: int) -> int:
    """Translate OpenType/CSS weights to fontconfig's independent scale."""
    anchors = ((100, 0), (200, 40), (300, 50), (400, 80), (500, 100),
               (600, 180), (700, 200), (800, 205), (900, 210), (1000, 210))
    if weight <= anchors[0][0]:
        return anchors[0][1]
    for (low_weight, low_fc), (high_weight, high_fc) in zip(anchors, anchors[1:]):
        if weight <= high_weight:
            return round(low_fc + (weight - low_weight) * (high_fc - low_fc) / (high_weight - low_weight))
    return anchors[-1][1]


def resolve_system_font(family: str, weight: int, *, runner=subprocess.run) -> SystemFontFace:
    """Resolve one exact fontconfig result; substitutions never become a face."""
    if not family.strip() or not 1 <= weight <= 1000:
        raise SystemFontError("E_FONT_SYSTEM_MISSING", family)
    try:
        result = runner(["fc-match", "--format=%{file}\\n%{family}\\n%{weight}\\n%{index}\\n",
                         f"{family}:weight={_fontconfig_weight(weight)}"],
                        check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise SystemFontError("E_FONT_SYSTEM_UNAVAILABLE", "Install fontconfig (macOS: brew install fontconfig; Linux: install your distribution's fontconfig package; Windows: install fontconfig)") from error
    except subprocess.CalledProcessError as error:
        raise SystemFontError("E_FONT_SYSTEM_MISSING", family) from error
    fields = result.stdout.splitlines()
    path = Path(fields[0]) if len(fields) == 4 else Path()
    if not path.is_file():
        raise SystemFontError("E_FONT_SYSTEM_MISSING", family)
    try:
        index = int(fields[3])
        if index < 0:
            raise ValueError("negative collection index")
        font = TTFont(path, fontNumber=index, recalcTimestamp=False)
        names = _names(font)
        actual_weight = int(font["OS/2"].usWeightClass)
    except Exception as error:
        raise SystemFontError("E_FONT_SYSTEM_MISMATCH", family) from error
    if family.casefold() not in {name.casefold() for name in names} or actual_weight != weight:
        raise SystemFontError("E_FONT_SYSTEM_MISMATCH", family)
    return SystemFontFace(family, weight, path, family, actual_weight,
                          "sha256:" + sha256(path.read_bytes()).hexdigest(), index)


def _draft_entry(face: SystemFontFace) -> tuple[FontMetrics, FontFile]:
    """Measure one exact face before it enters the draft catalog."""
    try:
        payload = face.path.read_bytes()
        if "sha256:" + sha256(payload).hexdigest() != face.content_identity:
            raise ValueError("face bytes changed after resolution")
        document = font_metrics_document(TTFont(face.path, fontNumber=face.index, recalcTimestamp=False),
                                         payload, face.family, face.weight, allow_partial_numeric=True,
                                         allow_outline_cap_height=True)
        metrics = font_metrics_from_document(document, metrics_path=face.path, family=face.family,
                                             weight=face.weight, source_content_identity=face.content_identity,
                                             require_numeric=False)
    except (OSError, ValueError, FontImportError, FontMetricsError) as error:
        raise SystemFontError("E_FONT_SYSTEM_MISMATCH", face.requested_family) from error
    return metrics, FontFile(face.path, face.content_identity, face.family, face.weight, face.index)


def resolve_draft_fonts(faces: Iterable[SystemFontFace]) -> DraftFontResolution:
    """Close exact system faces into the same catalog shape Layout already uses."""
    resolved_faces = tuple(sorted(faces, key=lambda face: (face.family.casefold(), face.weight)))
    if not resolved_faces:
        raise SystemFontError("E_FONT_SYSTEM_MISSING", "no Theme faces")
    metrics: dict[tuple[str, int], FontMetrics] = {}
    files: dict[tuple[str, int], FontFile] = {}
    for face in resolved_faces:
        key = (face.family.casefold(), face.weight)
        if key in metrics:
            raise SystemFontError("E_FONT_SYSTEM_MISMATCH", f"duplicate face: {face.family}/{face.weight}")
        metric, font_file = _draft_entry(face)
        metrics[key] = metric
        previous = files.setdefault((font_file.content_identity, font_file.index), font_file)
        if previous.family.casefold() != font_file.family.casefold() or previous.weight != font_file.weight:
            raise SystemFontError("E_FONT_SYSTEM_MISMATCH", f"ambiguous face identity: {font_file.content_identity}")
    return DraftFontResolution(resolved_faces, FontMetricsCatalog(metrics),
                               tuple(files[key] for key in sorted(files)))


def resolve_draft_font(face: SystemFontFace) -> DraftFontResolution:
    """Close one exact face for callers that deliberately need a one-face catalog."""
    return resolve_draft_fonts((face,))
