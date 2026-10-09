"""Close Review projection identity and expected mark emission for lanes.

This module is deliberately geometry-free. Layout derives mark roles from
selected Review facts and pins every role to an explicit projection instance
before geometry is composed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import quote

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import ObservationState, ReviewProjection


@dataclass(frozen=True, order=True)
class LaneProjectionInstance:
    """Typed identity of one selected Review item in one row."""

    row_id: str
    item_id: str
    object_id: str
    source_kind: str

    @property
    def placement_key(self) -> str:
        """Collision-free lane-only encoding of the typed instance key."""
        return f"{quote(self.row_id, safe='-._~')}:{quote(self.item_id, safe='-._~')}"


@dataclass(frozen=True)
class ExpectedLaneMark:
    """One required Layout mark, retaining its typed source instance."""

    instance: LaneProjectionInstance
    role: str
    purpose: str
    placement_id: str


@dataclass(frozen=True)
class LaneIntentionalAbsence:
    """One selected semantic role intentionally has no emitted primitive."""

    instance: LaneProjectionInstance
    role: str
    reason: str


@dataclass(frozen=True)
class LaneProjectionClosure:
    """Immutable selected item, attachment, and expected-emission closure."""

    instances: tuple[LaneProjectionInstance, ...]
    expected_marks: tuple[ExpectedLaneMark, ...]
    intentional_absences: tuple[LaneIntentionalAbsence, ...]
    attached_hosts: tuple[tuple[LaneProjectionInstance, LaneProjectionInstance], ...]


def lane_missing_actual_visible(projection: ReviewProjection) -> bool:
    """Apply the View facet selection before lane geometry is composed."""
    facets = projection.comparison_facets
    return not facets or "missingActual" in facets


def close_lane_projection(
    projection: ReviewProjection,
    *,
    as_of: date | None,
) -> LaneProjectionClosure:
    """Derive the exact mark inventory from selected Review semantics.

    The caller cannot declare away an expected role. In particular, open
    Actual uses the selected cutoff and malformed/incomplete Actual payloads
    are retained as typed intentional absences for later diagnostics.
    """
    if projection.surface != "table-timeline" or not projection.rows or projection.folded_points:
        raise LayoutError("E_LAYOUT_LANE_PROJECTION_UNSUPPORTED", "/projection/rows")
    if as_of is not None and type(as_of) is not date:
        raise LayoutError("E_LAYOUT_LANE_AS_OF_INVALID", "/presentationContract/time/as_of")

    instances: list[LaneProjectionInstance] = []
    row_instances: dict[str, list[LaneProjectionInstance]] = {}
    source_by_instance: dict[LaneProjectionInstance, object] = {}
    seen_row_ids: set[str] = set()
    for row in projection.rows:
        if not row.row_id or row.row_id in seen_row_ids:
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/rows")
        seen_row_ids.add(row.row_id)
        for item in row.items:
            item_id = item.item_id or item.object_id
            if not item_id or not item.object_id:
                raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/rows/{row.row_id}/items")
            key = (row.row_id, item_id)
            if any((candidate.row_id, candidate.item_id) == key for candidate in instances):
                raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/rows/{row.row_id}/items/{item_id}")
            instance = LaneProjectionInstance(row.row_id, item_id, item.object_id, item.source_kind)
            instances.append(instance)
            row_instances.setdefault(row.row_id, []).append(instance)
            source_by_instance[instance] = item

    expected_marks: list[ExpectedLaneMark] = []
    intentional_absences: list[LaneIntentionalAbsence] = []
    missing_actual_visible = lane_missing_actual_visible(projection)
    for instance in instances:
        item = source_by_instance[instance]
        path = f"/projection/rows/{instance.row_id}/items/{instance.item_id}"
        actual = item.actual or {}
        if instance.source_kind not in {"primary", "actual", "combined", "snapshot", "scenario"}:
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"{path}/source_kind")
        if actual.get("openUntil") == "asOf" and as_of is None:
            raise LayoutError("E_LAYOUT_LANE_AS_OF_REQUIRED", f"{path}/actual/openUntil")
        if actual and item.observation_state != ObservationState.RECORDED:
            raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_INVALID", path,
                              detail="Actual payload conflicts with observation_state")
        roles = set(item.roles)
        expected_observation_role = (
            "actual" if item.observation_state == ObservationState.RECORDED else
            "missing-actual" if item.observation_state == ObservationState.DUE_UNOBSERVED else None)
        status_roles = roles & {"actual", "missing-actual"}
        expected_status_roles = {expected_observation_role} if expected_observation_role else set()
        if "planned" not in roles or status_roles != expected_status_roles:
            raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_INVALID", path)
        planned_role = {"snapshot": "snapshot", "scenario": "scenario"}.get(
            instance.source_kind, "planned")
        if item.source_type not in {"point", "span"}:
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"{path}/source_type")
        planned_complete = (isinstance(item.planned.get("at"), date)
                            if item.source_type == "point" else
                            isinstance(item.planned.get("start"), date)
                            and isinstance(item.planned.get("end"), date))
        if not planned_complete:
            raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_INVALID", f"{path}/planned")
        if instance.source_kind == "actual":
            if item.observation_state != ObservationState.RECORDED or not actual:
                raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_INVALID", path,
                                  detail="selected Actual source has no recorded payload")
            intentional_absences.append(LaneIntentionalAbsence(instance, "planned", "actual-source-only"))
        else:
            _expect_mark(expected_marks, instance, planned_role, "planned")

        if instance.source_kind not in {"actual", "combined", "primary"}:
            continue
        if instance.source_kind == "primary":
            if item.observation_state == ObservationState.DUE_UNOBSERVED and not actual:
                anchor = item.planned.get("end" if item.source_type == "span" else "at")
                if not isinstance(anchor, date):
                    raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_INVALID", f"{path}/planned")
                if missing_actual_visible:
                    _expect_mark(expected_marks, instance, "missing-actual", "missing-actual")
                else:
                    intentional_absences.append(LaneIntentionalAbsence(
                        instance, "missing-actual", "view-facet-omitted"))
            else:
                if item.observation_state == ObservationState.RECORDED:
                    intentional_absences.append(LaneIntentionalAbsence(
                        instance, "actual", "actual-owned-by-selected-source"))
                if item.observation_state == ObservationState.DUE_UNOBSERVED and actual:
                    intentional_absences.append(LaneIntentionalAbsence(
                        instance, "missing-actual", "incomplete-actual-payload"))
            continue

        if (missing_actual_visible and getattr(item, "missing_actual_mark", "due-end") == "in-progress"
                and item.source_type == "span" and isinstance(actual.get("start"), date)):
            # `comparison.missingActualScope: in-progress` (#1027): the View marked this span as in progress, so
            # Layout draws the missing-actual span from its actual start to the cutoff in place of the open actual.
            if as_of is None:
                raise LayoutError("E_LAYOUT_LANE_AS_OF_REQUIRED", f"{path}/actual/start")
            if as_of <= actual["start"]:
                intentional_absences.append(LaneIntentionalAbsence(
                    instance, "missing-actual", "in-progress-empty-at-cutoff"))
            else:
                _expect_mark(expected_marks, instance, "missing-actual", "missing-actual")
        elif _has_complete_actual(item.source_type, actual):
            if actual.get("openUntil") == "asOf":
                start = actual.get("start")
                if as_of is None:
                    raise LayoutError("E_LAYOUT_LANE_AS_OF_REQUIRED", f"{path}/actual/openUntil")
                if not isinstance(start, date):
                    intentional_absences.append(LaneIntentionalAbsence(
                        instance, "actual", "incomplete-open-actual"))
                elif as_of <= start:
                    intentional_absences.append(LaneIntentionalAbsence(
                        instance, "actual", "open-actual-empty-at-cutoff"))
                else:
                    _expect_mark(expected_marks, instance, "actual", "actual")
            else:
                _expect_mark(expected_marks, instance, "actual", "actual")
        elif actual:
            intentional_absences.append(LaneIntentionalAbsence(
                instance, "actual", "incomplete-actual-payload"))
        elif item.observation_state == ObservationState.DUE_UNOBSERVED:
            anchor = item.planned.get("end" if item.source_type == "span" else "at")
            if not isinstance(anchor, date):
                raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_INVALID", f"{path}/planned")
            if missing_actual_visible:
                _expect_mark(expected_marks, instance, "missing-actual", "missing-actual")
            else:
                intentional_absences.append(LaneIntentionalAbsence(
                    instance, "missing-actual", "view-facet-omitted"))
        elif item.observation_state == ObservationState.RECORDED:
            intentional_absences.append(LaneIntentionalAbsence(
                instance, "actual", "incomplete-actual-payload"))

    attached_hosts: list[tuple[LaneProjectionInstance, LaneProjectionInstance]] = []
    for child in instances:
        item = source_by_instance[child]
        host_object_id = getattr(item, "attached_to", None)
        if host_object_id is None:
            continue
        matches = tuple(candidate for candidate in row_instances[child.row_id]
                        if candidate.object_id == host_object_id and candidate != child
                        and getattr(source_by_instance[candidate], "attached_to", None) is None)
        row = next(row for row in projection.rows if row.row_id == child.row_id)
        preferred = tuple(candidate for candidate in matches
                          if candidate.item_id == row.table_subject_id)
        if len(preferred) == 1:
            matches = preferred
        elif len(matches) > 1:
            primary = tuple(candidate for candidate in matches
                            if candidate.source_kind in {"primary", "combined"})
            if len(primary) == 1:
                matches = primary
        if len(matches) != 1:
            raise LayoutError("E_LAYOUT_LANE_ATTACHED_HOST_INVALID",
                              f"/projection/rows/{child.row_id}/items/{child.item_id}/attached_to",
                              detail=f"expected one selected host, found {len(matches)}")
        attached_hosts.append((child, matches[0]))

    return LaneProjectionClosure(tuple(instances), tuple(expected_marks),
                                 tuple(intentional_absences), tuple(attached_hosts))


def _has_complete_actual(source_type: str, actual: dict) -> bool:
    if source_type == "point":
        return isinstance(actual.get("at"), date)
    return (isinstance(actual.get("start"), date)
            and isinstance(actual.get("finish"), date)) or (
                actual.get("openUntil") == "asOf"
                and isinstance(actual.get("start"), date))


def _expect_mark(target: list[ExpectedLaneMark], instance: LaneProjectionInstance,
                 role: str, purpose: str) -> None:
    # This is the completed SurfacePlacement naming convention. The typed
    # instance remains the identity authority; consumers must not parse this
    # serialization back into source identities.
    target.append(ExpectedLaneMark(instance, role, purpose,
                                   f"{purpose}:{instance.placement_key}"))
