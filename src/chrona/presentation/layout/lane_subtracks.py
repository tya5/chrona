"""Fixed-membership lane mark subtracks from completed visible footprints.

Lane identity is supplied by Review's immutable, data-only membership result.
This module may separate overlapping marks *inside* those lanes, but it never
opens, merges, splits, or reorders lanes. Labels are deliberately not inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TypeAlias

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
class LaneItemFootprints:
    """One selected countable item's visible facets in a zero-origin mark frame."""

    item_id: str
    footprints: tuple[LaneFootprint, ...]


@dataclass(frozen=True)
class LaneSubtrack:
    """Completed vertical geometry for one fixed lane's internal mark tracks."""

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
    """One membership item and its completed track index/block translation."""

    item_id: str
    lane_id: str
    track_index: int
    block_offset: float

    def __post_init__(self) -> None:
        if (not self.item_id or not self.lane_id or self.track_index < 0
                or not isfinite(self.block_offset) or self.block_offset < 0):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INVALID")


@dataclass(frozen=True)
class LaneSubtrackPlan:
    """Lane summaries and item tracks, both in supplied membership order."""

    lanes: tuple[LaneSubtrack, ...]
    items: tuple[LaneItemSubtrack, ...]

    def item(self, item_id: str) -> LaneItemSubtrack:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise KeyError(item_id)


def assign_lane_subtracks(
    membership: LaneMembership,
    item_footprints: tuple[LaneItemFootprints, ...],
    *,
    mark_band_size: float,
    clearance: float = 0.0,
) -> LaneSubtrackPlan:
    """Assign first-compatible subtracks without changing ``membership``.

    Footprints are exact, target-independent Layout geometries relative to
    their item's mark-band origin. A lane pitch covers the full vertical union
    of every facet, the base mark band, and the requested clearance. This
    makes each later track safe even when an icon or stroked path protrudes
    beyond its base mark band.
    """
    _validate_metrics(mark_band_size, clearance)
    lane_members, assignments = _validate_membership(membership)
    footprints = _validate_footprints(item_footprints, set(assignments))

    lane_results: list[LaneSubtrack] = []
    item_results: list[LaneItemSubtrack] = []
    assignments_by_lane: dict[str, dict[str, LaneAssignment]] = {}
    for assignment in membership.assignments:
        assignments_by_lane.setdefault(assignment.lane_id, {})[assignment.item_id] = assignment

    for lane in membership.lanes:
        member_ids = lane_members[lane.lane_id]
        lane_assignments = assignments_by_lane[lane.lane_id]
        bundles = _atomic_bundles(member_ids, lane_assignments)

        min_top = 0.0
        max_bottom = mark_band_size
        for item_id in member_ids:
            for geometry in footprints[item_id]:
                _, top, _, bottom = obstacle_envelope(geometry)
                min_top = min(min_top, top)
                max_bottom = max(max_bottom, bottom)
        offset = max(0.0, -min_top)
        envelope_height = max(mark_band_size, max_bottom - min_top)
        pitch = envelope_height + clearance
        # Keep a strictly positive pitch even for degenerate zero-clearance
        # segment footprints, where the mark band is the only vertical extent.
        if not isfinite(pitch) or pitch <= 0 or not isfinite(offset):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")

        track_bundles: list[list[tuple[str, ...]]] = []
        bundle_tracks: dict[str, int] = {}
        for bundle in bundles:
            selected_track: int | None = None
            for track_index in range(len(track_bundles) + 1):
                if _fits_track(bundle, track_index, track_bundles, bundle_tracks,
                               footprints, offset, pitch, clearance):
                    selected_track = track_index
                    break
            if selected_track is None:  # a fresh vertically separated track must always fit
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_UNPLACEABLE")
            if selected_track == len(track_bundles):
                track_bundles.append([])
            track_bundles[selected_track].append(bundle)
            for item_id in bundle:
                bundle_tracks[item_id] = selected_track

        count = len(track_bundles)
        block_extent = offset + (count - 1) * pitch + max_bottom
        lane_results.append(LaneSubtrack(lane.lane_id, count, pitch, offset, block_extent))
        for item_id in member_ids:
            index = bundle_tracks[item_id]
            item_results.append(LaneItemSubtrack(
                item_id, lane.lane_id, index, offset + index * pitch,
            ))

    return LaneSubtrackPlan(tuple(lane_results), tuple(item_results))


def _validate_metrics(mark_band_size: float, clearance: float) -> None:
    values = (mark_band_size, clearance)
    if (any(not isinstance(value, (int, float)) or isinstance(value, bool)
            or not isfinite(value) for value in values)
            or mark_band_size <= 0 or clearance < 0):
        raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")


def _validate_membership(membership: LaneMembership) -> tuple[dict[str, tuple[str, ...]], dict[str, LaneAssignment]]:
    if not isinstance(membership, LaneMembership):
        raise TypeError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    if not isinstance(membership.lanes, tuple) or not isinstance(membership.assignments, tuple):
        raise TypeError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    lanes: dict[str, tuple[str, ...]] = {}
    for lane in membership.lanes:
        if (not isinstance(lane, Lane)
                or not isinstance(lane.lane_id, str) or not lane.lane_id
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
                or assignment.lane_id not in lanes
                or assignment.item_id not in lanes[assignment.lane_id]):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
        assignments[assignment.item_id] = assignment
    expected = {item_id for member_ids in lanes.values() for item_id in member_ids}
    if len(expected) != sum(map(len, lanes.values())) or set(assignments) != expected:
        raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    for lane in membership.lanes:
        if any(assignments[item_id].group_id != lane.group_id for item_id in lane.member_item_ids):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    return lanes, assignments


def _validate_footprints(
    values: tuple[LaneItemFootprints, ...], expected_ids: set[str],
) -> dict[str, tuple[LaneFootprint, ...]]:
    if not isinstance(values, tuple):
        raise TypeError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    result: dict[str, tuple[LaneFootprint, ...]] = {}
    for value in values:
        if (not isinstance(value, LaneItemFootprints)
                or not isinstance(value.item_id, str) or not value.item_id
                or value.item_id in result or not isinstance(value.footprints, tuple)
                or not value.footprints
                or any(not isinstance(geometry, (ObstacleRect, ObstacleSegment))
                       for geometry in value.footprints)):
            raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
        result[value.item_id] = value.footprints
    if set(result) != expected_ids:
        raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
    return result


def _atomic_bundles(
    member_ids: tuple[str, ...], assignments: dict[str, LaneAssignment],
) -> tuple[tuple[str, ...], ...]:
    """Group attachment children with their declared host, in membership order."""
    bundle_members: dict[str, list[str]] = {}
    member_positions = {item_id: index for index, item_id in enumerate(member_ids)}
    for index, item_id in enumerate(member_ids):
        assignment = assignments[item_id]
        if assignment.rule == "attached":
            host_id = assignment.source_id
            host = assignments.get(host_id)
            if (host is None or host.lane_id != assignment.lane_id
                    or host.rule == "attached" or host_id == item_id
                    or member_positions[host_id] >= index):
                raise ValueError("E_LAYOUT_LANE_SUBTRACK_INPUT")
            bundle_id = host_id
        else:
            bundle_id = item_id
        bundle_members.setdefault(bundle_id, []).append(item_id)
    return tuple(tuple(member_ids) for member_ids in bundle_members.values())


def _fits_track(
    candidate: tuple[str, ...],
    candidate_index: int,
    tracks: list[list[tuple[str, ...]]],
    item_track: dict[str, int],
    footprints: dict[str, tuple[LaneFootprint, ...]],
    offset: float,
    pitch: float,
    clearance: float,
) -> bool:
    candidate_offset = offset + candidate_index * pitch
    for existing_track in tracks:
        for existing_bundle in existing_track:
            existing_index = item_track[existing_bundle[0]]
            existing_offset = offset + existing_index * pitch
            if _bundles_collide(candidate, candidate_offset, existing_bundle,
                                existing_offset, footprints, clearance):
                return False
    return True


def _bundles_collide(
    left: tuple[str, ...], left_offset: float,
    right: tuple[str, ...], right_offset: float,
    footprints: dict[str, tuple[LaneFootprint, ...]], clearance: float,
) -> bool:
    for left_id in left:
        for right_id in right:
            for left_geometry in footprints[left_id]:
                shifted_left = _translate_block(left_geometry, left_offset)
                for right_geometry in footprints[right_id]:
                    shifted_right = _translate_block(right_geometry, right_offset)
                    if obstacles_intersect(shifted_left, shifted_right, clearance):
                        return True
    return False


def _translate_block(geometry: ObstacleGeometry, offset: float) -> ObstacleGeometry:
    if isinstance(geometry, ObstacleRect):
        return ObstacleRect(geometry.left, geometry.top + offset,
                            geometry.right, geometry.bottom + offset)
    return ObstacleSegment((geometry.start[0], geometry.start[1] + offset),
                           (geometry.end[0], geometry.end[1] + offset),
                           geometry.stroke_width)
