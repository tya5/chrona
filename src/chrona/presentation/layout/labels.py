"""Finite, deterministic label placement shared by presentation adapters."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from heapq import heappop, heappush
from math import ceil, floor, isfinite
from math import hypot
from typing import Any, Callable, Iterable, Iterator

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
class MemberNameCandidate:
    """One hard-admissible candidate yielded by a member-name search."""

    placement: LabelPlacement
    blocker_placement_ids: tuple[str, ...] = ()
    occupied: bool = False
    is_fallback: bool = False


class MemberNameSearchCursor:
    """Resumable, request-local traversal of a member name's existing domain.

    Candidate geometry and event positions are derived once from the obstacle
    snapshot supplied at construction. Each yielded candidate is rechecked
    against the probe inventory passed to ``next_candidate``; this lets a
    caller test the unconsumed suffix after a local placement exchange without
    changing the request's search domain or resetting its accounting.
    """

    def __init__(self, anchor: LabelRect, size: tuple[float, float], candidates: Iterable[str], *,
                 bounds: LabelRect, obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex = (),
                 gap: float = 0.0, maximum_end_gap: float = 0.0,
                 text_inline_inset: float = 0.0, inside_host_obstacle_id: str | None = None,
                 classes: tuple[str, ...] | None = None, full_band: bool = False,
                 association: MemberNameAssociation | None = None,
                 maximum_stagger: float | None = None, overflow: str = "suppress",
                 visible_fallback_side: str | None = None,
                 candidate_geometries: Mapping[str, LabelCandidateGeometry] | None = None,
                 own_mark_right: float | None = None,
                 final_association: MemberNameAssociation | None = None,
                 _budget_domain: str = "normal") -> None:
        self.anchor = anchor
        self.size = size
        self.sides = tuple(candidates)
        self.bounds = bounds
        self._obstacles = (obstacles.copy() if isinstance(obstacles, SurfaceObstacleIndex)
                           else tuple(obstacles))
        self.gap = gap
        self.maximum_end_gap = maximum_end_gap
        self.text_inline_inset = text_inline_inset
        self.inside_host_obstacle_id = inside_host_obstacle_id
        self.classes = classes
        self.full_band = full_band
        self.association = association
        self.maximum_stagger = maximum_stagger
        self.overflow = overflow
        self.visible_fallback_side = visible_fallback_side
        self.own_mark_right = own_mark_right
        self.final_association = final_association
        self._budget_domain = _budget_domain
        if ((own_mark_right is not None
             and (isinstance(own_mark_right, bool) or not isfinite(own_mark_right)))
                or overflow not in {"suppress", "visible-overflow", "diagnose"}
                or (visible_fallback_side is not None
                    and (overflow != "visible-overflow" or visible_fallback_side not in self.sides))):
            raise _label_error("E_PRESENTATION_LABEL_INPUT", "member-name request",
                               sides=self.sides, own_mark_right=own_mark_right, overflow=overflow,
                               visible_fallback_side=visible_fallback_side)
        self.geometries = _candidate_geometries(
            self.sides, candidate_geometries, owner="member-name candidate geometries")
        if (len(self.sides) > 16 or len(set(self.sides)) != len(self.sides)
                or any(side not in _LABEL_SIDES for side in self.sides)
                or any(isinstance(value, bool) or not isfinite(value) or value < 0
                       for value in (gap, maximum_end_gap, text_inline_inset))
                or (maximum_stagger is not None
                    and (isinstance(maximum_stagger, bool) or not isfinite(maximum_stagger)
                         or maximum_stagger < 0))):
            raise _label_error("E_PRESENTATION_LABEL_INPUT", "member-name ladder",
                               sides=self.sides, gap=gap, maximum_end_gap=maximum_end_gap,
                               text_inline_inset=text_inline_inset, maximum_stagger=maximum_stagger)
        self._history: list[MemberNameCandidate] = []
        self._canonical_obstructions: list[LabelSlotObstruction] = []
        self._normal_iterator = self._normal_candidates()
        self._normal_exhausted = False
        self._fallback_iterator: Iterator[tuple[str, LabelRect, bool]] | None = None
        self._fallback_done = False
        self._neighborhood_counts: dict[tuple[str, str], int] = {}

    @property
    def evaluated_candidates(self) -> tuple[MemberNameCandidate, ...]:
        return tuple(self._history)

    @property
    def evaluated_normal_candidates(self) -> tuple[MemberNameCandidate, ...]:
        return tuple(item for item in self._history if not item.is_fallback)

    @property
    def evaluated_count(self) -> int:
        return len(self._history)

    @property
    def neighborhood_evaluated_count(self) -> int:
        return sum(self._neighborhood_counts.values())

    def next_candidate(self, obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex | None = None
                       ) -> MemberNameCandidate | None:
        """Yield the next normal candidate, whether clear or occupied."""
        try:
            side, rect, search_count, final_rung, canonical = next(self._normal_iterator)
        except StopIteration:
            self._normal_exhausted = True
            return None
        probe = self._obstacles if obstacles is None else obstacles
        occupied, blocker_ids = self._collision_details(rect, side, probe)
        result = MemberNameCandidate(
            LabelPlacement(side, rect, search_count=search_count, final_rung=final_rung,
                           canonical_obstructions=tuple(self._canonical_obstructions)),
            blocker_ids, occupied, False)
        self._history.append(result)
        if canonical and occupied:
            self._canonical_obstructions.append(
                LabelSlotObstruction(side, blocker_ids, occupied=True))
        return result

    def next_clear(self, obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex | None = None
                   ) -> MemberNameCandidate | None:
        """Continue the normal domain until its next clear candidate."""
        while (candidate := self.next_candidate(obstacles)) is not None:
            if not candidate.occupied:
                return candidate
        return None

    def next_fallback(self, obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex | None = None
                       ) -> MemberNameCandidate | None:
        """Yield the declared visible-overflow rung only after normal exhaustion."""
        if (not self._normal_exhausted or self.overflow != "visible-overflow"
                or self._fallback_done):
            return None
        if self._fallback_iterator is None:
            self._fallback_iterator = self._fallback_candidates()
        for side, rect, final_rung in self._fallback_iterator:
            geometry = self.geometries.get(side) if self.geometries is not None else None
            association = geometry.association if geometry is not None else self.association
            final_association = (geometry.final_association if geometry is not None
                                 else self.final_association)
            if final_rung:
                association = final_association
            if association is not None and not association.allows(rect):
                continue
            probe = self._obstacles if obstacles is None else obstacles
            occupied, blocker_ids = self._collision_details(rect, side, probe)
            result = MemberNameCandidate(
                LabelPlacement(side, rect, True, final_rung=final_rung),
                                         blocker_ids, occupied, True)
            self._history.append(result)
            return result
        self._fallback_done = True
        return None

    def _fallback_candidates(self) -> Iterator[tuple[str, LabelRect, bool]]:
        sides = ((self.visible_fallback_side,) if self.visible_fallback_side is not None
                 else self.sides)
        for side in sides:
            geometry = self.geometries.get(side) if self.geometries is not None else None
            final_association = (geometry.final_association if geometry is not None
                                 else self.final_association)
            extended = (side == "end" and self.own_mark_right is not None
                        and self.own_mark_right > self.anchor.right
                        and final_association is not None)
            if extended:
                anchor = LabelRect(self.anchor.x, self.anchor.y,
                                  self.own_mark_right - self.anchor.x, self.anchor.height)
                size = geometry.size if geometry is not None else self.size
                gap = geometry.gap if geometry is not None else self.gap
                try:
                    yield side, _visible_candidate(anchor, size, side, gap), True
                except ValueError as exc:
                    if str(exc).split(":", 1)[0] != "E_PRESENTATION_LABEL_UNPLACEABLE":
                        raise
            size = geometry.size if geometry is not None else self.size
            gap = geometry.gap if geometry is not None else self.gap
            try:
                yield side, _visible_candidate(self.anchor, size, side, gap), False
            except ValueError as exc:
                if str(exc).split(":", 1)[0] != "E_PRESENTATION_LABEL_UNPLACEABLE":
                    raise

    def _collision_details(self, rect: LabelRect, side: str,
                           obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex
                           ) -> tuple[bool, tuple[str, ...]]:
        geometry = ObstacleRect(rect.x, rect.y, rect.right, rect.bottom)
        if isinstance(obstacles, SurfaceObstacleIndex):
            hits = obstacles.collisions(geometry,
                                        host_id=self.inside_host_obstacle_id if side == "inside" else None,
                                        classes=self.classes)
            return bool(hits), tuple(sorted(item.placement_id for item in hits))
        hits = tuple(item for item in obstacles
                     if not (side == "inside" and isinstance(item, LabelObstacle)
                             and item.placement_id == self.inside_host_obstacle_id)
                     and _intersects(rect, item.bounds if isinstance(item, LabelObstacle) else item))
        return bool(hits), tuple(sorted({item.placement_id for item in hits
                                        if isinstance(item, LabelObstacle)}))

    def _normal_candidates(self) -> Iterator[tuple[str, LabelRect, int, bool, bool]]:
        # Each domain is generated once; suspension preserves its remaining
        # contact events and accounting for a later local exchange probe.
        yield from _iter_member_name_candidates(self)


def start_member_name_search(anchor: LabelRect, size: tuple[float, float], candidates: Iterable[str], *,
                             bounds: LabelRect,
                             obstacles: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex = (),
                             **options: Any) -> MemberNameSearchCursor:
    """Create a resumable cursor over the normal member-name candidate domain."""
    return MemberNameSearchCursor(anchor, size, candidates, bounds=bounds,
                                  obstacles=obstacles, **options)


def _iter_member_name_candidates(cursor: MemberNameSearchCursor
                                ) -> Iterator[tuple[str, LabelRect, int, bool, bool]]:
    """Construct the finite declared ladder in its historical order."""
    sides = cursor.sides
    if not sides:
        return
    if (len(sides) > 16 or len(set(sides)) != len(sides)
            or any(side not in _LABEL_SIDES for side in sides)
            or any(isinstance(value, bool) or not isfinite(value) or value < 0
                   for value in (cursor.gap, cursor.maximum_end_gap, cursor.text_inline_inset))
            or (cursor.maximum_stagger is not None and
                (isinstance(cursor.maximum_stagger, bool) or not isfinite(cursor.maximum_stagger)
                 or cursor.maximum_stagger < 0))):
        raise _label_error("E_PRESENTATION_LABEL_INPUT", "member-name ladder",
                           sides=sides, gap=cursor.gap, maximum_end_gap=cursor.maximum_end_gap,
                           text_inline_inset=cursor.text_inline_inset,
                           maximum_stagger=cursor.maximum_stagger)

    initial = cursor._obstacles
    for side in sides:
        # place_label owns canonical slot explanations per selected side; a
        # failed earlier side is retained in search history, not copied into
        # a later side's final Placement metadata.
        cursor._canonical_obstructions = []
        geometry = cursor.geometries.get(side) if cursor.geometries is not None else None
        side_size = geometry.size if geometry is not None else cursor.size
        side_gap = geometry.gap if geometry is not None else cursor.gap
        side_end_gap = (geometry.maximum_end_gap if geometry is not None
                        and geometry.maximum_end_gap is not None else cursor.maximum_end_gap)
        inset = geometry.text_inline_inset if geometry is not None else cursor.text_inline_inset
        association = geometry.association if geometry is not None else cursor.association
        stagger = geometry.maximum_stagger if geometry is not None else cursor.maximum_stagger
        side_bounds = geometry.bounds if geometry is not None and geometry.bounds is not None else cursor.bounds
        max_side_gap = side_end_gap - inset if side == "end" else None
        if side == "end" and max_side_gap < side_gap:
            cursor._canonical_obstructions.append(LabelSlotObstruction(side, policy_rejected=True))
            continue
        if not cursor.full_band or side not in {"end", "start"}:
            if cursor.full_band and stagger is not None and side in {"above", "below"}:
                preferred = _candidate(cursor.anchor, side_size, side, side_gap)
                top = max(side_bounds.y, preferred.y - stagger)
                bottom = min(side_bounds.bottom, preferred.bottom + stagger)
                if bottom - top < side_size[1]:
                    cursor._canonical_obstructions.append(
                        LabelSlotObstruction(side, outside_bounds=True))
                    continue
                side_bounds = LabelRect(side_bounds.x, top, side_bounds.width, bottom - top)
            try:
                preferred = _candidate(cursor.anchor, side_size, side, side_gap)
            except ValueError as exc:
                if str(exc).split(":", 1)[0] == "E_PRESENTATION_LABEL_UNPLACEABLE":
                    cursor._canonical_obstructions.append(
                        LabelSlotObstruction(side, policy_rejected=True))
                    continue
                raise
            if _member_candidate_allowed(preferred, side, side_bounds, cursor.anchor,
                                         side_end_gap, inset, association):
                yield side, preferred, 0, False, True
            else:
                outside = (preferred.x < side_bounds.x or preferred.y < side_bounds.y
                           or preferred.right > side_bounds.right
                           or preferred.bottom > side_bounds.bottom)
                cursor._canonical_obstructions.append(
                    LabelSlotObstruction(side, outside_bounds=outside,
                                         policy_rejected=not outside))
            if side != "inside":
                yield from _member_neighborhood(cursor, side, side_size, side_gap, side_bounds,
                                                side_end_gap, inset, association, initial)
            continue

        preferred = _candidate(cursor.anchor, side_size, side, side_gap)
        event_y = {preferred.y, side_bounds.y, side_bounds.bottom - preferred.height}
        if isinstance(initial, SurfaceObstacleIndex):
            relevant = []
            for obstacle in initial.select(classes=cursor.classes):
                left, top, right, bottom = obstacle_envelope(obstacle.geometry)
                clearance = obstacle.clearance
                if (preferred.x <= right + clearance and left - clearance <= preferred.right
                        and side_bounds.y - preferred.height - clearance <= bottom
                        and top <= side_bounds.bottom + clearance):
                    relevant.append(obstacle)
            for obstacle in relevant:
                _, top, _, bottom = obstacle_envelope(obstacle.geometry)
                event_y.update((top - preferred.height - obstacle.clearance,
                                bottom + obstacle.clearance))
        else:
            for obstacle in initial:
                rect = obstacle.bounds if isinstance(obstacle, LabelObstacle) else obstacle
                event_y.update((rect.y - preferred.height, rect.bottom))
        ordered = sorted(event_y, key=lambda y: (abs(y - preferred.y), y))
        for y in ordered:
            if stagger is not None and abs(y - preferred.y) > stagger + 1e-9:
                continue
            rect = LabelRect(preferred.x, y, preferred.width, preferred.height)
            if not _member_candidate_allowed(rect, side, side_bounds, cursor.anchor,
                                             side_end_gap, inset, association):
                continue
            yield side, rect, len(event_y), False, False

    # The own-mark extension is a final normal rung, before visible overflow.
    if ("end" in sides and cursor.own_mark_right is not None
            and cursor.own_mark_right > cursor.anchor.right):
        end_geometry = cursor.geometries.get("end") if cursor.geometries is not None else None
        final_association = (end_geometry.final_association if end_geometry is not None
                             else cursor.final_association)
        if final_association is not None:
            extended = LabelRect(cursor.anchor.x, cursor.anchor.y,
                                 cursor.own_mark_right - cursor.anchor.x, cursor.anchor.height)
            final_geometry = (replace(end_geometry, association=final_association,
                                      final_association=None)
                              if end_geometry is not None else None)
            final_geometries = ({**cursor.geometries, "end": final_geometry}
                                if cursor.geometries is not None and final_geometry is not None
                                else None)
            final_cursor = MemberNameSearchCursor(
                extended, end_geometry.size if end_geometry is not None else cursor.size,
                ("end",), bounds=cursor.bounds, obstacles=initial,
                gap=end_geometry.gap if end_geometry is not None else cursor.gap,
                maximum_end_gap=(end_geometry.maximum_end_gap
                                 if end_geometry is not None and end_geometry.maximum_end_gap is not None
                                 else cursor.maximum_end_gap),
                text_inline_inset=(end_geometry.text_inline_inset if end_geometry is not None
                                   else cursor.text_inline_inset),
                inside_host_obstacle_id=cursor.inside_host_obstacle_id,
                classes=cursor.classes, full_band=cursor.full_band,
                association=final_association, maximum_stagger=cursor.maximum_stagger,
                candidate_geometries=final_geometries, _budget_domain="final")
            final_cursor._neighborhood_counts = dict(cursor._neighborhood_counts)
            for side, rect, count, _final, canonical in final_cursor._normal_iterator:
                cursor._neighborhood_counts = dict(final_cursor._neighborhood_counts)
                cursor._canonical_obstructions = list(final_cursor._canonical_obstructions)
                yield side, rect, count, True, canonical


def _member_candidate_allowed(rect: LabelRect, side: str, bounds: LabelRect,
                              anchor: LabelRect, maximum_end_gap: float, inset: float,
                              association: MemberNameAssociation | None) -> bool:
    return (rect.x >= bounds.x and rect.y >= bounds.y and rect.right <= bounds.right
            and rect.bottom <= bounds.bottom
            and not (side == "end" and rect.x + inset - anchor.right > maximum_end_gap)
            and (association is None or association.allows(rect)))


@dataclass(frozen=True)
class _ContactCandidateSide:
    rank: int
    side: str
    base: LabelRect
    bounds: LabelRect
    association: MemberNameAssociation | None
    side_gap: float
    maximum_side_gap: float | None


def _iter_contact_candidates(
        sides: Iterable[_ContactCandidateSide],
        envelopes: Iterable[tuple[float, float, float, float]],
        *,
        admissible: Callable[[LabelRect, MemberNameAssociation | None, LabelRect], bool],
        initial_count: int = 0,
        limit: int = 512,
) -> Iterator[tuple[str, LabelRect, int]]:
    """Shared finite contact-grid and lazy heap used by both label APIs."""
    lattice = 8.0
    envelope_values = tuple(envelopes)
    nearby: list[tuple[float, int, float, float, str, LabelRect,
                       tuple[float, ...], int, LabelRect, MemberNameAssociation | None]] = []
    for item in sides:
        side, base, side_bounds = item.side, item.base, item.bounds
        tangent_bound = base.width if side in {"above", "below"} else base.height
        tangent_min, tangent_max = -tangent_bound, tangent_bound
        outward_bound = base.height if side in {"above", "below"} else base.width
        if item.association is not None:
            left, top, right, bottom = item.association.position_envelope()
            left, top = max(side_bounds.x, left), max(side_bounds.y, top)
            right = min(side_bounds.right - base.width, right)
            bottom = min(side_bounds.bottom - base.height, bottom)
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
                                   if side == "above" else
                                   (side_bounds.y - base.y, side_bounds.bottom - base.bottom))
        else:
            tangent_offsets.update((side_bounds.y - base.y, side_bounds.bottom - base.bottom))
            outward_offsets.update((base.x - side_bounds.x, base.right - side_bounds.right)
                                   if side == "start" else
                                   (side_bounds.x - base.x, side_bounds.right - base.right))
        for left, top, right, bottom in envelope_values:
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
            if (item.maximum_side_gap is not None and side in {"start", "end"}
                    and item.side_gap + outward > item.maximum_side_gap):
                continue
            heappush(nearby, (abs(tangents[0]) + outward, item.rank, outward,
                              tangents[0], side, base, tangents, 0, side_bounds,
                              item.association))
    count = initial_count
    while nearby and count < limit:
        _, rank, outward, tangent, side, base, tangents, tangent_index, side_bounds, association = heappop(nearby)
        if outward != 0 or tangent != 0:
            candidate = (LabelRect(base.x + tangent, base.y - outward, base.width, base.height)
                         if side == "above" else
                         LabelRect(base.x + tangent, base.y + outward, base.width, base.height)
                         if side == "below" else
                         LabelRect(base.x - outward, base.y + tangent, base.width, base.height)
                         if side == "start" else
                         LabelRect(base.x + outward, base.y + tangent, base.width, base.height))
            if admissible(candidate, association, side_bounds):
                count += 1
                yield side, candidate, count
        next_index = tangent_index + 1
        if next_index < len(tangents):
            next_tangent = tangents[next_index]
            heappush(nearby, (abs(next_tangent) + outward, rank, outward, next_tangent,
                              side, base, tangents, next_index, side_bounds, association))


def _member_neighborhood(cursor: MemberNameSearchCursor, side: str,
                         size: tuple[float, float], gap: float, bounds: LabelRect,
                         maximum_end_gap: float, inset: float,
                         association: MemberNameAssociation | None,
                         initial: Iterable[LabelObstacle | LabelRect] | SurfaceObstacleIndex,
                         *, anchor: LabelRect | None = None, final_rung: bool = False
                         ) -> Iterator[tuple[str, LabelRect, int, bool, bool]]:
    """Use the shared contact grid for one declared member-name side."""
    anchor = anchor or cursor.anchor
    base = _candidate(anchor, size, side, gap)
    if isinstance(initial, SurfaceObstacleIndex):
        envelopes = []
        for obstacle in initial.select(classes=cursor.classes):
            left, top, right, bottom = obstacle_envelope(obstacle.geometry)
            envelopes.append((left - obstacle.clearance, top - obstacle.clearance,
                              right + obstacle.clearance, bottom + obstacle.clearance))
    else:
        envelopes = []
        for item in initial:
            rect = item.bounds if isinstance(item, LabelObstacle) else item
            envelopes.append((rect.x, rect.y, rect.right, rect.bottom))
    budget_key = (cursor._budget_domain, side)
    initial_count = cursor._neighborhood_counts.get(budget_key, 0)
    max_gap = maximum_end_gap - inset if side == "end" else None
    side_input = _ContactCandidateSide(0, side, base, bounds, association, gap, max_gap)
    for candidate_side, rect, count in _iter_contact_candidates(
            (side_input,), envelopes,
            admissible=lambda value, assoc, candidate_bounds: _member_candidate_allowed(
                value, side, candidate_bounds, anchor, maximum_end_gap, inset, assoc),
            initial_count=initial_count, limit=512):
        cursor._neighborhood_counts[budget_key] = count
        yield candidate_side, rect, count, final_rung, False
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
    # Typed source fact forwarded to the final TextPlacement, never parsed from content.
    estimated_delta: bool = False

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
    remembered_overflow: tuple[str, LabelRect] | None = None
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
        side_inputs: list[_ContactCandidateSide] = []
        for rank, side in enumerate(sides):
            geometry = geometries.get(side) if geometries is not None else None
            side_size = geometry.size if geometry is not None else size
            side_gap = geometry.gap if geometry is not None else gap
            side_bounds = geometry.bounds if geometry is not None and geometry.bounds is not None else bounds
            side_association = geometry.association if geometry is not None else search_association
            side_maximum_gap = (geometry.maximum_end_gap - geometry.text_inline_inset
                                if geometry is not None and geometry.maximum_end_gap is not None
                                and side == "end" else maximum_side_gap)
            if side == "inside":
                continue
            base = _candidate(anchor, side_size, side, side_gap)
            side_inputs.append(_ContactCandidateSide(rank, side, base, side_bounds,
                                                      side_association, side_gap,
                                                      side_maximum_gap))
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
        for side, candidate, count in _iter_contact_candidates(
                side_inputs, envelopes, admissible=admissible, limit=512):
            if clear(candidate, side):
                return LabelPlacement(side, candidate, search_count=count,
                                      canonical_obstructions=tuple(obstructions))
            # Reuse this hard-filter-safe candidate only if normal and
            # canonical visible placement fail; never start another search.
            if (remembered_overflow is None and overflow == "visible-overflow"
                    and candidate_filter is not None
                    and (visible_fallback_side is None or side == visible_fallback_side)):
                remembered_overflow = (side, candidate)
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
        if remembered_overflow is not None:
            side, candidate = remembered_overflow
            return LabelPlacement(side, candidate, True, count,
                                  canonical_obstructions=tuple(obstructions))
        raise _label_error("E_PRESENTATION_LABEL_UNPLACEABLE", "visible fallback candidates",
                           sides=(visible_fallback_side,) if visible_fallback_side is not None else sides,
                           size=size, anchor=anchor, bounds=bounds)
    if required:
        raise _label_error("E_PRESENTATION_LABEL_UNPLACEABLE", "required label candidates",
                           sides=sides, size=size, anchor=anchor, bounds=bounds,
                           gap=gap, overflow=overflow)
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
    cursor = start_member_name_search(
        anchor, size, sides, own_mark_right=own_mark_right,
        final_association=final_association, overflow=overflow,
        visible_fallback_side=visible_fallback_side,
        candidate_geometries=candidate_geometries, **options)
    candidate = cursor.next_clear()
    if candidate is not None:
        return candidate.placement
    fallback = cursor.next_fallback()
    return fallback.placement if fallback is not None else None
