"""Fixed-membership subtracks from source-keyed, completed mark facets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import isfinite
from typing import TypeAlias

from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_preflight import LaneInlineFrame
from chrona.presentation.layout.obstacles import (
    ObstacleGeometry,
    ObstacleRect,
    ObstacleSegment,
    obstacle_envelope,
    obstacles_intersect,
)
from chrona.presentation.review.lane_membership import (
    Lane,
    LaneAssignment,
    LaneMembership,
)

LaneFootprint: TypeAlias = ObstacleRect | ObstacleSegment


@dataclass(frozen=True)
class LaneFacetFootprint:
    """One source-keyed visible primitive footprint and exact overlay targets."""

    facet_id: str
    footprint: LaneFootprint
    overlay_with: tuple[str, ...] = ()


@dataclass(frozen=True)
class LaneItemFootprints:
    """One flattened Review projection instance within a countable member."""

    item_id: str
    projection_instance_id: LaneProjectionInstance
    facets: tuple[LaneFacetFootprint, ...]


@dataclass(frozen=True)
class LaneSubtrack:
    """Completed vertical geometry for one fixed lane's internal tracks."""

    lane_id: str
    subtrack_count: int
    pitch: float
    offset: float
    block_extent: float

    def __post_init__(self) -> None:
        if (not self.lane_id or self.subtrack_count < 1
                or not all(isfinite(value) for value in (self.pitch, self.offset, self.block_extent))
                or self.pitch <= 0 or self.offset < 0 or self.block_extent <= 0):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INVALID")


@dataclass(frozen=True)
class LaneItemSubtrack:
    """One projection instance's completed track index/block translation."""

    item_id: str
    projection_instance_id: LaneProjectionInstance
    lane_id: str
    track_index: int
    block_offset: float

    def __post_init__(self) -> None:
        if (not self.item_id or not isinstance(self.projection_instance_id, LaneProjectionInstance)
                or not self.lane_id or self.track_index < 0
                or not isfinite(self.block_offset) or self.block_offset < 0):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INVALID")


@dataclass(frozen=True)
class LaneSubtrackPlan:
    """Lane summaries and projection-instance tracks in deterministic order."""

    lanes: tuple[LaneSubtrack, ...]
    items: tuple[LaneItemSubtrack, ...]

    def instance(self, projection_instance_id: LaneProjectionInstance) -> LaneItemSubtrack:
        for item in self.items:
            if item.projection_instance_id == projection_instance_id:
                return item
        raise KeyError(projection_instance_id)

    def item(self, item_id: str) -> LaneItemSubtrack:
        matches = [item for item in self.items if item.item_id == item_id]
        if len(matches) != 1:
            raise KeyError(item_id)
        return matches[0]


@dataclass(frozen=True)
class FixedLanePreflight:
    """One measured Layout closure reused by final host allocation and paint."""

    subtracks: LaneSubtrackPlan
    seed_inline_frame: LaneInlineFrame
    natural_block_requirement: Decimal
    as_of: date | None

    def __post_init__(self) -> None:
        if (not self.natural_block_requirement.is_finite()
                or self.natural_block_requirement < 0):
            raise ValueError("E_LAYOUT_LANE_PREFLIGHT_INVALID")


def assign_lane_subtracks(
    membership: LaneMembership,
    item_footprints: tuple[LaneItemFootprints, ...],
    *,
    mark_band_size: float,
    clearance: float = 0.0,
) -> LaneSubtrackPlan:
    """Place projection instances inside immutable data-only lanes.

    Every instance moves as one unit. Intersections are accepted only for
    exact, symmetric facet overlay declarations. Attached children try the
    host's track first, then use ordinary first-compatible tracks; membership
    is never changed.
    """
    _validate_metrics(mark_band_size, clearance)
    lane_members, assignments = _validate_membership(membership)
    units, overlay_pairs = _validate_footprints(item_footprints, set(assignments), assignments)
    ordered_units = [unit for lane in membership.lanes for item_id in lane_members[lane.lane_id]
                     for unit in units[item_id]]

    lane_results: list[LaneSubtrack] = []
    item_results: list[LaneItemSubtrack] = []
    for lane in membership.lanes:
        member_ids = lane_members[lane.lane_id]
        roots = [item_id for item_id in member_ids if assignments[item_id].rule != "attached"]
        children = [item_id for item_id in member_ids if assignments[item_id].rule == "attached"]
        for child_id in children:
            host_id = assignments[child_id].source_id
            if (host_id not in member_ids or assignments[host_id].rule == "attached"
                    or assignments[host_id].lane_id != lane.lane_id):
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
        lane_units = [unit for item_id in (*roots, *children) for unit in units[item_id]]
        _validate_intra_instance_collisions(lane_units, overlay_pairs, clearance)
        min_top = 0.0
        max_bottom = mark_band_size
        for unit in lane_units:
            for facet in unit.facets:
                _, top, _, bottom = obstacle_envelope(facet.footprint)
                min_top = min(min_top, top)
                max_bottom = max(max_bottom, bottom)
        offset = max(0.0, -min_top)
        pitch = max(mark_band_size, max_bottom - min_top) + clearance
        if not isfinite(pitch) or pitch <= 0 or not isfinite(offset):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")

        lane_assignments = {item_id: assignments[item_id] for item_id in member_ids}
        host_tracks: dict[str, list[int]] = {}
        placed: list[tuple[LaneItemFootprints, int]] = []
        max_track = -1
        for unit in lane_units:
            assignment = lane_assignments[unit.item_id]
            preferred = (host_tracks.get(assignment.source_id, [])
                         if assignment.rule == "attached" else [])
            track_order = list(dict.fromkeys((*preferred, *range(max_track + 2))))
            selected = next((index for index in track_order
                             if _fits_track(unit, index, placed, offset, pitch,
                                            overlay_pairs, clearance)), None)
            if selected is None:
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_UNPLACEABLE")
            placed.append((unit, selected))
            max_track = max(max_track, selected)
            host_tracks.setdefault(unit.item_id, []).append(selected)
            item_results.append(LaneItemSubtrack(
                unit.item_id, unit.projection_instance_id, lane.lane_id, selected,
                offset + selected * pitch,
            ))

        count = max_track + 1
        lane_results.append(LaneSubtrack(
            lane.lane_id, count, pitch, offset,
            offset + (count - 1) * pitch + max_bottom,
        ))

    # Preserve lane membership order and each member's source projection order.
    result_order = {(unit.item_id, unit.projection_instance_id): index
                    for index, unit in enumerate(ordered_units)}
    item_results.sort(key=lambda item: result_order[(item.item_id, item.projection_instance_id)])
    return LaneSubtrackPlan(tuple(lane_results), tuple(item_results))


def _validate_metrics(mark_band_size: float, clearance: float) -> None:
    values = (mark_band_size, clearance)
    if (any(not isinstance(value, (int, float)) or isinstance(value, bool)
            or not isfinite(value) for value in values)
            or mark_band_size <= 0 or clearance < 0):
        raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")


def _validate_membership(membership: LaneMembership) -> tuple[dict[str, tuple[str, ...]], dict[str, LaneAssignment]]:
    if (not isinstance(membership, LaneMembership) or not isinstance(membership.lanes, tuple)
            or not isinstance(membership.assignments, tuple)):
        raise TypeError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    lanes: dict[str, tuple[str, ...]] = {}
    for lane in membership.lanes:
        if (not isinstance(lane, Lane) or not isinstance(lane.lane_id, str) or not lane.lane_id
                or not isinstance(lane.group_id, str)
                or not isinstance(lane.member_item_ids, tuple) or not lane.member_item_ids
                or any(not isinstance(item_id, str) or not item_id for item_id in lane.member_item_ids)
                or len(set(lane.member_item_ids)) != len(lane.member_item_ids)
                or lane.lane_id in lanes):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
        lanes[lane.lane_id] = lane.member_item_ids
    assignments: dict[str, LaneAssignment] = {}
    for assignment in membership.assignments:
        if (not isinstance(assignment, LaneAssignment)
                or not isinstance(assignment.item_id, str) or not assignment.item_id
                or not isinstance(assignment.lane_id, str) or not assignment.lane_id
                or not isinstance(assignment.group_id, str)
                or not isinstance(assignment.rule, str)
                or assignment.rule not in {"explicit", "attached", "chain", "dates", "single"}
                or not isinstance(assignment.source_id, str) or not assignment.source_id
                or assignment.item_id in assignments
                or assignment.lane_id not in lanes or assignment.item_id not in lanes[assignment.lane_id]):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
        assignments[assignment.item_id] = assignment
    member_order = tuple(item_id for member_ids in lanes.values() for item_id in member_ids)
    expected = set(member_order)
    if len(expected) != len(member_order) or set(assignments) != expected:
        raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    for lane in membership.lanes:
        if any(assignments[item_id].group_id != lane.group_id for item_id in lane.member_item_ids):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    return lanes, assignments


def _validate_footprints(
    values: tuple[LaneItemFootprints, ...], expected_ids: set[str],
    assignments: dict[str, LaneAssignment],
) -> tuple[dict[str, list[LaneItemFootprints]], set[frozenset[str]]]:
    if not isinstance(values, tuple):
        raise TypeError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    result: dict[str, list[LaneItemFootprints]] = {item_id: [] for item_id in expected_ids}
    facet_owner: dict[str, tuple[LaneItemFootprints, LaneFacetFootprint]] = {}
    overlay_pairs: set[frozenset[str]] = set()
    instance_ids: set[LaneProjectionInstance] = set()
    for unit in values:
        if (not isinstance(unit, LaneItemFootprints)
                or not isinstance(unit.item_id, str) or unit.item_id not in expected_ids
                or not isinstance(unit.projection_instance_id, LaneProjectionInstance)
                or unit.projection_instance_id in instance_ids
                or not isinstance(unit.facets, tuple) or not unit.facets):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
        instance_ids.add(unit.projection_instance_id)
        result[unit.item_id].append(unit)
        for facet in unit.facets:
            if (not isinstance(facet, LaneFacetFootprint) or not facet.facet_id
                    or facet.facet_id in facet_owner or not isinstance(facet.overlay_with, tuple)
                    or any(not isinstance(target, str) or not target or target == facet.facet_id
                           for target in facet.overlay_with)
                    or len(set(facet.overlay_with)) != len(facet.overlay_with)
                    or not isinstance(facet.footprint, (ObstacleRect, ObstacleSegment))):
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
            facet_owner[facet.facet_id] = (unit, facet)
    if any(not result[item_id] for item_id in expected_ids):
        raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    for facet_id, (unit, facet) in facet_owner.items():
        for target in facet.overlay_with:
            other = facet_owner.get(target)
            if other is None or assignments[other[0].item_id].lane_id != assignments[unit.item_id].lane_id:
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_OVERLAY_INVALID")
            target_facet = other[1]
            if facet_id not in target_facet.overlay_with:
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_OVERLAY_INVALID")
            overlay_pairs.add(frozenset((facet_id, target)))
    return result, overlay_pairs


def _validate_intra_instance_collisions(
    units: list[LaneItemFootprints], overlay_pairs: set[frozenset[str]], clearance: float,
) -> None:
    for unit in units:
        for index, left in enumerate(unit.facets):
            for right in unit.facets[index + 1:]:
                if (obstacles_intersect(left.footprint, right.footprint, clearance)
                        and frozenset((left.facet_id, right.facet_id)) not in overlay_pairs):
                    raise ValueError(f"E_LAYOUT_LANE_SUBTRACK_OVERLAY_MISSING:{left.facet_id}:{right.facet_id}")


def _fits_track(
    candidate: LaneItemFootprints,
    candidate_index: int,
    placed: list[tuple[LaneItemFootprints, int]],
    offset: float,
    pitch: float,
    overlay_pairs: set[frozenset[str]],
    clearance: float,
) -> bool:
    candidate_offset = offset + candidate_index * pitch
    for existing, existing_index in placed:
        if existing_index != candidate_index:
            continue
        existing_offset = offset + existing_index * pitch
        for left in candidate.facets:
            shifted_left = _translate_block(left.footprint, candidate_offset)
            for right in existing.facets:
                if frozenset((left.facet_id, right.facet_id)) in overlay_pairs:
                    continue
                if obstacles_intersect(shifted_left, _translate_block(right.footprint, existing_offset), clearance):
                    return False
    return True


def _translate_block(geometry: ObstacleGeometry, offset: float) -> ObstacleGeometry:
    if isinstance(geometry, ObstacleRect):
        return ObstacleRect(geometry.left, geometry.top + offset,
                            geometry.right, geometry.bottom + offset)
    return ObstacleSegment((geometry.start[0], geometry.start[1] + offset),
                           (geometry.end[0], geometry.end[1] + offset),
                           geometry.stroke_width)
