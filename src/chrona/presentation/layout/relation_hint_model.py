"""Neutral prior geometry: no artifact reader or Scene projection dependency."""
from __future__ import annotations

from dataclasses import dataclass

Point = tuple[float, float]


@dataclass(frozen=True)
class HintMarker:
    outline: tuple[tuple[str, tuple[Point, ...]], ...]
    head_length: float
    head_width: float
    attachment_offset: float
    paint_mode: str


@dataclass(frozen=True)
class HintMark:
    placement_id: str
    source_ref: str
    kind: str
    purpose: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class HintRelation:
    source_ref: str
    from_instance_id: str
    to_instance_id: str
    points: tuple[Point, ...]
    marker_start: HintMarker | None
    marker_end: HintMarker | None


@dataclass(frozen=True)
class HintSurface:
    surface_id: str
    marks: tuple[HintMark, ...]
    relations: tuple[HintRelation, ...]


@dataclass(frozen=True)
class PreviousRouteHints:
    has_endpoint_identity: bool
    surfaces: tuple[HintSurface, ...]
    theme_identity: str | None
    terminal_provenance_compatible: bool = False
