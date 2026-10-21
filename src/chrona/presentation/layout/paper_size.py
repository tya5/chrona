"""Physical named-page dimensions used as Draft viewport defaults.

This module is deliberately a small pure model: it maps the closed page-size
vocabulary to CSS-pixel dimensions, without choosing when a caller applies the
default or rounding dimensions for an output adapter.
"""
from __future__ import annotations

from fractions import Fraction
from types import MappingProxyType
from typing import Mapping


# Values are width, height, unit in portrait orientation. Landscape entries
# are explicit members of the same registry so the runtime vocabulary has one
# authoritative source and callers never infer formats from arbitrary text.
_PAGE_SIZE_IN_PHYSICAL_UNITS: Mapping[str, tuple[int, int, str]] = MappingProxyType({
    "a3-portrait": (297, 420, "mm"),
    "a3-landscape": (420, 297, "mm"),
    "a4-portrait": (210, 297, "mm"),
    "a4-landscape": (297, 210, "mm"),
    "a5-portrait": (148, 210, "mm"),
    "a5-landscape": (210, 148, "mm"),
    "letter-portrait": (17, 22, "in-half"),
    "letter-landscape": (22, 17, "in-half"),
    "legal-portrait": (17, 28, "in-half"),
    "legal-landscape": (28, 17, "in-half"),
})

PAGE_SIZE_NAMES = tuple(_PAGE_SIZE_IN_PHYSICAL_UNITS)


def viewport_for_page_size(page_size: str) -> tuple[float, float]:
    """Return named paper width and height in fractional CSS pixels.

    CSS defines 96 px/in and 25.4 mm/in. US page dimensions are stored as
    integer half-inches to preserve their exact 8.5-inch width. No integer
    pixel rounding is performed here; adapters own any output discretization.
    """
    try:
        width, height, unit = _PAGE_SIZE_IN_PHYSICAL_UNITS[page_size]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown named page size: {page_size!r}") from exc

    if unit == "mm":
        css_px_per_unit = Fraction(480, 127)  # 96 / 25.4, exactly
        scale = css_px_per_unit
    else:
        scale = Fraction(96, 2)  # dimensions are in half-inches
    return float(width * scale), float(height * scale)
