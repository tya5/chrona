"""Deterministic font selection and glyph metrics for presentation v0.2."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from chrona.presentation.presentation_settings import PresentationSettingsError


@dataclass(frozen=True)
class FontMetrics:
    path: Path
    content_identity: str
    units_per_em: int
    ascent: int
    descent: int
    advances: dict[int, int]
    default_advance: int

    def width(self, value: str, size: float, letter_spacing: float = 0) -> float:
        return sum(self.advances.get(ord(char), self.default_advance) for char in value) / self.units_per_em * size + max(0, len(value) - 1) * letter_spacing

    def baseline(self, top: float, size: float, line_height: float) -> float:
        line = size * line_height
        return top + (line - size) / 2 + size * self.ascent / self.units_per_em


def _families(font_stack: str) -> list[str]:
    return [family.strip().strip("'\"") for family in font_stack.split(",") if family.strip()]


def resolve_font_metrics(font_stack: str, descriptor: dict, *, weight: int = 400,
                         asset_root: Path | None = None) -> FontMetrics:
    """Resolve an exact declared family/weight metrics table."""
    assets = descriptor.get("assets")
    if not isinstance(assets, list) or not assets:
        raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
    families = _families(font_stack)
    if not families:
        raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
    allow_fallback = descriptor.get("missingFont") == "declared-fallback"
    for index, family in enumerate(families):
        if index and not allow_fallback:
            raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
        declared = next((asset for asset in assets if asset.get("family", "").casefold() == family.casefold() and asset.get("weight") == weight), None)
        if declared is None:
            continue
        raw_path = declared.get("path")
        if not isinstance(raw_path, str):
            continue
        relative = Path(raw_path)
        root = (asset_root or Path(__file__).resolve().parents[3]).resolve()
        if relative.is_absolute() or ".." in relative.parts:
            continue
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        payload = path.read_bytes()
        identity = "sha256:" + sha256(payload).hexdigest()
        requested = declared.get("contentIdentity")
        if not requested or requested.endswith("0" * 64) or requested != identity:
            continue
        try:
            table = json.loads(payload)
            if (table.get("version") != "chrona/font-metrics/v1"
                    or table.get("family", "").casefold() != family.casefold()
                    or table.get("weight") != weight):
                continue
            units = int(table["unitsPerEm"])
            ascent = int(table["ascent"])
            descent = int(table["descent"])
            default = int(table["defaultAdvance"])
            advances = {int(code): int(value) for code, value in table["advances"].items()}
            if units <= 0 or default < 0 or any(code < 0 or value < 0 for code, value in advances.items()):
                continue
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        return FontMetrics(path, identity, units, ascent, descent, advances, default)
    else:
        raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
