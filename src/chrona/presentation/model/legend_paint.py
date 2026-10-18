"""Completed semantic legend ink, independent of period or scale identities."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.theme_paint import ThemePaintWitness


@dataclass(frozen=True)
class RealizedGlyphInk:
    """Closed glyph selection, canonical structure and ordered part paint."""

    selected_role: str | None
    geometry_identity: tuple[object, ...]
    paints: tuple[ThemePaintWitness, ...]
    footprint: tuple[float, float]

    @property
    def identity(self) -> tuple[object, ...]:
        return self.geometry_identity, tuple(paint.identity for paint in self.paints)


@dataclass(frozen=True)
class RealizedLegendKey:
    """A measured candidate and its exact completed paint/source witnesses."""

    family: str
    paint_role: str
    paint: ThemePaintWitness
    occurrences: tuple[StyleOccurrenceKey, ...] = ()
    variance_classes: tuple[str, ...] = ()
    pattern_identity: tuple[object, ...] | None = None
    base_label: str = ""
    glyph: RealizedGlyphInk | None = None

    @property
    def identity(self) -> tuple[object, ...]:
        if self.glyph is not None:
            return self.family, ("glyph", self.glyph.identity), self.pattern_identity
        return self.family, self.paint.identity, self.pattern_identity

    @property
    def key_id(self) -> str:
        digest = sha256(repr(self.identity).encode("utf-8")).hexdigest()[:16]
        return f"{self.family}:{digest}"
