"""Finite, deterministic label placement shared by presentation adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class LabelRect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass(frozen=True)
class LabelPlacement:
    side: str
    bounds: LabelRect


@dataclass(frozen=True)
class LabelRequest:
    """One semantic plot-text request awaiting deterministic Layout placement."""

    placement_id: str
    source_ref: str
    content: str
    anchor: LabelRect
    candidates: tuple[str, ...]
    typography_role: str
    collision_region: str
    overflow: str
    wrap: str = "forbid"


def _intersects(a: LabelRect, b: LabelRect) -> bool:
    return a.x < b.right and b.x < a.right and a.y < b.bottom and b.y < a.bottom


def _candidate(anchor: LabelRect, size: tuple[float, float], side: str, gap: float) -> LabelRect:
    width, height = size
    if width <= 0 or height <= 0 or gap < 0:
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    if side == "above":
        return LabelRect(anchor.x + (anchor.width - width) / 2, anchor.y - gap - height, width, height)
    if side == "below":
        return LabelRect(anchor.x + (anchor.width - width) / 2, anchor.bottom + gap, width, height)
    if side == "start":
        return LabelRect(anchor.x - gap - width, anchor.y + (anchor.height - height) / 2, width, height)
    if side == "end":
        return LabelRect(anchor.right + gap, anchor.y + (anchor.height - height) / 2, width, height)
    if side == "inside":
        if width > anchor.width or height > anchor.height:
            raise ValueError("E_PRESENTATION_LABEL_UNPLACEABLE")
        return LabelRect(anchor.x + (anchor.width - width) / 2, anchor.y + (anchor.height - height) / 2, width, height)
    raise ValueError("E_PRESENTATION_LABEL_INPUT")


def place_label(anchor: LabelRect, size: tuple[float, float], candidates: Iterable[str], *,
                bounds: LabelRect, obstacles: Iterable[LabelRect] = (), gap: float = 0,
                required: bool = True, overflow: str = "diagnose") -> LabelPlacement | None:
    """Choose the first legal candidate in declared order; never search indefinitely."""
    sides = tuple(candidates)
    if not 1 <= len(sides) <= 16 or len(set(sides)) != len(sides) or overflow not in {"diagnose", "suppress", "clip-optional"}:
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    blocked = tuple(obstacles)
    for side in sides:
        try:
            candidate = _candidate(anchor, size, side, gap)
        except ValueError as exc:
            if str(exc) == "E_PRESENTATION_LABEL_UNPLACEABLE":
                continue
            raise
        if candidate.x < bounds.x or candidate.y < bounds.y or candidate.right > bounds.right or candidate.bottom > bounds.bottom:
            continue
        if not any(_intersects(candidate, obstacle) for obstacle in blocked):
            return LabelPlacement(side, candidate)
    if required or overflow == "diagnose":
        raise ValueError("E_PRESENTATION_LABEL_UNPLACEABLE")
    return None
