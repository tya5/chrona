"""Close Review projection identity and expected mark emission for lanes.

This module is deliberately geometry-free. The View/normalization caller
declares which mark roles are selected for each Review item; Layout verifies
that declaration covers the selected projection exactly and pins every role
to an explicit projection instance before geometry is composed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import ReviewProjection


LANE_MARK_ROLES = frozenset({"planned", "snapshot", "scenario", "actual", "missing-actual"})


@dataclass(frozen=True, order=True)
class LaneProjectionInstance:
    """Typed identity of one selected Review item in one row."""

    row_id: str
    item_id: str
    object_id: str
    source_kind: str

    @property
    def placement_key(self) -> str:
        """Stable Layout placement key for existing completed placement IDs."""
        return f"{self.row_id}:{self.item_id}"


@dataclass(frozen=True)
class ExpectedLaneMark:
    """One required Layout mark, retaining its typed source instance."""

    instance: LaneProjectionInstance
    role: str
    placement_id: str


@dataclass(frozen=True)
class LaneProjectionClosure:
    """Immutable selected item, attachment, and expected-emission closure."""

    instances: tuple[LaneProjectionInstance, ...]
    expected_marks: tuple[ExpectedLaneMark, ...]
    attached_hosts: tuple[tuple[LaneProjectionInstance, LaneProjectionInstance], ...]


def close_lane_projection(
    projection: ReviewProjection,
    selected_roles: Mapping[tuple[str, str], Sequence[str]],
) -> LaneProjectionClosure:
    """Validate normalized role selection and resolve exact attached hosts.

    ``selected_roles`` is keyed by ``(row_id, item_id)`` and must contain one
    entry for every and only selected row item. Roles represent normalized
    semantics after cutoff/scenario/comparison selection; this helper does not
    infer which marks ought to exist from incomplete source dictionaries.
    """
    if projection.surface != "table-timeline" or not projection.rows or projection.folded_points:
        raise LayoutError("E_LAYOUT_LANE_PROJECTION_UNSUPPORTED", "/projection/rows")

    instances: list[LaneProjectionInstance] = []
    row_instances: dict[str, list[LaneProjectionInstance]] = {}
    source_by_instance: dict[LaneProjectionInstance, object] = {}
    selected_keys: list[tuple[str, str]] = []
    for row in projection.rows:
        if not row.row_id:
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/rows")
        for item in row.items:
            item_id = item.item_id or item.object_id
            if not item_id or not item.object_id:
                raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/rows/{row.row_id}/items")
            key = (row.row_id, item_id)
            if key in selected_keys:
                raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/rows/{row.row_id}/items/{item_id}")
            selected_keys.append(key)
            instance = LaneProjectionInstance(row.row_id, item_id, item.object_id, item.source_kind)
            instances.append(instance)
            row_instances.setdefault(row.row_id, []).append(instance)
            source_by_instance[instance] = item

    if len(set(instances)) != len(instances) or set(selected_roles) != set(selected_keys):
        raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_MISMATCH", "/projection/rows")

    expected_marks: list[ExpectedLaneMark] = []
    for instance in instances:
        key = (instance.row_id, instance.item_id)
        roles = tuple(selected_roles[key])
        if (not roles or len(set(roles)) != len(roles)
                or any(role not in LANE_MARK_ROLES for role in roles)):
            raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_INVALID",
                              f"/projection/rows/{instance.row_id}/items/{instance.item_id}")
        for role in roles:
            # This is the completed SurfacePlacement naming convention. The
            # typed ``instance`` remains the identity authority; consumers must
            # not parse this serialization back into source identities.
            expected_marks.append(ExpectedLaneMark(instance, role,
                                                   f"{role}:{instance.placement_key}"))

    attached_hosts: list[tuple[LaneProjectionInstance, LaneProjectionInstance]] = []
    for child in instances:
        item = source_by_instance[child]
        host_object_id = getattr(item, "attached_to", None)
        if host_object_id is None:
            continue
        matches = tuple(candidate for candidate in row_instances[child.row_id]
                        if candidate.object_id == host_object_id and candidate != child
                        and getattr(source_by_instance[candidate], "attached_to", None) is None)
        if len(matches) != 1:
            raise LayoutError("E_LAYOUT_LANE_ATTACHED_HOST_INVALID",
                              f"/projection/rows/{child.row_id}/items/{child.item_id}/attached_to",
                              detail=f"expected one selected host, found {len(matches)}")
        attached_hosts.append((child, matches[0]))

    return LaneProjectionClosure(tuple(instances), tuple(expected_marks), tuple(attached_hosts))
