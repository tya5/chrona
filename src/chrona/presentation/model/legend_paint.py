"""Completed semantic legend ink, independent of period or scale identities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Literal

from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.theme_paint import ThemePaintWitness
from chrona.presentation.style import EncodingWitness, LegendEncodingCoverage


_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _normalized_color(value: str) -> str:
    return value.upper() if _HEX_COLOR.fullmatch(value) else value


def _visible_channels(paint: ThemePaintWitness) -> tuple[tuple[object, ...], tuple[object, ...]]:
    """Return visible fill and stroke inks separately for one completed paint."""
    channels = paint.effective_channels
    opacity = channels.opacity if channels.opacity is not None else Decimal(1)
    if opacity == 0:
        return (), ()
    fills = []
    strokes = []
    if channels.fill is not None:
        gradient = (paint.gradient.identity if paint.gradient is not None and paint.gradient.admitted
                    else None)
        fills.append((("gradient", gradient) if gradient is not None
                      else ("color", _normalized_color(channels.fill)), opacity))
    if channels.stroke is not None:
        strokes.append((("color", _normalized_color(channels.stroke)), opacity))
    return tuple(fills), tuple(strokes)


def effective_ink_identity(paints: tuple[ThemePaintWitness, ...],
                           pattern_identity: tuple[object, ...] | None = None) -> tuple[object, ...]:
    """Normalize a figure's emitted ink, preferring fill palette over its border."""
    fills, strokes = [], []
    for paint in paints:
        fill_inks, stroke_inks = _visible_channels(paint)
        fills.extend(fill_inks)
        strokes.extend(stroke_inks)
    palette = tuple(sorted(set(fills or strokes), key=repr))
    return palette, pattern_identity


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

    @property
    def ink_identity(self) -> tuple[object, ...]:
        return effective_ink_identity(self.paints)[0]


@dataclass(frozen=True)
class PointStateEncodingWitness:
    """Actual occurrence ink retained behind a neutral state representative."""

    occurrence: StyleOccurrenceKey
    encoding: EncodingWitness
    paints: tuple[ThemePaintWitness, ...]


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
    point_state: Literal["planned", "actual", "forecast"] | None = None
    covered_point_states: tuple[Literal["planned", "actual", "forecast"], ...] = ()
    encoding_witnesses: tuple[PointStateEncodingWitness, ...] = ()

    @property
    def legend_encoding_coverage(self) -> LegendEncodingCoverage | None:
        witnesses = tuple(dict.fromkeys(item.encoding for item in self.encoding_witnesses))
        return LegendEncodingCoverage("state", witnesses) if witnesses else None

    @property
    def point_states(self) -> tuple[str, ...]:
        return self.covered_point_states or ((self.point_state,) if self.point_state is not None else ())

    @property
    def identity(self) -> tuple[object, ...]:
        if self.glyph is not None:
            identity = self.family, ("glyph", self.glyph.identity), self.pattern_identity
        else:
            identity = self.family, self.paint.identity, self.pattern_identity
        return identity if self.point_state is None else (*identity[:1], "point", *identity[1:])

    @property
    def ink_identity(self) -> tuple[object, ...]:
        """Visible colour identity, deliberately independent of channel and glyph geometry."""
        paints = self.glyph.paints if self.glyph is not None else (self.paint,)
        return effective_ink_identity(paints, self.pattern_identity)

    @property
    def grouping_identity(self) -> tuple[object, ...]:
        """Semantic family plus visible ink; exact paint remains in ``identity``."""
        if self.point_state is None:
            return self.family, self.ink_identity
        witness = (("glyph", self.glyph.identity) if self.glyph is not None
                   else ("paint", self.paint.identity))
        return self.family, "point", witness, self.pattern_identity

    @property
    def key_id(self) -> str:
        digest = sha256(repr(self.grouping_identity).encode("utf-8")).hexdigest()[:16]
        return f"{self.family}:{digest}"
