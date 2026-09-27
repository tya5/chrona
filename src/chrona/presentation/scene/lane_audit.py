"""Read-only lane-rule audit over serialized Scene lane inventories."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
from typing import Any, Mapping

from chrona.presentation.layout.obstacles import (
    ObstacleGeometry, ObstacleRect, ObstacleSegment, obstacle_envelope, obstacles_intersect,
)


class SceneLaneAuditError(ValueError):
    """Serialized lane evidence is incomplete or malformed for a closed audit."""


@dataclass(frozen=True)
class LaneCollisionWitness:
    source_lane_id: str
    target_lane_id: str
    source_member_id: str
    source_primitive_id: str
    source_facet_id: str
    target_member_id: str
    target_primitive_id: str
    target_facet_id: str
    source_class: str
    target_class: str


@dataclass(frozen=True)
class LanePairAudit:
    group_id: str
    lane_a_id: str
    lane_b_id: str
    a_into_b: LaneCollisionWitness | None
    b_into_a: LaneCollisionWitness | None

    @property
    def non_redundant(self) -> bool:
        return self.a_into_b is not None and self.b_into_a is not None


@dataclass(frozen=True)
class LaneGroupAudit:
    group_id: str
    lane_count: int
    primary_mark_lower_bound: int
    lane_gap: int
    gap_witnesses: tuple[LaneCollisionWitness, ...]


@dataclass(frozen=True)
class SceneLaneAudit:
    groups: tuple[LaneGroupAudit, ...]
    lane_pairs: tuple[LanePairAudit, ...]

    @property
    def non_redundant(self) -> bool:
        return all(pair.non_redundant for pair in self.lane_pairs)


@dataclass(frozen=True)
class _Obstacle:
    facet_id: str
    primitive_id: str
    row_id: str
    member_id: str
    obstacle_class: str
    geometry: ObstacleGeometry


def audit_serialized_lane_surface(surface: Mapping[str, Any]) -> SceneLaneAudit:
    """Audit a serialized Scene surface without consulting Layout or paint.

    Lane merge checks translate each completed obstacle only in block position
    from its source mark-band anchor to the target anchor. Inline coordinates,
    geometry, and the single surface clearance stay fixed. This contract has no
    enforced chain-separation exceptions.
    """
    rows, members, obstacles, clearance = _closed_inputs(surface)
    obstacles_by_member: dict[tuple[str, str], list[_Obstacle]] = {}
    for obstacle in obstacles:
        obstacles_by_member.setdefault((obstacle.row_id, obstacle.member_id), []).append(obstacle)

    lane_rows_by_group: dict[str, list[tuple[str, float]]] = {}
    for row_id, row in rows.items():
        lane_rows_by_group.setdefault(row["group_id"], []).append((row_id, row["anchor"]))
    for lanes in lane_rows_by_group.values():
        lanes.sort(key=lambda item: item[0])

    pair_audits: list[LanePairAudit] = []
    for group_id, lanes in sorted(lane_rows_by_group.items()):
        for (lane_a, anchor_a), (lane_b, anchor_b) in combinations(lanes, 2):
            a_witness = _merge_witness(
                lane_a, anchor_a, lane_b, anchor_b, obstacles_by_member, clearance)
            b_witness = _merge_witness(
                lane_b, anchor_b, lane_a, anchor_a, obstacles_by_member, clearance)
            pair_audits.append(LanePairAudit(group_id, lane_a, lane_b, a_witness, b_witness))

    primary_bounds: dict[str, int] = {
        group_id: _primary_mark_concurrency(group_lanes, members, obstacles_by_member)
        for group_id, group_lanes in lane_rows_by_group.items()
    }
    lane_counts = {group_id: len(lanes) for group_id, lanes in lane_rows_by_group.items()}
    groups: list[LaneGroupAudit] = []
    for group_id in sorted(lane_rows_by_group):
        pair_witnesses = tuple(
            witness for pair in pair_audits if pair.group_id == group_id
            for witness in (pair.a_into_b, pair.b_into_a) if witness is not None
        )
        count, lower_bound = lane_counts[group_id], primary_bounds[group_id]
        groups.append(LaneGroupAudit(group_id, count, lower_bound, count - lower_bound,
                                     pair_witnesses))
    return SceneLaneAudit(tuple(groups), tuple(pair_audits))


def _closed_inputs(surface: Mapping[str, Any]) -> tuple[
        dict[str, dict[str, Any]], dict[tuple[str, str], Mapping[str, Any]], tuple[_Obstacle, ...], float]:
    if not isinstance(surface, Mapping) or surface.get("laneMode") != "lanes":
        raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
    clearance = surface.get("laneClearance")
    if not _number(clearance) or clearance < 0:
        raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
    rows_doc, members_doc, obstacles_doc = (surface.get("rows"), surface.get("laneMembers"),
                                            surface.get("laneObstacles"))
    if not all(isinstance(value, list) and value for value in (rows_doc, members_doc, obstacles_doc)):
        raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")

    rows: dict[str, dict[str, Any]] = {}
    for row in rows_doc:
        if not isinstance(row, Mapping):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        row_id, group_id, anchor = row.get("id"), row.get("groupId"), row.get("laneMarkBandBlock")
        if (not _identity(row_id) or not isinstance(group_id, str) or not _number(anchor)
                or row_id in rows):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        rows[row_id] = {"group_id": group_id, "anchor": anchor}

    members: dict[tuple[str, str], Mapping[str, Any]] = {}
    expected_primitives: dict[str, tuple[str, str]] = {}
    rows_with_members: set[str] = set()
    for member in members_doc:
        if not isinstance(member, Mapping):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        row_id, member_id = member.get("rowId"), member.get("memberId")
        emitted, primary = member.get("emittedPrimitiveIds"), member.get("primaryMarkIds")
        if (not _identity(row_id) or row_id not in rows or not _identity(member_id)
                or not isinstance(emitted, list) or not emitted
                or not isinstance(primary, list) or not primary
                or any(not _identity(item) for item in (*emitted, *primary))
                or len(set(emitted)) != len(emitted) or len(set(primary)) != len(primary)
                or not set(primary) <= set(emitted)):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        key = (row_id, member_id)
        if key in members:
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        members[key] = member
        rows_with_members.add(row_id)
        for primitive_id in emitted:
            if not _identity(primitive_id) or primitive_id in expected_primitives:
                raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
            expected_primitives[primitive_id] = key
    if rows_with_members != set(rows):
        raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")

    obstacles: list[_Obstacle] = []
    facets: set[str] = set()
    covered_primitives: set[str] = set()
    primary_ids = {primitive_id for member in members.values()
                   for primitive_id in member["primaryMarkIds"]}
    primary_obstacle_ids: set[str] = set()
    for item in obstacles_doc:
        if not isinstance(item, Mapping):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        facet_id, primitive_id = item.get("facetId"), item.get("primitiveId")
        row_id, member_id, obstacle_class = (item.get("rowId"), item.get("memberId"), item.get("class"))
        key = (row_id, member_id)
        geometry = _geometry(item.get("geometry"))
        if (not _identity(facet_id) or facet_id in facets
                or not _identity(primitive_id) or not _identity(row_id) or not _identity(member_id)
                or expected_primitives.get(primitive_id) != key
                or not isinstance(obstacle_class, str)
                or obstacle_class not in {"mark", "required-label"}):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        facets.add(facet_id)
        covered_primitives.add(primitive_id)
        obstacle = _Obstacle(facet_id, primitive_id, row_id, member_id, obstacle_class, geometry)
        obstacles.append(obstacle)
        if primitive_id in primary_ids:
            if obstacle_class != "mark":
                raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
            primary_obstacle_ids.add(primitive_id)
    if covered_primitives != set(expected_primitives) or primary_obstacle_ids != primary_ids:
        raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
    for obstacle in obstacles:
        obstacles_by_key = expected_primitives.get(obstacle.primitive_id)
        if obstacles_by_key is None:
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
    return rows, members, tuple(obstacles), float(clearance)


def _geometry(value: Any) -> ObstacleGeometry:
    if not isinstance(value, Mapping):
        raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
    if value.get("kind") == "rect":
        left, top, right, bottom = (value.get(name) for name in ("left", "top", "right", "bottom"))
        if not all(_number(item) for item in (left, top, right, bottom)) or right <= left or bottom <= top:
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        return ObstacleRect(float(left), float(top), float(right), float(bottom))
    if value.get("kind") == "stroked-segment":
        start, end, stroke = value.get("start"), value.get("end"), value.get("strokeWidth")
        if (not isinstance(start, list) or len(start) != 2 or not isinstance(end, list) or len(end) != 2
                or not all(_number(item) for item in (*start, *end, stroke)) or stroke < 0
                or start == end):
            raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")
        return ObstacleSegment((float(start[0]), float(start[1])),
                               (float(end[0]), float(end[1])), float(stroke))
    raise SceneLaneAuditError("E_SCENE_LANE_AUDIT_INVALID")


def _merge_witness(source_row: str, source_anchor: float, target_row: str, target_anchor: float,
                   by_member: Mapping[tuple[str, str], list[_Obstacle]], clearance: float
                   ) -> LaneCollisionWitness | None:
    source = sorted((item for (row_id, _), values in by_member.items() if row_id == source_row
                     for item in values), key=_obstacle_sort_key)
    target = sorted((item for (row_id, _), values in by_member.items() if row_id == target_row
                     for item in values), key=_obstacle_sort_key)
    shift = target_anchor - source_anchor
    for moving in source:
        moved_geometry = _translate_block(moving.geometry, shift)
        for fixed in target:
            if obstacles_intersect(moved_geometry, fixed.geometry, clearance):
                return LaneCollisionWitness(
                    source_row, target_row, moving.member_id, moving.primitive_id, moving.facet_id,
                    fixed.member_id, fixed.primitive_id, fixed.facet_id,
                    moving.obstacle_class, fixed.obstacle_class,
                )
    return None


def _translate_block(geometry: ObstacleGeometry, delta: float) -> ObstacleGeometry:
    if isinstance(geometry, ObstacleRect):
        return ObstacleRect(geometry.left, geometry.top + delta,
                            geometry.right, geometry.bottom + delta)
    return ObstacleSegment((geometry.start[0], geometry.start[1] + delta),
                           (geometry.end[0], geometry.end[1] + delta), geometry.stroke_width)


def _primary_mark_concurrency(group_lanes: list[tuple[str, float]],
                              members: Mapping[tuple[str, str], Mapping[str, Any]],
                              obstacles_by_member: Mapping[tuple[str, str], list[_Obstacle]]) -> int:
    lane_ids = {row_id for row_id, _ in group_lanes}
    intervals_by_member: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for key, member in members.items():
        row_id, _member_id = key
        if row_id not in lane_ids:
            continue
        intervals: list[tuple[float, float]] = []
        primary_ids = set(member["primaryMarkIds"])
        for obstacle in obstacles_by_member.get(key, ()):
            if obstacle.primitive_id not in primary_ids:
                continue
            left, _top, right, _bottom = obstacle_envelope(obstacle.geometry)
            if left < right:
                intervals.append((left, right))
        for start, end in _merge_intervals(intervals):
            intervals_by_member.setdefault(key, []).append((start, end))
    events: list[tuple[float, int]] = []
    for intervals in intervals_by_member.values():
        for start, end in intervals:
            # Ends sort ahead of starts at equal coordinates: intervals are half-open.
            events.extend(((start, 1), (end, -1)))
    active = maximum = 0
    for _position, delta in sorted(events, key=lambda item: (item[0], item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def _merge_intervals(intervals: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((start, end) for start, end in merged)


def _obstacle_sort_key(value: _Obstacle) -> tuple[str, str, str]:
    return value.member_id, value.primitive_id, value.facet_id


def _identity(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
