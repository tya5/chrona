"""Deterministic, data-only lane membership for Review presentation.

This module deliberately knows nothing about rendering or geometry.  It
assigns selected Review items to group-local lanes from planned dates, View
intent, attachment facts, and selected finish-to-start relation facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import TypeAlias


@dataclass(frozen=True)
class PlannedSpan:
    """A planned half-open interval [start, end)."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if type(self.start) is not date or type(self.end) is not date or self.end < self.start:
            raise LaneMembershipError("E_REVIEW_LANE_INVALID_SPAN")


@dataclass(frozen=True)
class PlannedPoint:
    """A planned point at one calendar instant."""

    at: date

    def __post_init__(self) -> None:
        if type(self.at) is not date:
            raise LaneMembershipError("E_REVIEW_LANE_INVALID_POINT")


PlannedInterval: TypeAlias = PlannedSpan | PlannedPoint


@dataclass(frozen=True)
class LaneItem:
    """One countable selected item; IDs are stable identities, not ordinals."""

    item_id: str
    object_id: str
    group_id: str
    planned: PlannedInterval
    explicit_key: str | None = None
    attached_host_item_id: str | None = None


@dataclass(frozen=True)
class SelectedFSRelation:
    """A selected end-to-start relation, expressed using Project object IDs."""

    relation_id: str
    predecessor_object_id: str
    successor_object_id: str


PackingRule: TypeAlias = str
_RULES = ("explicit", "attached", "chain", "dates")


@dataclass(frozen=True)
class LanePackingInput:
    items: tuple[LaneItem, ...]
    packing: tuple[PackingRule, ...] = ("explicit", "attached")
    selected_fs_relations: tuple[SelectedFSRelation, ...] = ()


@dataclass(frozen=True)
class LaneAssignment:
    item_id: str
    lane_id: str
    group_id: str
    rule: str
    source_id: str


@dataclass(frozen=True)
class Lane:
    lane_id: str
    group_id: str
    member_item_ids: tuple[str, ...]
    explicit_key: str | None = None


@dataclass(frozen=True)
class LaneMembership:
    lanes: tuple[Lane, ...]
    assignments: tuple[LaneAssignment, ...]

    def assignment_for(self, item_id: str) -> LaneAssignment:
        for assignment in self.assignments:
            if assignment.item_id == item_id:
                return assignment
        raise KeyError(item_id)


class LaneMembershipError(ValueError):
    """Stable fail-closed diagnostic for invalid lane membership input."""


@dataclass
class _Bundle:
    root: LaneItem
    members: tuple[LaneItem, ...]
    explicit_key: str | None


@dataclass
class _MutableLane:
    lane_id: str
    group_id: str
    explicit_key: str | None
    bundles: list[_Bundle]


def _interval_start(item: LaneItem) -> date:
    return item.planned.start if isinstance(item.planned, PlannedSpan) else item.planned.at


def _interval_end(item: LaneItem) -> date:
    return item.planned.end if isinstance(item.planned, PlannedSpan) else item.planned.at


def _item_order(item: LaneItem) -> tuple[date, date, str, str]:
    return (_interval_start(item), _interval_end(item), item.object_id, item.item_id)


def _overlaps(left: PlannedInterval, right: PlannedInterval) -> bool:
    if isinstance(left, PlannedPoint) and isinstance(right, PlannedPoint):
        return left.at == right.at
    if isinstance(left, PlannedPoint):
        return right.start <= left.at < right.end
    if isinstance(right, PlannedPoint):
        return left.start <= right.at < left.end
    return left.start < right.end and right.start < left.end


def _lane_id(group_id: str, *, key: str | None = None, founder: str | None = None) -> str:
    identity = ("explicit", group_id, key) if key is not None else ("generated", group_id, founder)
    return "review-lane:" + json.dumps(identity, ensure_ascii=False, separators=(",", ":"))


def _validate_input(value: LanePackingInput) -> None:
    if not isinstance(value, LanePackingInput):
        raise TypeError("value must be LanePackingInput")
    if any(rule not in _RULES for rule in value.packing) or len(set(value.packing)) != len(value.packing):
        raise LaneMembershipError("E_REVIEW_LANE_PACKING")
    if tuple(rule for rule in _RULES if rule in value.packing) != value.packing:
        raise LaneMembershipError("E_REVIEW_LANE_PACKING_ORDER")
    item_ids = [item.item_id for item in value.items]
    if any(not isinstance(item_id, str) or not item_id for item_id in item_ids) or len(set(item_ids)) != len(item_ids):
        raise LaneMembershipError("E_REVIEW_LANE_DUPLICATE_ITEM")
    for item in value.items:
        if (not isinstance(item, LaneItem) or not isinstance(item.object_id, str) or not item.object_id
                or not isinstance(item.group_id, str) or not item.group_id
                or not isinstance(item.planned, (PlannedSpan, PlannedPoint))):
            raise LaneMembershipError("E_REVIEW_LANE_ITEM_IDENTITY")
        if item.explicit_key is not None and (not isinstance(item.explicit_key, str) or not item.explicit_key):
            raise LaneMembershipError("E_REVIEW_LANE_KEY")
    by_group_object: set[tuple[str, str]] = set()
    for item in value.items:
        identity = item.group_id, item.object_id
        if identity in by_group_object:
            raise LaneMembershipError("E_REVIEW_LANE_DUPLICATE_OBJECT")
        by_group_object.add(identity)
    relation_ids = [relation.relation_id for relation in value.selected_fs_relations]
    if any(not isinstance(value, str) or not value for relation in value.selected_fs_relations
           for value in (relation.relation_id, relation.predecessor_object_id, relation.successor_object_id)):
        raise LaneMembershipError("E_REVIEW_LANE_RELATION")
    if len(relation_ids) != len(set(relation_ids)):
        raise LaneMembershipError("E_REVIEW_LANE_DUPLICATE_RELATION")


def _make_bundles(value: LanePackingInput) -> tuple[_Bundle, ...]:
    items_by_id = {item.item_id: item for item in value.items}
    attached = "attached" in value.packing
    children: dict[str, list[LaneItem]] = {}
    for item in value.items:
        host_id = item.attached_host_item_id if attached else None
        if host_id is None:
            continue
        host = items_by_id.get(host_id)
        if host is None or host.group_id != item.group_id or not isinstance(item.planned, PlannedPoint) or not isinstance(host.planned, PlannedSpan):
            raise LaneMembershipError("E_REVIEW_LANE_ATTACHMENT")
        children.setdefault(host_id, []).append(item)

    consumed = {child.item_id for members in children.values() for child in members}
    bundles: list[_Bundle] = []
    for root in value.items:
        if root.item_id in consumed:
            continue
        members = (root, *sorted(children.get(root.item_id, ()), key=_item_order))
        keys = ({member.explicit_key for member in members if member.explicit_key is not None}
                if "explicit" in value.packing else set())
        if len(keys) > 1:
            raise LaneMembershipError("E_REVIEW_LANE_KEY_CONFLICT")
        bundles.append(_Bundle(root, members, next(iter(keys), None)))
    return tuple(bundles)


def derive_lane_membership(value: LanePackingInput) -> LaneMembership:
    """Return immutable, deterministic group-local lane assignments."""
    _validate_input(value)
    bundles = _make_bundles(value)
    item_to_bundle = {item.item_id: bundle for bundle in bundles for item in bundle.members}
    lanes: dict[tuple[str, str], _MutableLane] = {}
    assignments: dict[str, tuple[_MutableLane, str, str]] = {}

    # Authored explicit keys are materialized before generated allocation.
    if "explicit" in value.packing:
        keyed: dict[tuple[str, str], list[_Bundle]] = {}
        for bundle in bundles:
            if bundle.explicit_key is not None:
                keyed.setdefault((bundle.root.group_id, bundle.explicit_key), []).append(bundle)
        for (group_id, key), keyed_bundles in sorted(keyed.items()):
            lane = _MutableLane(_lane_id(group_id, key=key), group_id, key, [])
            for bundle in sorted(keyed_bundles, key=lambda entry: _item_order(entry.root)):
                lane.bundles.append(bundle)
                assignments[bundle.root.item_id] = (lane, "explicit", key)
            lanes[group_id, lane.lane_id] = lane

    placed = {bundle.root.item_id for bundle in bundles if bundle.root.item_id in assignments}
    pending = sorted((bundle for bundle in bundles if bundle.root.item_id not in placed), key=lambda entry: _item_order(entry.root))
    relations_by_successor: dict[str, list[tuple[SelectedFSRelation, _Bundle]]] = {}
    item_by_group_object = {(item.group_id, item.object_id): item for item in value.items}
    for relation in value.selected_fs_relations:
        successors = [item for item in value.items if item.object_id == relation.successor_object_id]
        for successor in successors:
            predecessor = item_by_group_object.get((successor.group_id, relation.predecessor_object_id))
            if predecessor is None:
                continue
            predecessor_bundle = item_to_bundle[predecessor.item_id]
            relations_by_successor.setdefault(successor.item_id, []).append((relation, predecessor_bundle))

    for bundle in pending:
        lane: _MutableLane | None = None
        rule = "single"
        source_id = bundle.root.item_id
        group_id = bundle.root.group_id

        if "chain" in value.packing:
            candidates = []
            for relation, predecessor_bundle in relations_by_successor.get(bundle.root.item_id, ()):
                predecessor_assignment = assignments.get(predecessor_bundle.root.item_id)
                predecessor = predecessor_bundle.root
                if predecessor_assignment is None or _interval_end(predecessor) != _interval_start(bundle.root):
                    continue
                candidate_lane = predecessor_assignment[0]
                if candidate_lane.group_id != group_id or any(
                    existing.root.item_id != predecessor_bundle.root.item_id
                    and any(_overlaps(existing_item.planned, new_item.planned)
                            for existing_item in existing.members for new_item in bundle.members)
                    for existing in candidate_lane.bundles
                ):
                    continue
                candidates.append((relation.relation_id, predecessor.object_id, predecessor.item_id, candidate_lane))
            if candidates:
                source_id, _, _, lane = min(candidates, key=lambda candidate: candidate[:3])
                rule = "chain"

        if lane is None and "dates" in value.packing:
            candidates = [candidate for candidate in lanes.values() if candidate.group_id == group_id]
            candidates.sort(key=lambda candidate: (candidate.explicit_key is None,
                                                    candidate.explicit_key or candidate.bundles[0].root.item_id))
            for candidate in candidates:
                if all(not _overlaps(existing_item.planned, new_item.planned)
                       for existing in candidate.bundles for existing_item in existing.members
                       for new_item in bundle.members):
                    lane = candidate
                    rule = "dates"
                    source_id = f"first-compatible:{candidate.lane_id}"
                    break

        if lane is None:
            lane = _MutableLane(_lane_id(group_id, founder=bundle.root.item_id), group_id, None, [])
            lanes[group_id, lane.lane_id] = lane
        lane.bundles.append(bundle)
        assignments[bundle.root.item_id] = (lane, rule, source_id)
        placed.add(bundle.root.item_id)

    # A child is an independently countable member, with explicit evidence of
    # the attachment fact that pins it to the host's assignment.
    for bundle in bundles:
        lane, rule, source_id = assignments[bundle.root.item_id]
        for member in bundle.members:
            if member.item_id == bundle.root.item_id:
                continue
            assignments[member.item_id] = (lane, "attached", bundle.root.item_id)

    lane_values: list[Lane] = []
    assignment_values: list[LaneAssignment] = []
    for lane in lanes.values():
        members = tuple(item.item_id for bundle in sorted(lane.bundles, key=lambda entry: _item_order(entry.root))
                        for item in bundle.members)
        lane_values.append(Lane(lane.lane_id, lane.group_id, members, lane.explicit_key))
        for bundle in lane.bundles:
            for member in bundle.members:
                _, rule, source_id = assignments[member.item_id]
                assignment_values.append(LaneAssignment(member.item_id, lane.lane_id, lane.group_id, rule, source_id))
    group_order = {group_id: index for index, group_id in enumerate(dict.fromkeys(item.group_id for item in value.items))}
    lane_values.sort(key=lambda lane: (group_order[lane.group_id], lane.explicit_key is None,
                                       lane.explicit_key if lane.explicit_key is not None else
                                       next(bundle.root.item_id for bundle in lanes[lane.group_id, lane.lane_id].bundles)))
    assignment_values.sort(key=lambda assignment: (assignment.group_id,
                                                   _item_order(next(item for item in value.items if item.item_id == assignment.item_id))))
    return LaneMembership(tuple(lane_values), tuple(assignment_values))
