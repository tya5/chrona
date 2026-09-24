"""Deterministic declared font closure for Layout and output adapters."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path


class FontMetricsError(ValueError):
    """A declared font closure cannot measure the requested text exactly."""

    def __init__(self, diagnostic_id: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail


@dataclass(frozen=True)
class FontMetrics:
    metrics_path: Path
    metrics_content_identity: str
    font_path: Path
    content_identity: str
    family: str
    units_per_em: int
    ascent: int
    descent: int
    cap_height: int
    advances: dict[int, int]

    def width(self, value: str, size: float, letter_spacing: float = 0) -> float:
        total = 0
        for character in value:
            codepoint = ord(character)
            advance = self.advances.get(codepoint)
            if advance is None:
                if codepoint <= 0x1F or codepoint == 0x7F:
                    continue
                raise FontMetricsError(
                    "E_FONT_GLYPH_UNAVAILABLE",
                    f"{self.family} has no metric for U+{codepoint:04X} in {value!r}",
                )
            total += advance
        return total / self.units_per_em * size + max(0, len(value) - 1) * letter_spacing

    def baseline(self, top: float, size: float, line_height: float) -> float:
        line = size * line_height
        return top + (line - size) / 2 + size * self.ascent / self.units_per_em

    def cap_height_at(self, size: float) -> float:
        return size * self.cap_height / self.units_per_em


@dataclass(frozen=True)
class FontFile:
    """One identity-pinned rasterizable font asset declared by a Context."""

    path: Path
    content_identity: str
    family: str
    weight: int


def _families(font_stack: str) -> list[str]:
    return [family.strip().strip("'\"") for family in font_stack.split(",") if family.strip()]


def _safe_path(root: Path | None, relative: object) -> Path | None:
    if not isinstance(relative, str):
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    if root is not None:
        path = (root.resolve() / candidate).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            return None
        return path if path.is_file() else None
    resource = files("chrona.resources").joinpath(*candidate.parts)
    return Path(str(resource)) if resource.is_file() else None


def _identity(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def resolve_font_metrics(font_stack: str, descriptor: dict, *, weight: int = 400,
                         asset_root: Path | None = None) -> FontMetrics:
    """Resolve one exact metrics/font pair from a declared Context closure."""
    if descriptor.get("algorithm") != "declared-metrics-v2" or descriptor.get("missingFont") != "diagnose":
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    assets = descriptor.get("assets")
    families = _families(font_stack)
    if not isinstance(assets, list) or not assets or not families:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    for family in families:
        asset = next((item for item in assets if isinstance(item, dict)
                      and item.get("family", "").casefold() == family.casefold()
                      and item.get("weight") == weight), None)
        if asset is None:
            continue
        metrics, font = asset.get("metrics"), asset.get("font")
        if not isinstance(metrics, dict) or not isinstance(font, dict):
            continue
        metrics_path = _safe_path(asset_root, metrics.get("path"))
        font_path = _safe_path(asset_root, font.get("path"))
        if metrics_path is None or font_path is None:
            continue
        metrics_identity, font_identity = _identity(metrics_path), _identity(font_path)
        if metrics.get("contentIdentity") != metrics_identity or font.get("contentIdentity") != font_identity:
            continue
        try:
            table = json.loads(metrics_path.read_bytes())
            if (table.get("version") != "chrona/font-metrics/v2"
                    or table.get("family", "").casefold() != family.casefold()
                    or table.get("weight") != weight
                    or table.get("sourceContentIdentity") != font_identity):
                continue
            units, ascent, descent, cap_height = (int(table[key]) for key in ("unitsPerEm", "ascent", "descent", "capHeight"))
            advances = {int(code): int(value) for code, value in table["advances"].items()}
            if units <= 0 or cap_height <= 0 or cap_height > units or any(code < 0 or value < 0 for code, value in advances.items()):
                continue
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        return FontMetrics(metrics_path, metrics_identity, font_path, font_identity, family,
                           units, ascent, descent, cap_height, advances)
    raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")


def resolve_font_files(descriptor: dict, *, asset_root: Path | None) -> tuple[tuple[FontFile, ...], tuple[str, ...]]:
    """Return the unique, identity-checked font files declared by one Context."""
    if descriptor.get("algorithm") != "declared-metrics-v2":
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    assets = descriptor.get("assets")
    if not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    files_by_identity: dict[str, FontFile] = {}
    for asset in assets:
        font = asset.get("font") if isinstance(asset, dict) else None
        if not isinstance(font, dict):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
        family = asset.get("family") if isinstance(asset, dict) else None
        path = _safe_path(asset_root, font.get("path"))
        if not isinstance(family, str) or not family or path is None or font.get("contentIdentity") != _identity(path):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
        identity = str(font["contentIdentity"])
        declared = FontFile(path, identity, family, int(asset["weight"]))
        previous = files_by_identity.setdefault(identity, declared)
        if previous.family.casefold() != declared.family.casefold() or previous.weight != declared.weight:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    return tuple(files_by_identity[key] for key in sorted(files_by_identity)), tuple(sorted(files_by_identity))
