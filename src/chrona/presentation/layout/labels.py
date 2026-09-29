"""Finite, deterministic label placement shared by presentation adapters."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
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
    search_count: int = 0


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
    rule_host_obstacle_id: str | None = None
    semantic_id: str = ""
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    lane_source_kind: str | None = None


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
                visible_fallback_side: str | None = None,
                rule_host_obstacle_id: str | None = None,
                classes: tuple[str, ...] | None = None,
                search_side_neighborhood: bool = False,
                maximum_side_gap: float | None = None) -> LabelPlacement | None:
    """Choose the first legal candidate in declared order; never search indefinitely."""
    sides = tuple(candidates)
    if (not 1 <= len(sides) <= 16 or len(set(sides)) != len(sides)
            or overflow not in {"visible-overflow", "suppress", "clip-optional"}
            or (visible_fallback_side is not None
                and (overflow != "visible-overflow"
                     or visible_fallback_side not in {"above", "below", "start", "end", "inside"}))
            or (maximum_side_gap is not None
                and (isinstance(maximum_side_gap, bool)
                     or not isfinite(maximum_side_gap) or maximum_side_gap < 0))):
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    blocked = () if index is not None else tuple(obstacles)

    def legal(candidate: LabelRect, side: str) -> bool:
        if (candidate.x < bounds.x or candidate.y < bounds.y
                or candidate.right > bounds.right or candidate.bottom > bounds.bottom):
            return False
        if index is not None:
            return not index.collisions(
                ObstacleRect(candidate.x, candidate.y, candidate.right, candidate.bottom),
                host_id=inside_host_obstacle_id if side == "inside" else None,
                rule_host_id=rule_host_obstacle_id, classes=classes)
        active_obstacles = (obstacle for obstacle in blocked
                            if not (side == "inside" and isinstance(obstacle, LabelObstacle)
                                    and obstacle.placement_id == inside_host_obstacle_id))
        return not any(_intersects(candidate, obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle)
                       for obstacle in active_obstacles)

    for side in sides:
        if (maximum_side_gap is not None and side in {"end", "start"}
                and gap > maximum_side_gap):
            continue
        try:
            candidate = _candidate(anchor, size, side, gap)
        except ValueError as exc:
            if str(exc) == "E_PRESENTATION_LABEL_UNPLACEABLE":
                continue
            raise
        if legal(candidate, side):
            return LabelPlacement(side, candidate)
    if search_side_neighborhood:
        lattice = 8.0
        nearby: list[tuple[float, int, float, float, str, LabelRect]] = []
        for rank, side in enumerate(sides):
            if side == "inside":
                continue
            base = _candidate(anchor, size, side, gap)
            tangent_bound = size[0] if side in {"above", "below"} else size[1]
            outward_bound = size[1] if side in {"above", "below"} else size[0]
            for outward_step in range(ceil(outward_bound / lattice) + 1):
                outward = outward_step * lattice
                if outward > outward_bound:
                    continue
                if (maximum_side_gap is not None and side in {"end", "start"}
                        and gap + outward > maximum_side_gap):
                    continue
                for tangent_step in range(-ceil(tangent_bound / lattice), ceil(tangent_bound / lattice) + 1):
                    tangent = tangent_step * lattice
                    if abs(tangent) > tangent_bound or (outward == 0 and tangent == 0):
                        continue
                    displaced = (LabelRect(base.x + tangent, base.y - outward, base.width, base.height)
                                 if side == "above" else
                                 LabelRect(base.x + tangent, base.y + outward, base.width, base.height)
                                 if side == "below" else
                                 LabelRect(base.x - outward, base.y + tangent, base.width, base.height)
                                 if side == "start" else
                                 LabelRect(base.x + outward, base.y + tangent, base.width, base.height))
                    nearby.append((abs(tangent) + outward, rank, outward, tangent, side, displaced))
        nearby.sort(key=lambda item: item[:4])
        for count, (_, _, _, _, side, candidate) in enumerate(nearby[:512], start=1):
            if legal(candidate, side):
                return LabelPlacement(side, candidate, search_count=count)
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


def place_member_name(
    anchor: LabelRect,
    size: tuple[float, float],
    candidates: Iterable[str],
    *,
    bounds: LabelRect,
    obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex = (),
    gap: float,
    maximum_end_gap: float,
    text_inline_inset: float = 0.0,
    inside_host_obstacle_id: str | None = None,
    classes: tuple[str, ...] | None = None,
) -> LabelPlacement | None:
    """Try declared member-name sides in order, bounding end gap to completed text.

    ``text_inline_inset`` is the distance from the searched label box's left
    edge to its completed Text bounds (for example chip padding and a leading
    visual).  Only the end-side trial is capped; the declared next side remains
    available before the caller records a typed suppression.
    """
    sides = tuple(candidates)
    if (not sides or len(sides) > 16 or len(set(sides)) != len(sides)
            or any(side not in {"above", "below", "start", "end", "inside"} for side in sides)
            or any(isinstance(value, bool) or not isfinite(value) or value < 0
                   for value in (gap, maximum_end_gap, text_inline_inset))):
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    available_obstacles = (obstacles if isinstance(obstacles, SurfaceObstacleIndex)
                           else tuple(obstacles))
    for side in sides:
        maximum_side_gap = (maximum_end_gap - text_inline_inset) if side == "end" else None
        if side == "end" and maximum_side_gap < gap:
            continue
        if side not in {"end", "start"}:
            # Member names use the lane's inline rungs. Keep the established
            # finite behavior for any legacy caller that declares another side.
            placed = place_label(
                anchor, size, (side,), bounds=bounds, obstacles=available_obstacles, gap=gap,
                inside_host_obstacle_id=inside_host_obstacle_id,
                required=False, overflow="suppress", classes=classes,
                search_side_neighborhood=True, maximum_side_gap=maximum_side_gap,
            )
            if placed is not None:
                return placed
            continue

        # At a fixed inline position, the legal block positions form components
        # separated by obstacle-contact intervals. Their nearest points to the
        # preferred anchor position are the row edges and obstacle contacts.
        # Querying those events through the canonical collision predicate makes
        # the search complete for the axis-aligned lane obstacles without a
        # sampling lattice or candidate cutoff.
        preferred = _candidate(anchor, size, side, gap)
        candidates = {preferred.y, bounds.y, bounds.bottom - preferred.height}
        if isinstance(available_obstacles, SurfaceObstacleIndex):
            obstacle_values = available_obstacles.select()
            for obstacle in obstacle_values:
                if not isinstance(obstacle.geometry, ObstacleRect):
                    continue
                clearance = obstacle.clearance
                candidates.add(obstacle.geometry.top - preferred.height - clearance)
                candidates.add(obstacle.geometry.bottom + clearance)
        else:
            for obstacle in available_obstacles:
                rect = obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle
                candidates.add(rect.y - preferred.height)
                candidates.add(rect.bottom)

        legal_positions = []
        for y in candidates:
            candidate = LabelRect(preferred.x, y, preferred.width, preferred.height)
            if candidate.y < bounds.y or candidate.bottom > bounds.bottom:
                continue
            if side == "end" and candidate.x + text_inline_inset - anchor.right > maximum_end_gap:
                continue
            if isinstance(available_obstacles, SurfaceObstacleIndex):
                collides = bool(available_obstacles.collisions(
                    ObstacleRect(candidate.x, candidate.y, candidate.right, candidate.bottom),
                    host_id=inside_host_obstacle_id if side == "inside" else None,
                    classes=classes,
                ))
            else:
                collides = any(_intersects(candidate, item.bounds if isinstance(item, LabelObstacle) else item)
                               for item in available_obstacles)
            if not collides:
                legal_positions.append(candidate)
        if legal_positions:
            selected = min(legal_positions, key=lambda rect: (abs(rect.y - preferred.y), rect.y))
            return LabelPlacement(side, selected, search_count=len(candidates))
    return None
