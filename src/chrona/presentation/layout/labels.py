"""Finite, deterministic label placement shared by presentation adapters."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from math import hypot
from typing import Callable, Iterable

from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    SurfaceObstacleIndex,
    obstacle_envelope,
)


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


def nearest_rect_perimeters(label: LabelRect, mark: LabelRect) -> tuple[float, tuple[float, float], tuple[float, float]]:
    """Return nearest perimeter distance and points, with stable side tie order."""
    overlap_left, overlap_right = max(label.x, mark.x), min(label.right, mark.right)
    overlap_top, overlap_bottom = max(label.y, mark.y), min(label.bottom, mark.bottom)
    if overlap_left < overlap_right and overlap_top < overlap_bottom:
        label_contains = (label.x <= mark.x and label.y <= mark.y
                          and label.right >= mark.right and label.bottom >= mark.bottom)
        mark_contains = (mark.x <= label.x and mark.y <= label.y
                         and mark.right >= label.right and mark.bottom >= label.bottom)
        if not label_contains and not mark_contains:
            point = (overlap_left, overlap_top)
            return 0.0, point, point
        if label_contains and mark_contains:
            point = (label.x, label.y)
            return 0.0, point, point
        inner, outer = (mark, label) if label_contains else (label, mark)
        options = (
            (inner.x - outer.x, 0, (inner.x, min(max((inner.y + inner.bottom) / 2, outer.y), outer.bottom)),
             (outer.x, min(max((inner.y + inner.bottom) / 2, outer.y), outer.bottom))),
            (outer.right - inner.right, 1, (inner.right, min(max((inner.y + inner.bottom) / 2, outer.y), outer.bottom)),
             (outer.right, min(max((inner.y + inner.bottom) / 2, outer.y), outer.bottom))),
            (inner.y - outer.y, 2, (min(max((inner.x + inner.right) / 2, outer.x), outer.right), inner.y),
             (min(max((inner.x + inner.right) / 2, outer.x), outer.right), outer.y)),
            (outer.bottom - inner.bottom, 3, (min(max((inner.x + inner.right) / 2, outer.x), outer.right), inner.bottom),
             (min(max((inner.x + inner.right) / 2, outer.x), outer.right), outer.bottom)),
        )
        distance, _side, first, second = min(options, key=lambda item: (item[0], item[1]))
        source, target = (second, first) if label_contains else (first, second)
        return distance, source, target
    candidates: list[tuple[float, int, tuple[float, float], tuple[float, float]]] = []
    # For each label perimeter side, clamp its orthogonal coordinate to the
    # host perimeter; ties follow start, end, top, bottom as specified by #554.
    middle_y = (label.y + label.bottom) / 2
    middle_x = (label.x + label.right) / 2
    mark_y = min(max(middle_y, mark.y), mark.bottom)
    mark_x = min(max(middle_x, mark.x), mark.right)
    label_y = min(max(mark_y, label.y), label.bottom)
    label_x = min(max(mark_x, label.x), label.right)
    candidates.extend((
        (hypot(mark.x - label.right, mark_y - label_y), 0,
         (label.right, label_y), (mark.x, mark_y)),
        (hypot(label.x - mark.right, mark_y - label_y), 1,
         (label.x, label_y), (mark.right, mark_y)),
        (hypot(mark.y - label.bottom, mark_x - label_x), 2,
         (label_x, label.bottom), (mark_x, mark.y)),
        (hypot(label.y - mark.bottom, mark_x - label_x), 3,
         (label_x, label.y), (mark_x, mark.bottom)),
    ))
    distance, _side, source, target = min(candidates, key=lambda item: (item[0], item[1]))
    return distance, source, target


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
class MemberNameAssociation:
    """Measured Text footprint and its exact completed marks, in Layout space.

    ``mark`` is the requested host; ``also_marks`` are the item's other own drawn
    marks (an actual or baseline mark). The Text is associated when it is within
    ``maximum_distance`` of at least one of them.
    """

    mark: LabelRect
    text_inline_inset: float
    text_block_inset: float
    text_width: float
    text_height: float
    maximum_distance: float
    also_marks: tuple[LabelRect, ...] = ()

    def distances(self, footprint: LabelRect) -> tuple[float, ...]:
        """Nearest-perimeter gap from the completed Text to ``mark``, then each of ``also_marks``."""
        text = LabelRect(footprint.x + self.text_inline_inset,
                         footprint.y + self.text_block_inset,
                         self.text_width, self.text_height)
        return tuple(nearest_rect_perimeters(text, mark)[0] for mark in (self.mark, *self.also_marks))

    def nearest_mark_index(self, footprint: LabelRect) -> int:
        """Index in ``(mark, *also_marks)`` of the nearest own mark; a tie keeps the earlier one."""
        values = self.distances(footprint)
        return values.index(min(values))

    def allows(self, footprint: LabelRect) -> bool:
        return min(self.distances(footprint)) <= self.maximum_distance + 1e-9


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
                maximum_side_gap: float | None = None,
                candidate_filter: Callable[[LabelRect], bool] | None = None) -> LabelPlacement | None:
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
        if candidate_filter is not None and not candidate_filter(candidate):
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
    full_band: bool = False,
    association: MemberNameAssociation | None = None,
    maximum_stagger: float | None = None,
    overflow: str = "suppress",
    visible_fallback_side: str | None = None,
    own_mark_right: float | None = None,
) -> LabelPlacement | None:
    """Try declared member-name sides in order, bounding end gap to completed text.

    ``own_mark_right`` is the right edge of the item's last own drawn mark. The
    ``end`` side starts and is bounded from it when it passes the anchor's right
    edge; every other side keeps the anchor.

    ``association`` checks the completed Text, not its decorative footprint,
    against the exact host mark. Full-band lane contacts may move by at most
    one measured stagger step; a failed contact proceeds to the declared side.
    """
    sides = tuple(candidates)
    if not sides:
        return None
    if (len(sides) > 16 or len(set(sides)) != len(sides)
            or any(side not in {"above", "below", "start", "end", "inside"} for side in sides)
            or any(isinstance(value, bool) or not isfinite(value) or value < 0
                   for value in (gap, maximum_end_gap, text_inline_inset))
            or (maximum_stagger is not None and
                (isinstance(maximum_stagger, bool) or not isfinite(maximum_stagger)
                 or maximum_stagger < 0))
            or (own_mark_right is not None and
                (isinstance(own_mark_right, bool) or not isfinite(own_mark_right)))
            or overflow not in {"suppress", "visible-overflow", "diagnose"}
            or (visible_fallback_side is not None and
                (overflow != "visible-overflow" or visible_fallback_side not in sides))):
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    available_obstacles = (obstacles if isinstance(obstacles, SurfaceObstacleIndex)
                           else tuple(obstacles))
    end_anchor = (anchor if own_mark_right is None or own_mark_right <= anchor.right
                  else LabelRect(anchor.x, anchor.y, own_mark_right - anchor.x, anchor.height))
    for side in sides:
        side_anchor = end_anchor if side == "end" else anchor
        maximum_side_gap = (maximum_end_gap - text_inline_inset) if side == "end" else None
        if side == "end" and maximum_side_gap < gap:
            continue
        if not full_band or side not in {"end", "start"}:
            # Full-band contacts apply only to lane names. Other labels retain
            # their established side-neighborhood policy and public bytes.
            placed = place_label(
                side_anchor, size, (side,), bounds=bounds, obstacles=available_obstacles, gap=gap,
                inside_host_obstacle_id=inside_host_obstacle_id,
                required=False, overflow="suppress", classes=classes,
                search_side_neighborhood=True, maximum_side_gap=maximum_side_gap,
                candidate_filter=association.allows if association is not None else None,
            )
            if placed is not None:
                return placed
            continue

        # At a fixed inline position, the legal block positions form components
        # separated by obstacle-contact intervals. Their nearest points to the
        # preferred anchor position are the row edges and obstacle contacts.
        # Rectangles (and the vertical envelope of selected route segments)
        # provide finite contact events. Every event is then checked by the
        # canonical collision predicate; no sampling lattice or cutoff is used.
        preferred = _candidate(side_anchor, size, side, gap)
        candidates = {preferred.y, bounds.y, bounds.bottom - preferred.height}
        if isinstance(available_obstacles, SurfaceObstacleIndex):
            relevant = []
            for obstacle in available_obstacles.select(classes=classes):
                left, top, right, bottom = obstacle_envelope(obstacle.geometry)
                clearance = obstacle.clearance
                if (preferred.x <= right + clearance and left - clearance <= preferred.right
                        and bounds.y - preferred.height - clearance <= bottom
                        and top <= bounds.bottom + clearance):
                    relevant.append(obstacle)
            obstacle_values = tuple(relevant)
            local_obstacles = SurfaceObstacleIndex()
            local_obstacles.extend(obstacle_values)
            for obstacle in obstacle_values:
                _, top, _, bottom = obstacle_envelope(obstacle.geometry)
                clearance = obstacle.clearance
                candidates.add(top - preferred.height - clearance)
                candidates.add(bottom + clearance)
        else:
            for obstacle in available_obstacles:
                rect = obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle
                candidates.add(rect.y - preferred.height)
                candidates.add(rect.bottom)

        legal_positions = []
        for y in candidates:
            if maximum_stagger is not None and abs(y - preferred.y) > maximum_stagger + 1e-9:
                continue
            candidate = LabelRect(preferred.x, y, preferred.width, preferred.height)
            if (candidate.x < bounds.x or candidate.right > bounds.right
                    or candidate.y < bounds.y or candidate.bottom > bounds.bottom):
                continue
            if side == "end" and candidate.x + text_inline_inset - side_anchor.right > maximum_end_gap:
                continue
            if association is not None and not association.allows(candidate):
                continue
            if isinstance(available_obstacles, SurfaceObstacleIndex):
                collides = bool(local_obstacles.collisions(
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
    if overflow == "visible-overflow":
        # Preserve the declared visible fallback without waiving the own-mark
        # association. It may overlap an obstacle or leave its nominal bounds.
        fallback_sides = (visible_fallback_side,) if visible_fallback_side is not None else sides
        for side in fallback_sides:
            candidate = _visible_candidate(end_anchor if side == "end" else anchor, size, side, gap)
            if association is None or association.allows(candidate):
                return LabelPlacement(side, candidate, True)
    return None
