"""Completed semantic legend ink, independent of period or scale identities."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.theme_paint import ThemePaintWitness


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

    @property
    def identity(self) -> tuple[object, ...]:
        return self.family, self.paint.identity, self.pattern_identity

    @property
    def key_id(self) -> str:
        digest = sha256(repr(self.identity).encode("utf-8")).hexdigest()[:16]
        return f"{self.family}:{digest}"
