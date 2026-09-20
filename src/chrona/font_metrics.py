"""Deterministic font selection and glyph metrics for presentation v0.2."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess

from fontTools.ttLib import TTFont

from .presentation_settings import PresentationSettingsError


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


def resolve_font_metrics(font_stack: str, descriptor: dict, *, weight: int = 400) -> FontMetrics:
    """Resolve an exact declared family/weight asset through fontconfig."""
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
        style = "Regular" if weight == 400 else "Bold" if weight == 700 else None
        pattern = f"{family}:style={style}" if style else f"{family}:weight={weight}"
        match = subprocess.run(["fc-match", "-f", "%{file}", pattern], check=True, capture_output=True, text=True).stdout.strip()
        path = Path(match)
        if not path.is_file():
            continue
        identity = "sha256:" + sha256(path.read_bytes()).hexdigest()
        requested = declared.get("contentIdentity")
        actual_weight = TTFont(path)["OS/2"].usWeightClass
        if requested and not requested.endswith("0" * 64) and requested == identity and actual_weight == weight:
            break
    else:
        raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
    font = TTFont(path)
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"].metrics
    advances = {code: hmtx[name][0] for code, name in cmap.items() if name in hmtx}
    units = font["head"].unitsPerEm
    hhea = font["hhea"]
    default = hmtx.get(".notdef", (units, 0))[0]
    return FontMetrics(path, identity, units, hhea.ascent, hhea.descent, advances, default)
