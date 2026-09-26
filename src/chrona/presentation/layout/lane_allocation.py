"""Collision-aware lane allocation for `rows.mode: lanes` (#467).

This module is schema-free: it knows nothing of View/Project resources. It
takes closed, measured candidate footprints (mark rectangles plus title/delta
text widths) and returns a deterministic group-local lane assignment with a
required, reserved label placement for every candidate. It reuses the one
#466 :class:`SurfaceObstacleIndex` machinery so that "touching" and
"collision" mean exactly what they mean for every other completed Layout
placement; each lane gets its own index instance because the ladder is
measured in the lane's local frame (translated to final block coordinates by
the caller) and lanes never share obstacles with each other.

Ladder (fixed by the #467 L0 feasibility measurement and its design
correction, ``issue-467-lane-rows-l0-ladder-correction-2026-09-27.md``):
for each candidate in a candidate lane, try, in order:

1. ``label-row-1``: a label row above the mark level, aligned to the bar's start;
2. ``label-row-2``: a second label row above the mark level, aligned to the bar's end;
3. ``end``: same level as the mark, immediately after it;
4. ``start``: same level as the mark, immediately before it.

A lane has at most two label rows; its block extent is the mark level plus
however many label rows it actually uses (0, 1 or 2). A name is never
suppressed: if no candidate lane, including a freshly opened one, admits a
fitting placement, the item is placed on the terminal `visible-overflow`
level (`end`, translated to the lane's own frame) and recorded as such,
never dropped.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    SurfaceObstacle,
    SurfaceObstacleIndex,
)

LADDER = ("label-row-1", "label-row-2", "end", "start")
_MARK_CLASS = "lane-mark"
_LABEL_CLASS_BY_LEVEL: Mapping[str, str] = {
    "label-row-1": "lane-label-row-1",
    "label-row-2": "lane-label-row-2",
    "end": "lane-label-inline",
    "start": "lane-label-inline",
}


@dataclass(frozen=True)
class LaneMark:
    """One candidate's closed, renderer-neutral mark footprint.

    ``left``/``right`` are inline (time-axis) coordinates; the mark occupies
    the full mark-level block band, so no block coordinates are needed here.
    """

    left: float
    right: float

    def __post_init__(self) -> None:
        if self.right <= self.left:
            raise ValueError("E_LAYOUT_LANE_MARK_GEOMETRY")


@dataclass(frozen=True)
class LaneCandidate:
    """One selected primary Review Item eligible for group-local lane packing."""

    candidate_id: str
    group_key: str
    order_key: tuple
    mark: LaneMark
    title_width: float
    delta_width: float | None = None
    predecessors: tuple[tuple[str, str], ...] = ()
    """``(relation_id, predecessor_candidate_id)`` pairs for immediate
    finish-to-start predecessors; the caller resolves which relations are
    immediate finish-to-start, not this module."""

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.group_key:
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if self.title_width < 0 or (self.delta_width is not None and self.delta_width < 0):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")

    @property
    def label_width(self) -> float:
        return self.title_width + (0.0 if self.delta_width is None else self.delta_width)


@dataclass(frozen=True)
class LanePlacement:
    """One candidate's accepted, lane-local placement."""

    candidate_id: str
    level: str
    """One of :data:`LADDER`, or ``"visible-overflow"`` for the terminal case."""
    rect: ObstacleRect
    visible_overflow: bool = False


@dataclass(frozen=True)
class LaneAssignment:
    """One generated lane's stable identity, members and reserved block extent."""

    lane_id: str
    group_key: str
    representative_id: str
    members: tuple[str, ...]
    placements: Mapping[str, LanePlacement]
    label_rows_used: int
    block_extent: float
    """Mark-level height plus ``label_rows_used`` label-row heights."""


@dataclass(frozen=True)
class LaneAllocationResult:
    lanes: tuple[LaneAssignment, ...]

    def lane_of(self, candidate_id: str) -> LaneAssignment:
        for lane in self.lanes:
            if candidate_id in lane.members:
                return lane
        raise KeyError(candidate_id)


class _Lane:
    """Mutable working state for one candidate lane during allocation."""

    def __init__(self, lane_id: str, group_key: str, representative_id: str,
                 mark_row_height: float, label_row_height: float, clearance: float,
                 canvas_left: float | None, canvas_right: float | None) -> None:
        self.lane_id = lane_id
        self.group_key = group_key
        self.representative_id = representative_id
        self.members: list[str] = []
        self.placements: dict[str, LanePlacement] = {}
        self.label_rows_used = 0
        self._mark_row_height = mark_row_height
        self._label_row_height = label_row_height
        self._clearance = clearance
        self._canvas_left = canvas_left
        self._canvas_right = canvas_right
        self._index = SurfaceObstacleIndex()

    def try_place(self, candidate: LaneCandidate) -> LanePlacement | None:
        """Return the first ladder placement that fits, or ``None``."""
        mark_rect = ObstacleRect(candidate.mark.left, 0.0, candidate.mark.right, self._mark_row_height)
        if self._index.collisions(mark_rect, classes=(_MARK_CLASS,), clearance=self._clearance):
            return None
        for level in LADDER:
            rect = self._candidate_rect(candidate, level)
            if self._canvas_left is not None and rect.left < self._canvas_left:
                continue
            if self._canvas_right is not None and rect.right > self._canvas_right:
                continue
            obstacle_class = _LABEL_CLASS_BY_LEVEL[level]
            if not self._index.collisions(rect, classes=(obstacle_class,), clearance=self._clearance):
                return LanePlacement(candidate.candidate_id, level, rect)
        return None

    def _candidate_rect(self, candidate: LaneCandidate, level: str) -> ObstacleRect:
        left, right = candidate.mark.left, candidate.mark.right
        width = candidate.label_width
        if level == "label-row-1":
            top = -self._label_row_height
            return ObstacleRect(left, top, left + width, top + self._label_row_height)
        if level == "label-row-2":
            top = -2 * self._label_row_height
            return ObstacleRect(right - width, top, right, top + self._label_row_height)
        if level == "end":
            return ObstacleRect(right, 0.0, right + width, self._mark_row_height)
        if level == "start":
            return ObstacleRect(left - width, 0.0, left, self._mark_row_height)
        raise ValueError("E_LAYOUT_LANE_LADDER_LEVEL")

    def accept(self, candidate: LaneCandidate, placement: LanePlacement) -> None:
        obstacle_class = _LABEL_CLASS_BY_LEVEL.get(placement.level, "lane-label-overflow")
        mark_rect = ObstacleRect(candidate.mark.left, 0.0, candidate.mark.right, self._mark_row_height)
        self._index.add(SurfaceObstacle(f"{placement.candidate_id}:mark", _MARK_CLASS, self.lane_id, mark_rect,
                                        clearance=self._clearance))
        self._index.add(SurfaceObstacle(f"{placement.candidate_id}:label", obstacle_class, self.lane_id,
                                        placement.rect, clearance=self._clearance))
        self.members.append(candidate.candidate_id)
        self.placements[candidate.candidate_id] = placement
        if placement.level in ("label-row-1", "label-row-2"):
            self.label_rows_used = max(self.label_rows_used,
                                       1 if placement.level == "label-row-1" else 2)

    def block_extent(self) -> float:
        return self._mark_row_height + self.label_rows_used * self._label_row_height

    def overflow_rect(self, candidate: LaneCandidate) -> ObstacleRect:
        right = candidate.mark.right
        return ObstacleRect(right, 0.0, right + candidate.label_width, self._mark_row_height)


def allocate_lanes(candidates: Sequence[LaneCandidate], *, mark_row_height: float = 1.0,
                   label_row_height: float = 1.0, clearance: float = 0.0,
                   canvas_left: float | None = None,
                   canvas_right: float | None = None) -> LaneAllocationResult:
    """Deterministically pack ``candidates`` into group-local collision-free lanes.

    Candidates must already be measured (finite mark and text footprints).
    Ordering, group isolation and predecessor preference follow the #467
    design; the label ladder follows the #467 L0 ladder correction. No
    candidate is ever dropped: a candidate that fits nowhere else gets the
    terminal ``visible-overflow`` placement in a fresh lane.

    ``canvas_left``/``canvas_right`` are the finite plot bounds a label
    candidate must stay within to count as "fitting"; omit either to leave
    that side unbounded (as neutral algorithm tests do).
    """
    ordered = sorted(candidates, key=lambda item: (item.group_key, item.order_key, item.candidate_id))
    lanes: list[_Lane] = []
    lane_by_candidate: dict[str, _Lane] = {}
    by_id = {item.candidate_id: item for item in candidates}
    lane_counters: dict[str, int] = {}

    def open_lane(group_key: str, representative_id: str) -> _Lane:
        lane_counters[group_key] = lane_counters.get(group_key, 0) + 1
        lane = _Lane(f"lane:{group_key}:{representative_id}", group_key, representative_id,
                    mark_row_height, label_row_height, clearance, canvas_left, canvas_right)
        lanes.append(lane)
        return lane

    for candidate in ordered:
        group_lanes = [lane for lane in lanes if lane.group_key == candidate.group_key]
        predecessor_lane = _eligible_predecessor_lane(candidate, by_id, lane_by_candidate)
        search_order: list[_Lane] = []
        if predecessor_lane is not None:
            search_order.append(predecessor_lane)
        search_order.extend(lane for lane in group_lanes if lane is not predecessor_lane)
        accepted = False
        for lane in search_order:
            placement = lane.try_place(candidate)
            if placement is not None:
                lane.accept(candidate, placement)
                lane_by_candidate[candidate.candidate_id] = lane
                accepted = True
                break
        if not accepted:
            lane = open_lane(candidate.group_key, candidate.candidate_id)
            placement = lane.try_place(candidate)
            if placement is None:
                # Even alone, no label candidate fits: record the terminal
                # visible-overflow placement rather than dropping the name.
                placement = LanePlacement(candidate.candidate_id, "visible-overflow",
                                          lane.overflow_rect(candidate), visible_overflow=True)
                lane.members.append(candidate.candidate_id)
                lane.placements[candidate.candidate_id] = placement
                lane._index.add(SurfaceObstacle(f"{candidate.candidate_id}:mark", _MARK_CLASS, lane.lane_id,
                                                ObstacleRect(candidate.mark.left, 0.0, candidate.mark.right,
                                                            mark_row_height), clearance=clearance))
            else:
                lane.accept(candidate, placement)
            lane_by_candidate[candidate.candidate_id] = lane

    return LaneAllocationResult(tuple(
        LaneAssignment(lane.lane_id, lane.group_key, lane.representative_id, tuple(lane.members),
                       dict(lane.placements), lane.label_rows_used, lane.block_extent())
        for lane in lanes
    ))


def _eligible_predecessor_lane(candidate: LaneCandidate, by_id: Mapping[str, LaneCandidate],
                               lane_by_candidate: Mapping[str, "_Lane"]) -> "_Lane | None":
    """Return the unique eligible immediate predecessor's lane, if any.

    Eligibility requires the predecessor to already be assigned to a lane and
    its mark to end at or before this candidate's mark start (a nonnegative
    gap, including exact touch). Several eligible predecessors are broken by
    stable relation ID then predecessor candidate ID, matching the design.
    """
    eligible: list[tuple[str, str, "_Lane"]] = []
    for relation_id, predecessor_id in candidate.predecessors:
        predecessor = by_id.get(predecessor_id)
        lane = lane_by_candidate.get(predecessor_id)
        if predecessor is None or lane is None:
            continue
        if predecessor.mark.right <= candidate.mark.left:
            eligible.append((relation_id, predecessor_id, lane))
    if not eligible:
        return None
    eligible.sort(key=lambda item: (item[0], item[1]))
    return eligible[0][2]
