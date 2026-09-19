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


def resolve_font_metrics(font_stack: str, descriptor: dict) -> FontMetrics:
    """Resolve the declared stack through fontconfig and verify its identity."""
    family = font_stack.split(",", 1)[0].strip()
    match = subprocess.run(["fc-match", "-f", "%{file}", family], check=True, capture_output=True, text=True).stdout.strip()
    path = Path(match)
    if not path.is_file():
        raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
    identity = "sha256:" + sha256(path.read_bytes()).hexdigest()
    requested = descriptor["contentIdentity"]
    if requested.endswith("0" * 64) or requested != identity:
        raise PresentationSettingsError("E_FONT_METRICS_UNAVAILABLE")
    font = TTFont(path)
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"].metrics
    advances = {code: hmtx[name][0] for code, name in cmap.items() if name in hmtx}
    units = font["head"].unitsPerEm
    hhea = font["hhea"]
    default = hmtx.get(".notdef", (units, 0))[0]
    return FontMetrics(path, identity, units, hhea.ascent, hhea.descent, advances, default)
