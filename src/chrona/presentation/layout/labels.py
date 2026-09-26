"""Finite, deterministic label placement shared by presentation adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex


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
    visible_overflow: bool = False


@dataclass(frozen=True)
class LabelObstacle:
    """A completed Layout obstacle, retaining the placement that owns it."""

    placement_id: str
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
    collision_domain: CollisionDomain
    overflow: str
    wrap: str = "forbid"
    bounds: LabelRect | None = None
    inside_host_obstacle_id: str | None = None
    visible_fallback_side: str | None = None


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


def _visible_candidate(anchor: LabelRect, size: tuple[float, float], side: str, gap: float) -> LabelRect:
    """Return a deterministic preferred label position without fit rejection."""
    if side == "inside":
        width, height = size
        if width <= 0 or height <= 0 or gap < 0:
            raise ValueError("E_PRESENTATION_LABEL_INPUT")
        return LabelRect(anchor.x + (anchor.width - width) / 2,
                         anchor.y + (anchor.height - height) / 2, width, height)
    return _candidate(anchor, size, side, gap)


def place_label(anchor: LabelRect, size: tuple[float, float], candidates: Iterable[str], *,
                bounds: LabelRect, obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex = (), gap: float = 0,
                inside_host_obstacle_id: str | None = None,
                required: bool = True, overflow: str = "visible-overflow",
                visible_fallback_side: str | None = None) -> LabelPlacement | None:
    """Choose the first legal candidate in declared order; never search indefinitely."""
    sides = tuple(candidates)
    if (not 1 <= len(sides) <= 16 or len(set(sides)) != len(sides)
            or overflow not in {"visible-overflow", "suppress", "clip-optional"}
            or (visible_fallback_side is not None
                and (overflow != "visible-overflow"
                     or visible_fallback_side not in {"above", "below", "start", "end", "inside"}))):
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    blocked = () if index is not None else tuple(obstacles)
    for side in sides:
        try:
            candidate = _candidate(anchor, size, side, gap)
        except ValueError as exc:
            if str(exc) == "E_PRESENTATION_LABEL_UNPLACEABLE":
                continue
            raise
        if candidate.x < bounds.x or candidate.y < bounds.y or candidate.right > bounds.right or candidate.bottom > bounds.bottom:
            continue
        if index is not None:
            collides = bool(index.collisions(
                ObstacleRect(candidate.x, candidate.y, candidate.right, candidate.bottom),
                host_id=inside_host_obstacle_id if side == "inside" else None))
        else:
            active_obstacles = (obstacle for obstacle in blocked
                                if not (side == "inside" and isinstance(obstacle, LabelObstacle)
                                        and obstacle.placement_id == inside_host_obstacle_id))
            collides = any(_intersects(candidate, obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle)
                           for obstacle in active_obstacles)
        if not collides:
            return LabelPlacement(side, candidate)
    if overflow == "visible-overflow":
        # Ordinary requests retain their first ranked side. A separately
        # declared terminal side is used only after all ranked candidates fail.
        for side in ((visible_fallback_side,) if visible_fallback_side is not None else sides):
            try:
                return LabelPlacement(side, _visible_candidate(anchor, size, side, gap), True)
            except ValueError as exc:
                if str(exc) != "E_PRESENTATION_LABEL_UNPLACEABLE":
                    raise
        raise ValueError("E_PRESENTATION_LABEL_UNPLACEABLE")
    if required:
        raise ValueError("E_PRESENTATION_LABEL_UNPLACEABLE")
    return None
