"""Finite, deterministic label placement shared by presentation adapters."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from heapq import heappop, heappush
from math import ceil, floor, isfinite
from math import hypot
from typing import Callable, Iterable

from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    SurfaceObstacleIndex,
    obstacle_envelope,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.style_rules import StyleOccurrenceKey


def _label_error(code: str, owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"{code}: {owner} " + ", ".join(fields))


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
class LabelSlotObstruction:
    """Why an earlier canonical slot could not complete, without invented IDs."""

    side: str
    blocker_placement_ids: tuple[str, ...] = ()
    occupied: bool = False
    outside_bounds: bool = False
    policy_rejected: bool = False


@dataclass(frozen=True)
class LabelPlacement:
    side: str
    bounds: LabelRect
    visible_overflow: bool = False
    search_count: int = 0
    final_rung: bool = False
    canonical_obstructions: tuple[LabelSlotObstruction, ...] = ()


@dataclass(frozen=True)
class LabelObstacle:
    """A completed Layout obstacle, retaining the placement that owns it."""

    placement_id: str
    bounds: LabelRect


@dataclass(frozen=True)
class MemberNameAssociation:
    """Measured Text footprint and its exact completed marks, in Layout space.

    ``mark`` is the requested host; ``also_marks`` are the item's other own drawn
    marks (an actual mark). The Text is associated when it is within
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

    def position_envelope(self) -> tuple[float, float, float, float]:
        """Conservative top-left position bounds; ``allows`` remains exact.

        The completed Text must approach at least one own mark. Its inset,
        dimensions and declared reach bound a finite footprint-position domain.
        """
        marks = (self.mark, *self.also_marks)
        return (
            min(mark.x for mark in marks) - self.maximum_distance
            - self.text_inline_inset - self.text_width,
            min(mark.y for mark in marks) - self.maximum_distance
            - self.text_block_inset - self.text_height,
            max(mark.right for mark in marks) + self.maximum_distance - self.text_inline_inset,
            max(mark.bottom for mark in marks) + self.maximum_distance - self.text_block_inset,
        )


@dataclass(frozen=True)
class LabelCandidateGeometry:
    """One already-measured candidate's complete Layout geometry inputs."""

    size: tuple[float, float]
    gap: float = 0.0
    text_inline_inset: float = 0.0
    maximum_end_gap: float | None = None
    association: MemberNameAssociation | None = None
    maximum_stagger: float | None = None
    final_association: MemberNameAssociation | None = None
    bounds: LabelRect | None = None


_LABEL_SIDES = frozenset({"above", "below", "start", "end", "inside"})


def _candidate_geometries(
    candidates: tuple[str, ...],
    geometries: Mapping[str, LabelCandidateGeometry] | None,
    *,
    owner: str,
) -> dict[str, LabelCandidateGeometry] | None:
    if geometries is None:
        return None
    if not isinstance(geometries, Mapping):
        raise _label_error("E_PRESENTATION_LABEL_INPUT", owner,
                           candidate_geometries_type=type(geometries).__name__)
    missing = set(candidates) - set(geometries)
    unknown = set(geometries) - _LABEL_SIDES
    if missing or unknown:
        raise _label_error("E_PRESENTATION_LABEL_INPUT", owner,
                           missing_geometry_sides=tuple(sorted(missing)),
                           unknown_geometry_sides=tuple(sorted(unknown)))
    result = dict(geometries)
    for side, geometry in result.items():
        if not isinstance(geometry, LabelCandidateGeometry):
            raise _label_error("E_PRESENTATION_LABEL_INPUT", owner,
                               side=side, geometry_type=type(geometry).__name__)
        dimensions = geometry.size
        numeric = (geometry.gap, geometry.text_inline_inset)
        if (not isinstance(dimensions, tuple) or len(dimensions) != 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not isfinite(value) or value <= 0 for value in dimensions)
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not isfinite(value) or value < 0 for value in numeric)
                or (geometry.maximum_end_gap is not None and
                    (isinstance(geometry.maximum_end_gap, bool)
                     or not isinstance(geometry.maximum_end_gap, (int, float))
                     or not isfinite(geometry.maximum_end_gap)
                     or geometry.maximum_end_gap < 0))
                or (geometry.maximum_stagger is not None and
                    (isinstance(geometry.maximum_stagger, bool)
                     or not isinstance(geometry.maximum_stagger, (int, float))
                     or not isfinite(geometry.maximum_stagger) or geometry.maximum_stagger < 0))
                or (geometry.association is not None and
                    not isinstance(geometry.association, MemberNameAssociation))
                or (geometry.final_association is not None and
                    not isinstance(geometry.final_association, MemberNameAssociation))
                or (geometry.bounds is not None and
                    (not isinstance(geometry.bounds, LabelRect)
                     or any(isinstance(value, bool) or not isinstance(value, (int, float))
                            or not isfinite(value)
                            for value in (geometry.bounds.x, geometry.bounds.y,
                                          geometry.bounds.width, geometry.bounds.height))
                     or geometry.bounds.width <= 0 or geometry.bounds.height <= 0))):
            raise _label_error("E_PRESENTATION_LABEL_INPUT", owner,
                               side=side, size=dimensions, gap=geometry.gap,
                               text_inline_inset=geometry.text_inline_inset,
                               maximum_end_gap=geometry.maximum_end_gap,
                               maximum_stagger=geometry.maximum_stagger,
                               bounds=geometry.bounds)
    return result


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
    subjects: tuple[DiagnosticSubject, ...] = ()
    required_before_routes: bool = False
    style_occurrence_key: StyleOccurrenceKey | None = None

    @property
    def is_required_before_routes(self) -> bool:
        return (self.required_before_routes or self.rule_host_obstacle_id is not None
                or self.overflow == "diagnose")


def _intersects(a: LabelRect, b: LabelRect) -> bool:
    return a.x < b.right and b.x < a.right and a.y < b.bottom and b.y < a.bottom


def _candidate(anchor: LabelRect, size: tuple[float, float], side: str, gap: float) -> LabelRect:
    width, height = size
    if width <= 0 or height <= 0 or gap < 0:
        raise _label_error("E_PRESENTATION_LABEL_INPUT", "label candidate geometry",
                           anchor=anchor, size=size, side=side, gap=gap)
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
            raise _label_error("E_PRESENTATION_LABEL_UNPLACEABLE", "inside label candidate",
                               anchor_size=(anchor.width, anchor.height), size=size, side=side)
        return LabelRect(anchor.x + (anchor.width - width) / 2, anchor.y + (anchor.height - height) / 2, width, height)
    raise _label_error("E_PRESENTATION_LABEL_INPUT", "label candidate side",
                       anchor=anchor, size=size, side=side, gap=gap)


def _visible_candidate(anchor: LabelRect, size: tuple[float, float], side: str, gap: float) -> LabelRect:
    """Return a deterministic preferred label position without fit rejection."""
    if side == "inside":
        width, height = size
        if width <= 0 or height <= 0 or gap < 0:
            raise _label_error("E_PRESENTATION_LABEL_INPUT", "visible label candidate",
                               anchor=anchor, size=size, side=side, gap=gap)
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
                search_association: MemberNameAssociation | None = None,
                candidate_filter: Callable[[LabelRect], bool] | None = None,
                candidate_geometries: Mapping[str, LabelCandidateGeometry] | None = None) -> LabelPlacement | None:
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
        raise _label_error("E_PRESENTATION_LABEL_INPUT", "label request",
                           sides=sides, overflow=overflow,
                           visible_fallback_side=visible_fallback_side,
                           maximum_side_gap=maximum_side_gap, size=size, gap=gap)
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    blocked = () if index is not None else tuple(obstacles)
    geometries = _candidate_geometries(sides, candidate_geometries, owner="label candidate geometries")

    def admissible(candidate: LabelRect, association: MemberNameAssociation | None = search_association,
                   candidate_bounds: LabelRect = bounds) -> bool:
        if (candidate.x < candidate_bounds.x or candidate.y < candidate_bounds.y
                or candidate.right > candidate_bounds.right or candidate.bottom > candidate_bounds.bottom):
            return False
        if candidate_filter is not None and not candidate_filter(candidate):
            return False
        if association is not None and not association.allows(candidate):
            return False
        return True

    def collision_details(candidate: LabelRect, side: str) -> tuple[bool, tuple[str, ...]]:
        if index is not None:
            hits = index.collisions(
                ObstacleRect(candidate.x, candidate.y, candidate.right, candidate.bottom),
                host_id=inside_host_obstacle_id if side == "inside" else None,
                rule_host_id=rule_host_obstacle_id, classes=classes)
            return bool(hits), tuple(sorted(item.placement_id for item in hits))
        active_obstacles = (obstacle for obstacle in blocked
                            if not (side == "inside" and isinstance(obstacle, LabelObstacle)
                                    and obstacle.placement_id == inside_host_obstacle_id))
        hits = tuple(obstacle for obstacle in active_obstacles
                     if _intersects(candidate, obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle))
        return bool(hits), tuple(sorted({item.placement_id for item in hits if isinstance(item, LabelObstacle)}))

    def clear(candidate: LabelRect, side: str) -> bool:
        return not collision_details(candidate, side)[0]

    obstructions: list[LabelSlotObstruction] = []
    for side in sides:
        geometry = geometries.get(side) if geometries is not None else None
        side_size = geometry.size if geometry is not None else size
        side_gap = geometry.gap if geometry is not None else gap
        side_bounds = geometry.bounds if geometry is not None and geometry.bounds is not None else bounds
        side_association = geometry.association if geometry is not None else search_association
        side_maximum_gap = (geometry.maximum_end_gap - geometry.text_inline_inset
                            if geometry is not None and geometry.maximum_end_gap is not None
                            and side == "end" else maximum_side_gap)
        if (side_maximum_gap is not None and side in {"end", "start"}
                and side_gap > side_maximum_gap):
            obstructions.append(LabelSlotObstruction(side, policy_rejected=True))
            continue
        try:
            candidate = _candidate(anchor, side_size, side, side_gap)
        except ValueError as exc:
            if str(exc).split(":", 1)[0] == "E_PRESENTATION_LABEL_UNPLACEABLE":
                obstructions.append(LabelSlotObstruction(side, policy_rejected=True))
                continue
            raise
        if not admissible(candidate, side_association, side_bounds):
            outside = (candidate.x < side_bounds.x or candidate.y < side_bounds.y
                       or candidate.right > side_bounds.right or candidate.bottom > side_bounds.bottom)
            obstructions.append(LabelSlotObstruction(side, outside_bounds=outside, policy_rejected=not outside))
            continue
        occupied, blocker_ids = collision_details(candidate, side)
        if not occupied:
            return LabelPlacement(side, candidate, canonical_obstructions=tuple(obstructions))
        obstructions.append(LabelSlotObstruction(side, blocker_ids, occupied=True))
    if search_side_neighborhood:
        lattice = 8.0
        position_bounds = None
        nearby: list[tuple[float, int, float, float, str, LabelRect, tuple[float, ...], int, LabelRect]] = []
        association_by_side: dict[str, MemberNameAssociation | None] = {}
        for rank, side in enumerate(sides):
            geometry = geometries.get(side) if geometries is not None else None
            side_size = geometry.size if geometry is not None else size
            side_gap = geometry.gap if geometry is not None else gap
            side_bounds = geometry.bounds if geometry is not None and geometry.bounds is not None else bounds
            side_association = geometry.association if geometry is not None else search_association
            association_by_side[side] = side_association
            side_maximum_gap = (geometry.maximum_end_gap - geometry.text_inline_inset
                                if geometry is not None and geometry.maximum_end_gap is not None
                                and side == "end" else maximum_side_gap)
            if side == "inside":
                continue
            base = _candidate(anchor, side_size, side, side_gap)
            tangent_bound = side_size[0] if side in {"above", "below"} else side_size[1]
            tangent_min, tangent_max = -tangent_bound, tangent_bound
            outward_bound = side_size[1] if side in {"above", "below"} else side_size[0]
            position_bounds = (side_association.position_envelope()
                               if side_association is not None else None)
            if position_bounds is not None:
                left = max(side_bounds.x, position_bounds[0])
                top = max(side_bounds.y, position_bounds[1])
                right = min(side_bounds.right - base.width, position_bounds[2])
                bottom = min(side_bounds.bottom - base.height, position_bounds[3])
                if side in {"above", "below"}:
                    tangent_min, tangent_max = left - base.x, right - base.x
                    outward_bound = base.y - top if side == "above" else bottom - base.y
                else:
                    tangent_min, tangent_max = top - base.y, bottom - base.y
                    outward_bound = base.x - left if side == "start" else right - base.x
                if tangent_min > tangent_max or outward_bound < 0:
                    continue
            tangent_offsets = {step * lattice for step in range(ceil(tangent_min / lattice),
                                                                floor(tangent_max / lattice) + 1)}
            tangent_offsets.update((tangent_min, tangent_max))
            outward_offsets = {step * lattice for step in range(ceil(outward_bound / lattice) + 1)
                               if step * lattice <= outward_bound}
            outward_offsets.add(outward_bound)

            if side in {"above", "below"}:
                tangent_offsets.update((side_bounds.x - base.x, side_bounds.right - base.right))
                outward_offsets.update((base.y - side_bounds.y, base.bottom - side_bounds.bottom)
                    if side == "above" else (side_bounds.y - base.y, side_bounds.bottom - base.bottom))
            else:
                tangent_offsets.update((side_bounds.y - base.y, side_bounds.bottom - base.bottom))
                outward_offsets.update((base.x - side_bounds.x, base.right - side_bounds.right)
                    if side == "start" else (side_bounds.x - base.x, side_bounds.right - base.right))

            if index is not None:
                event_obstacles = tuple(item for item in index.select(classes=classes)
                    if item.placement_id != rule_host_obstacle_id)
                envelopes = []
                for obstacle in event_obstacles:
                    left, top, right, bottom = obstacle_envelope(obstacle.geometry)
                    envelopes.append((left - obstacle.clearance, top - obstacle.clearance,
                                      right + obstacle.clearance, bottom + obstacle.clearance))
            else:
                envelopes = []
                for obstacle in blocked:
                    rect = obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle
                    envelopes.append((rect.x, rect.y, rect.right, rect.bottom))

            # Include exact translations at which the candidate rectangle
            # touches an obstacle envelope, plus both footprint-boundary
            # offsets. The canonical collision query remains the authority.
            for left, top, right, bottom in envelopes:
                if side in {"above", "below"}:
                    tangent_offsets.update((left - base.right, right - base.x))
                    outward_offsets.update((base.bottom - top, base.y - bottom)
                        if side == "above" else (bottom - base.y, top - base.bottom))
                else:
                    tangent_offsets.update((top - base.bottom, bottom - base.y))
                    outward_offsets.update((base.right - left, base.x - right)
                        if side == "start" else (right - base.x, left - base.right))
            tangent_offsets = {value for value in tangent_offsets
                               if isfinite(value) and tangent_min <= value <= tangent_max}
            outward_offsets = {value for value in outward_offsets
                               if isfinite(value) and 0 <= value <= outward_bound}
            tangents = tuple(sorted(tangent_offsets, key=lambda value: (abs(value), value)))
            for outward in sorted(outward_offsets):
                if (side_maximum_gap is not None and side in {"end", "start"}
                        and side_gap + outward > side_maximum_gap):
                    continue
                heappush(nearby, (abs(tangents[0]) + outward, rank, outward,
                                  tangents[0], side, base, tangents, 0, side_bounds))
        count = 0
        while nearby and count < 512:
            _, rank, outward, tangent, side, base, tangents, tangent_index, side_bounds = heappop(nearby)
            if outward != 0 or tangent != 0:
                candidate = (LabelRect(base.x + tangent, base.y - outward, base.width, base.height)
                             if side == "above" else
                             LabelRect(base.x + tangent, base.y + outward, base.width, base.height)
                             if side == "below" else
                             LabelRect(base.x - outward, base.y + tangent, base.width, base.height)
                             if side == "start" else
                             LabelRect(base.x + outward, base.y + tangent, base.width, base.height))
                if admissible(candidate, association_by_side[side], side_bounds):
                    count += 1
                    if clear(candidate, side):
                        return LabelPlacement(side, candidate, search_count=count,
                                              canonical_obstructions=tuple(obstructions))
            next_index = tangent_index + 1
            if next_index < len(tangents):
                next_tangent = tangents[next_index]
                heappush(nearby, (abs(next_tangent) + outward, rank, outward,
                                  next_tangent, side, base, tangents, next_index, side_bounds))
    if overflow == "visible-overflow":
        # Ordinary requests retain their first ranked side. A separately
        # declared terminal side is used only after all ranked candidates fail.
        for side in ((visible_fallback_side,) if visible_fallback_side is not None else sides):
            geometry = geometries.get(side) if geometries is not None else None
            side_size = geometry.size if geometry is not None else size
            side_gap = geometry.gap if geometry is not None else gap
            try:
                candidate = _visible_candidate(anchor, side_size, side, side_gap)
                # A visible fallback may leave its declared bounds, but a
                # caller's hard geometric filter still applies. In particular,
                # terminal route text may overflow the plot, never other text.
                if candidate_filter is not None and not candidate_filter(candidate):
                    obstructions.append(LabelSlotObstruction(side, policy_rejected=True))
                    continue
                return LabelPlacement(side, candidate, True,
                                      canonical_obstructions=tuple(obstructions))
            except ValueError as exc:
                if str(exc).split(":", 1)[0] != "E_PRESENTATION_LABEL_UNPLACEABLE":
                    raise
        raise _label_error("E_PRESENTATION_LABEL_UNPLACEABLE", "visible fallback candidates",
                           sides=(visible_fallback_side,) if visible_fallback_side is not None else sides,
                           size=size, anchor=anchor, bounds=bounds)
    if required:
        raise _label_error("E_PRESENTATION_LABEL_UNPLACEABLE", "required label candidates",
                           sides=sides, size=size, anchor=anchor, bounds=bounds,
                           gap=gap, overflow=overflow)
    return None


def _place_member_name_ladder(
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
    candidate_geometries: Mapping[str, LabelCandidateGeometry] | None = None,
) -> LabelPlacement | None:
    """Try declared member-name sides in order, bounding end gap to completed text.

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
            or overflow not in {"suppress", "visible-overflow", "diagnose"}
            or (visible_fallback_side is not None and
                (overflow != "visible-overflow" or visible_fallback_side not in sides))):
        raise _label_error("E_PRESENTATION_LABEL_INPUT", "member-name ladder",
                           sides=sides, gap=gap, maximum_end_gap=maximum_end_gap,
                           text_inline_inset=text_inline_inset, maximum_stagger=maximum_stagger,
                           overflow=overflow, visible_fallback_side=visible_fallback_side)
    geometries = _candidate_geometries(sides, candidate_geometries,
                                       owner="member-name candidate geometries")
    available_obstacles = (obstacles if isinstance(obstacles, SurfaceObstacleIndex)
                           else tuple(obstacles))
    for side in sides:
        geometry = geometries.get(side) if geometries is not None else None
        side_size = geometry.size if geometry is not None else size
        side_gap = geometry.gap if geometry is not None else gap
        side_end_gap = (geometry.maximum_end_gap
                        if geometry is not None and geometry.maximum_end_gap is not None
                        else maximum_end_gap)
        side_text_inset = geometry.text_inline_inset if geometry is not None else text_inline_inset
        side_association = geometry.association if geometry is not None else association
        side_stagger = geometry.maximum_stagger if geometry is not None else maximum_stagger
        side_bounds = geometry.bounds if geometry is not None and geometry.bounds is not None else bounds
        maximum_side_gap = (side_end_gap - side_text_inset) if side == "end" else None
        if side == "end" and maximum_side_gap < side_gap:
            continue
        if not full_band or side not in {"end", "start"}:
            if full_band and side_stagger is not None and side in {"above", "below"}:
                preferred = _candidate(anchor, side_size, side, side_gap)
                top = max(side_bounds.y, preferred.y - side_stagger)
                bottom = min(side_bounds.bottom, preferred.bottom + side_stagger)
                if bottom - top < side_size[1]:
                    continue
                side_bounds = LabelRect(side_bounds.x, top, side_bounds.width, bottom - top)
            # Association governs member-name reach; fill lanes additionally
            # retain their single measured block-stagger constraint.
            placed = place_label(
                anchor, side_size, (side,), bounds=side_bounds, obstacles=available_obstacles, gap=side_gap,
                inside_host_obstacle_id=inside_host_obstacle_id,
                required=False, overflow="suppress", classes=classes,
                search_side_neighborhood=True, maximum_side_gap=maximum_side_gap,
                search_association=side_association,
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
        preferred = _candidate(anchor, side_size, side, side_gap)
        candidates = {preferred.y, side_bounds.y, side_bounds.bottom - preferred.height}
        if isinstance(available_obstacles, SurfaceObstacleIndex):
            relevant = []
            for obstacle in available_obstacles.select(classes=classes):
                left, top, right, bottom = obstacle_envelope(obstacle.geometry)
                clearance = obstacle.clearance
                if (preferred.x <= right + clearance and left - clearance <= preferred.right
                        and side_bounds.y - preferred.height - clearance <= bottom
                        and top <= side_bounds.bottom + clearance):
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
            if side_stagger is not None and abs(y - preferred.y) > side_stagger + 1e-9:
                continue
            candidate = LabelRect(preferred.x, y, preferred.width, preferred.height)
            if (candidate.x < side_bounds.x or candidate.right > side_bounds.right
                    or candidate.y < side_bounds.y or candidate.bottom > side_bounds.bottom):
                continue
            if side == "end" and candidate.x + side_text_inset - anchor.right > side_end_gap:
                continue
            if side_association is not None and not side_association.allows(candidate):
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
            geometry = geometries.get(side) if geometries is not None else None
            side_size = geometry.size if geometry is not None else size
            side_gap = geometry.gap if geometry is not None else gap
            side_association = geometry.association if geometry is not None else association
            candidate = _visible_candidate(anchor, side_size, side, side_gap)
            if side_association is None or side_association.allows(candidate):
                return LabelPlacement(side, candidate, True)
    return None


def place_member_name(
    anchor: LabelRect,
    size: tuple[float, float],
    candidates: Iterable[str],
    *,
    own_mark_right: float | None = None,
    final_association: MemberNameAssociation | None = None,
    overflow: str = "suppress",
    visible_fallback_side: str | None = None,
    candidate_geometries: Mapping[str, LabelCandidateGeometry] | None = None,
    **options,
) -> LabelPlacement | None:
    """Place a member name on its declared ladder, then on a final own-mark rung.

    The declared ladder is tried exactly as ``_place_member_name_ladder`` does, so a
    name with a legal candidate keeps its position and host. Only when none is
    legal, and ``end`` is declared, an own mark ends past the anchor
    (``own_mark_right``, the right edge of the item's last own drawn mark) and
    ``final_association`` is given, the ``end`` side is tried from that mark, bounded
    from its right edge and associated with any own mark; the placement carries
    ``final_rung``. Then the visible-overflow fallback applies, measured from the same
    mark when its side is ``end``.
    """
    sides = tuple(candidates)
    if ((own_mark_right is not None and (isinstance(own_mark_right, bool) or not isfinite(own_mark_right)))
            or overflow not in {"suppress", "visible-overflow", "diagnose"}
            or (visible_fallback_side is not None and
                (overflow != "visible-overflow" or visible_fallback_side not in sides))):
        raise _label_error("E_PRESENTATION_LABEL_INPUT", "member-name request",
                           sides=sides, own_mark_right=own_mark_right, overflow=overflow,
                           visible_fallback_side=visible_fallback_side)
    geometries = _candidate_geometries(sides, candidate_geometries,
                                       owner="member-name candidate geometries")
    if geometries is not None:
        placed = _place_member_name_ladder(anchor, size, sides, overflow="suppress",
                                            candidate_geometries=geometries, **options)
        if placed is not None or not sides:
            return placed
        end_geometry = geometries.get("end")
        end_association = (end_geometry.final_association if end_geometry is not None
                           else None)
        if (end_geometry is not None and own_mark_right is not None
                and own_mark_right > anchor.right and end_association is not None):
            extended = LabelRect(anchor.x, anchor.y, own_mark_right - anchor.x, anchor.height)
            final_geometry = replace(end_geometry, association=end_association)
            final = _place_member_name_ladder(
                extended, end_geometry.size, ("end",), overflow="suppress",
                candidate_geometries={"end": final_geometry}, **options)
            if final is not None:
                return replace(final, final_rung=True)
        if overflow == "suppress":
            return None
        fallback_side = visible_fallback_side or sides[0]
        fallback_geometry = geometries[fallback_side]
        if (fallback_side == "end" and own_mark_right is not None
                and own_mark_right > anchor.right and end_association is not None):
            extended = LabelRect(anchor.x, anchor.y, own_mark_right - anchor.x, anchor.height)
            final_geometry = replace(end_geometry, association=end_association)
            final = _place_member_name_ladder(
                extended, end_geometry.size, ("end",), overflow=overflow,
                visible_fallback_side="end", candidate_geometries={"end": final_geometry}, **options)
            if final is not None:
                return replace(final, final_rung=True)
        return _place_member_name_ladder(
            anchor, fallback_geometry.size, sides, overflow=overflow,
            visible_fallback_side=visible_fallback_side,
            candidate_geometries=geometries, **options)
    placed = _place_member_name_ladder(anchor, size, sides, overflow="suppress", **options)
    if placed is not None or not sides:
        return placed
    if ("end" in sides and own_mark_right is not None and own_mark_right > anchor.right
            and final_association is not None):
        extended = LabelRect(anchor.x, anchor.y, own_mark_right - anchor.x, anchor.height)
        options_final = {**options, "association": final_association}
        final = _place_member_name_ladder(extended, size, ("end",), overflow="suppress", **options_final)
        if final is not None:
            return replace(final, final_rung=True)
    if overflow == "suppress":
        return None
    if ((visible_fallback_side or sides[0]) == "end" and own_mark_right is not None
            and own_mark_right > anchor.right and final_association is not None):
        # The visible fallback is an end candidate: measure it from the last own mark too, so the
        # overflowing name does not cover the item's own actual mark.
        extended = LabelRect(anchor.x, anchor.y, own_mark_right - anchor.x, anchor.height)
        options_final = {**options, "association": final_association}
        final = _place_member_name_ladder(extended, size, ("end",), overflow=overflow,
                                          visible_fallback_side="end", **options_final)
        if final is not None:
            return replace(final, final_rung=True)
    return _place_member_name_ladder(anchor, size, sides, overflow=overflow,
                                     visible_fallback_side=visible_fallback_side, **options)
