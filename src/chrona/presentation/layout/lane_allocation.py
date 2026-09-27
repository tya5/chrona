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

This is the partial B1b allocator extension only. It accepts an already
closed atomic bundle and preserves each member's identity and required label;
it does not map ReviewProjection or resolve marks, typography, or icons from
render inputs. That projection-to-bundle mapper remains a separate B1b slice.

Ladder (fixed by the #467/#494 feasibility and route correction):
for each candidate in a candidate lane, try, in order:

1. ``label-row-1``: a label row above the mark level, aligned to the bar's start;
2. ``label-row-2``: a second label row above the mark level, aligned to the bar's end;
3. ``end``: same level as the mark, immediately after it;
4. ``start``: same level as the mark, immediately before it.
5. ``label-row-3-start``: third stagger row, aligned to the mark's start;
6. ``label-row-3-end``: third stagger row, aligned to the mark's end.

A lane has at most three label rows; its block extent is the mark level plus
however many label rows it actually uses (0 through 3). A name is never
suppressed: if no candidate lane, including a freshly opened one, admits a
fitting placement, the item is placed on the terminal `visible-overflow`
level (`end`, translated to the lane's own frame) and recorded as such,
never dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence
from urllib.parse import quote

from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleGeometry,
    SurfaceObstacle,
    SurfaceObstacleIndex,
    obstacle_envelope,
)

LADDER = ("label-row-1", "label-row-2", "end", "start",
          "label-row-3-start", "label-row-3-end")
_MARK_CLASS = "lane-mark"
_LABEL_CLASS_BY_LEVEL: Mapping[str, str] = {
    "label-row-1": "lane-label-row-1",
    "label-row-2": "lane-label-row-2",
    "label-row-3-start": "lane-label-row-3",
    "label-row-3-end": "lane-label-row-3",
    "end": "lane-label-inline",
    "start": "lane-label-inline",
}


@dataclass(frozen=True)
class LaneMark:
    """One candidate's closed, renderer-neutral mark footprint.

    ``left``/``right`` are inline (time-axis) coordinates; the mark occupies
    the full mark-level block band. ``footprints`` include measured actual,
    baseline, comparison, point-glyph and progress geometry where present;
    the caller supplies stroke-expanded renderer-neutral bounds or segments.
    """

    left: float
    right: float
    footprints: tuple[ObstacleGeometry, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.left) or not isfinite(self.right) or self.right <= self.left:
            raise ValueError("E_LAYOUT_LANE_MARK_GEOMETRY")


@dataclass(frozen=True)
class LaneMember:
    """One independently identified mark and required label in a bundle.

    ``overlays`` names bundle members whose marks may intentionally occupy
    the same geometry (for example a comparison facet or attached point).
    The exemption is local to this bundle and never applies to labels.
    """

    member_id: str
    mark: LaneMark
    title_width: float
    delta_width: float | None = None
    overlays: tuple[str, ...] = ()

    @property
    def label_width(self) -> float:
        return self.title_width + (0.0 if self.delta_width is None else self.delta_width)


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
    group_order: tuple = ()
    bundle: tuple[LaneMember, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if (not isfinite(self.title_width) or self.title_width <= 0
                or (self.delta_width is not None and (not isfinite(self.delta_width) or self.delta_width < 0))
                or not isfinite(self.label_width)):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if self.bundle:
            ids = tuple(member.member_id for member in self.bundle)
            if (ids[0] != self.candidate_id or len(set(ids)) != len(ids)
                    or (self.bundle[0].mark, self.bundle[0].title_width, self.bundle[0].delta_width)
                    != (self.mark, self.title_width, self.delta_width)):
                raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
            known = set(ids)
            for member in self.bundle:
                if (not member.member_id or not isfinite(member.title_width) or member.title_width <= 0
                        or (member.delta_width is not None and
                            (not isfinite(member.delta_width) or member.delta_width < 0))
                        or not isfinite(member.label_width)
                        or any(target not in known or target == member.member_id for target in member.overlays)):
                    raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")

    @property
    def members_for_placement(self) -> tuple[LaneMember, ...]:
        return self.bundle or (LaneMember(self.candidate_id, self.mark, self.title_width, self.delta_width),)

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
    member_placements: Mapping[str, "LanePlacement"] = field(default_factory=lambda: MappingProxyType({}))


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

    def try_place(self, candidate: LaneCandidate, *, allow_visible_overflow: bool = False) -> LanePlacement | None:
        """Return the first ladder placement that fits, or ``None``."""
        members = candidate.members_for_placement
        all_mark_geometries = {member.member_id: self._member_mark_geometries(member) for member in members}
        # Compare every proposed member with already accepted lane content.
        for member in members:
            mark_geometries = all_mark_geometries[member.member_id]
            if any(self._index.collisions(geometry, classes=(_MARK_CLASS, "lane-label-inline"),
                                          clearance=self._clearance) for geometry in mark_geometries):
                return None
        # Marks inside one bundle may overlap only through an explicit pair
        # exemption. This is the only mark-overlap exception in the kernel.
        for index, member in enumerate(members):
            for other in members[index + 1:]:
                allowed = (other.member_id in member.overlays or member.member_id in other.overlays)
                if not allowed and any(
                    _geometries_collide(left, right, self._clearance)
                    for left in all_mark_geometries[member.member_id]
                    for right in all_mark_geometries[other.member_id]
                ):
                    raise ValueError("E_LAYOUT_LANE_BUNDLE_MARK_COLLISION")
        # A new mark shares its band with any earlier item's already-accepted
        # `end`/`start` label (the same two-way check `try_place` applies to
        # a new `end`/`start` candidate against earlier marks, below): a
        # later mark must not land inside an earlier inline label either.
        trial = SurfaceObstacleIndex()
        for existing in self._index.all():
            trial.add(existing)
        for member in members:
            for index, geometry in enumerate(all_mark_geometries[member.member_id]):
                trial.add(SurfaceObstacle(f"bundle-mark:{member.member_id}:{index}", _MARK_CLASS,
                                          self.lane_id, geometry, clearance=self._clearance))
        per_member: dict[str, LanePlacement] = {}
        for member in members:
            chosen: LanePlacement | None = None
            for level in LADDER:
                rect = self._member_rect(member, level)
                if ((self._canvas_left is not None and rect.left < self._canvas_left)
                        or (self._canvas_right is not None and rect.right > self._canvas_right)):
                    continue
                classes = tuple(_LABEL_CLASS_BY_LEVEL.values())
                if level in ("end", "start"):
                    classes += (_MARK_CLASS,)
                if not trial.collisions(rect, classes=classes, clearance=self._clearance):
                    chosen = LanePlacement(member.member_id, level, rect)
                    break
            if chosen is None:
                if not allow_visible_overflow:
                    return None
                chosen = LanePlacement(member.member_id, "visible-overflow",
                                       self.overflow_rect_for_member(member), visible_overflow=True)
            per_member[member.member_id] = chosen
            trial.add(SurfaceObstacle(f"bundle-label:{member.member_id}",
                                      _LABEL_CLASS_BY_LEVEL.get(chosen.level, "lane-label-overflow"),
                                      self.lane_id, chosen.rect, clearance=self._clearance))
        root = per_member[candidate.candidate_id]
        return LanePlacement(candidate.candidate_id, root.level, root.rect, root.visible_overflow,
                             MappingProxyType(per_member))

    def _mark_geometries(self, candidate: LaneCandidate) -> tuple[ObstacleGeometry, ...]:
        return self._member_mark_geometries(LaneMember(candidate.candidate_id, candidate.mark,
                                                       candidate.title_width, candidate.delta_width))

    def _member_mark_geometries(self, member: LaneMember) -> tuple[ObstacleGeometry, ...]:
        primary = ObstacleRect(member.mark.left, 0.0, member.mark.right, self._mark_row_height)
        for geometry in member.mark.footprints:
            _, top, _, bottom = obstacle_envelope(geometry)
            if top < 0.0 or bottom > self._mark_row_height:
                raise ValueError("E_LAYOUT_LANE_MARK_GEOMETRY")
        return (primary, *member.mark.footprints)

    def _candidate_rect(self, candidate: LaneCandidate, level: str) -> ObstacleRect:
        return self._member_rect(candidate.members_for_placement[0], level)

    def _member_rect(self, member: LaneMember, level: str) -> ObstacleRect:
        left, right = member.mark.left, member.mark.right
        width = member.label_width
        if level == "label-row-1":
            top = -self._label_row_height
            return ObstacleRect(left, top, left + width, top + self._label_row_height)
        if level == "label-row-2":
            top = -2 * self._label_row_height
            return ObstacleRect(right - width, top, right, top + self._label_row_height)
        if level == "label-row-3-start":
            top = -3 * self._label_row_height
            return ObstacleRect(left, top, left + width, top + self._label_row_height)
        if level == "label-row-3-end":
            top = -3 * self._label_row_height
            return ObstacleRect(right - width, top, right, top + self._label_row_height)
        if level == "end":
            return ObstacleRect(right, 0.0, right + width, self._mark_row_height)
        if level == "start":
            return ObstacleRect(left - width, 0.0, left, self._mark_row_height)
        raise ValueError("E_LAYOUT_LANE_LADDER_LEVEL")

    def accept(self, candidate: LaneCandidate, placement: LanePlacement) -> None:
        members = candidate.members_for_placement
        for member in members:
            for index, geometry in enumerate(self._member_mark_geometries(member)):
                self._index.add(SurfaceObstacle(f"{member.member_id}:mark:{index}", _MARK_CLASS,
                                                self.lane_id, geometry, clearance=self._clearance))
            member_placement = placement.member_placements.get(member.member_id, placement)
            obstacle_class = _LABEL_CLASS_BY_LEVEL.get(member_placement.level, "lane-label-overflow")
            rect = (self.overflow_rect_for_member(member) if member_placement.visible_overflow
                    else self._member_rect(member, member_placement.level))
            self._index.add(SurfaceObstacle(f"{member.member_id}:label", obstacle_class, self.lane_id,
                                            rect, clearance=self._clearance))
            self.members.append(member.member_id)
            self.placements[member.member_id] = LanePlacement(member.member_id, member_placement.level, rect,
                                                               member_placement.visible_overflow)
            rows = {"label-row-1": 1, "label-row-2": 2,
                    "label-row-3-start": 3, "label-row-3-end": 3}
            self.label_rows_used = max(self.label_rows_used, rows.get(member_placement.level, 0))

    def block_extent(self) -> float:
        return self._mark_row_height + self.label_rows_used * self._label_row_height

    def overflow_rect(self, candidate: LaneCandidate) -> ObstacleRect:
        return self.overflow_rect_for_member(candidate.members_for_placement[0])

    def overflow_rect_for_member(self, member: LaneMember) -> ObstacleRect:
        right = member.mark.right
        return ObstacleRect(right, 0.0, right + member.label_width, self._mark_row_height)


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
    if (not isfinite(mark_row_height) or mark_row_height <= 0
            or not isfinite(label_row_height) or label_row_height <= 0
            or not isfinite(clearance) or clearance < 0
            or any(bound is not None and not isfinite(bound) for bound in (canvas_left, canvas_right))
            or (canvas_left is not None and canvas_right is not None and canvas_right <= canvas_left)):
        raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
    all_member_ids = [member.member_id for item in candidates for member in item.members_for_placement]
    if len(set(all_member_ids)) != len(all_member_ids):
        raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
    orders: dict[str, tuple] = {}
    for item in candidates:
        if item.group_key in orders and orders[item.group_key] != item.group_order:
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        orders[item.group_key] = item.group_order
    ordered = sorted(candidates, key=lambda item: (item.group_order, item.group_key,
                                                    item.order_key, item.candidate_id))
    lanes: list[_Lane] = []
    lane_by_candidate: dict[str, _Lane] = {}
    by_id = {item.candidate_id: item for item in candidates}
    lane_counters: dict[str, int] = {}

    def open_lane(group_key: str, representative_id: str) -> _Lane:
        lane_counters[group_key] = lane_counters.get(group_key, 0) + 1
        group_identity = "u" if not group_key else "g" + quote(group_key, safe="")
        lane = _Lane(f"lane:{group_identity}:{quote(representative_id, safe='')}", group_key, representative_id,
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
                for member in candidate.members_for_placement:
                    lane_by_candidate[member.member_id] = lane
                accepted = True
                break
        if not accepted:
            lane = open_lane(candidate.group_key, candidate.candidate_id)
            placement = lane.try_place(candidate, allow_visible_overflow=True)
            if placement is None:
                # Even alone, no label candidate fits: record the terminal
                # visible-overflow placement rather than dropping the name.
                member_overflow = {member.member_id: LanePlacement(
                    member.member_id, "visible-overflow", lane.overflow_rect_for_member(member), True)
                    for member in candidate.members_for_placement}
                placement = LanePlacement(candidate.candidate_id, "visible-overflow",
                                          lane.overflow_rect(candidate), visible_overflow=True,
                                          member_placements=MappingProxyType(member_overflow))
            lane.accept(candidate, placement)
            for member in candidate.members_for_placement:
                lane_by_candidate[member.member_id] = lane

    return LaneAllocationResult(tuple(
        LaneAssignment(lane.lane_id, lane.group_key, lane.representative_id, tuple(lane.members),
                       MappingProxyType(dict(lane.placements)), lane.label_rows_used, lane.block_extent())
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


def _geometries_collide(left: ObstacleGeometry, right: ObstacleGeometry, clearance: float) -> bool:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("other", _MARK_CLASS, "bundle", right))
    return bool(index.collisions(left, classes=(_MARK_CLASS,), clearance=clearance))
