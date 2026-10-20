"""Account for every original lane mark using cached window admission."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_quality import MarkPlacement
    from chrona.presentation.layout.window_row_admission import WindowRowOmissionProof

from chrona.presentation.layout.lane_projection import (
    ExpectedLaneMark, LaneProjectionClosure, LaneProjectionInstance, close_lane_projection,
    lane_instance_owners,
)
from chrona.presentation.layout.mark_facet_visibility import FacetDisposition
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.semantic_mark_facets import mark_placement_facet
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, MarkOccurrence, MarkOccurrenceKind,
)
from chrona.presentation.model.projection import ReviewProjection


@dataclass(frozen=True)
class LaneWindowAbsence:
    """An original expected mark omitted by the explicit window, not deleted."""

    expected: ExpectedLaneMark
    source_ref: str
    reason: str = "outside-window"


@dataclass(frozen=True)
class LaneWindowMarkAccount:
    """The original source inventory and its exhaustive emission partition."""

    source: LaneProjectionClosure
    admitted: tuple[ExpectedLaneMark, ...]
    absences: tuple[LaneWindowAbsence, ...]

    @property
    def wholly_omitted_instances(self) -> frozenset[LaneProjectionInstance]:
        """Only original nonempty mark inventories with no admitted mark."""
        original = {mark.instance for mark in self.source.expected_marks}
        visible = {mark.instance for mark in self.admitted}
        return frozenset(original - visible)


@dataclass(frozen=True)
class LaneWindowPlacementAbsence:
    """Original omitted mark joined to its final countable member, without geometry."""

    row_id: str
    member_id: str
    expected: ExpectedLaneMark
    source_ref: str
    reason: str = "outside-window"
    row_omission_proof: WindowRowOmissionProof | None = None

    def __post_init__(self) -> None:
        if (not all(isinstance(value, str) and value for value in
                    (self.row_id, self.member_id, self.source_ref))
                or not isinstance(self.expected, ExpectedLaneMark)
                or self.reason != "outside-window"):
            _invalid("invalid-placement-absence")
        if self.row_omission_proof is not None:
            from chrona.presentation.layout.window_row_admission import WindowRowOmissionProof
            proof = self.row_omission_proof
            instance = self.expected.instance
            if (not isinstance(proof, WindowRowOmissionProof)
                    or proof.row_id != self.row_id
                    or proof.occurrence.kind != MarkOccurrenceKind.LANE_SOURCE
                    or (proof.occurrence.item_id, proof.occurrence.object_id,
                        proof.occurrence.source_kind)
                       != (instance.item_id, instance.object_id, instance.source_kind)
                    or proof.source_ref != self.source_ref):
                _invalid("invalid-row-omission-proof")
            proof.validate()


@dataclass(frozen=True)
class LaneWindowRowAbsence:
    """An original lane member whose complete row was omitted by Layout."""

    row_id: str
    member_id: str
    reason: str
    proof: WindowRowOmissionProof
    admission: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        from chrona.presentation.layout.window_row_admission import (
            WindowRowAdmission, WindowRowOmissionProof,
        )
        if (not isinstance(self.row_id, str) or not self.row_id
                or not isinstance(self.member_id, str) or not self.member_id
                or not isinstance(self.proof, WindowRowOmissionProof)
                or not isinstance(self.admission, WindowRowAdmission)
                or self.proof.row_id != self.row_id
                or self.proof.occurrence.kind != MarkOccurrenceKind.LANE_SOURCE
                or self.proof.occurrence.item_id != self.member_id
                or self.reason not in {"outside-window", "no-selected-temporal-facet"}):
            _invalid("invalid-row-absence")
        self.admission.require_match(self.proof.projection, self.proof.visibility_index)
        if (self.admission.omitted_row_reasons.get(self.row_id) != self.reason
                or self.admission.omission_for(self.proof.occurrence) != self.proof):
            _invalid("row-absence-cache-mismatch")
        self.proof.validate()


def complete_lane_window_placement_absences(
    account: LaneWindowMarkAccount, *, projection: ReviewProjection,
    as_of: date | None, visibility_index: ItemMarkVisibilityIndex,
    row_admission: object | None = None,
) -> tuple[LaneWindowPlacementAbsence, ...]:
    """Validate the cache partition, then join occurrence and member identities."""
    validate_lane_window_mark_account(account, projection=projection, as_of=as_of,
                                     visibility_index=visibility_index)
    if row_admission is None and getattr(projection, "window_outside", "keep") == "omit":
        from chrona.presentation.layout.window_row_admission import complete_window_row_admission
        row_admission = complete_window_row_admission(projection, visibility_index)
    if row_admission is not None:
        from chrona.presentation.layout.window_row_admission import WindowRowAdmission
        if not isinstance(row_admission, WindowRowAdmission):
            _invalid("invalid-row-admission")
        row_admission.require_match(projection, visibility_index)
    owners = lane_instance_owners(projection, account.source)
    rows = {row.lane_id: row for row in projection.lane_rows}
    completed = []
    for absence in account.absences:
        instance = absence.expected.instance
        lane_id, occurrence_id = owners[instance]
        row = rows[lane_id]
        members = [member_id for item, member_id in zip(row.items, row.member_item_ids, strict=True)
                   if (item.item_id or item.object_id, item.object_id, item.source_kind)
                   == (instance.item_id, instance.object_id, instance.source_kind)]
        source = visibility_index.lookup(
            MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
                           instance.object_id, instance.source_kind),
            projection=projection, as_of=as_of)
        try:
            final = visibility_index.lookup(
                MarkOccurrence(MarkOccurrenceKind.LANE_FINAL, lane_id, occurrence_id,
                               instance.object_id, instance.source_kind),
                projection=projection, as_of=as_of)
        except KeyError:
            _invalid("missing-final-occurrence")
        if len(members) != 1 or source is not final:
            _invalid("placement-owner-mismatch")
        row_proof = None
        if row_admission is not None and lane_id not in row_admission.admitted_lane_ids:
            occurrence = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, instance.row_id,
                                        instance.item_id, instance.object_id,
                                        instance.source_kind)
            row_proof = row_admission.omission_for(occurrence)
            if row_proof is None:
                _invalid("missing-row-omission-proof")
        completed.append(LaneWindowPlacementAbsence(
            lane_id, members[0], absence.expected, absence.source_ref, absence.reason,
            row_proof))
    return tuple(completed)


def _invalid(reason: str) -> None:
    raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/laneRows",
                      detail=f"stage=expected-mark-account; reason={reason}")


def complete_lane_window_handoff(
    marks: tuple[MarkPlacement, ...], *, projection: ReviewProjection, as_of: date | None,
    visibility_index: ItemMarkVisibilityIndex, row_admission: object | None = None,
) -> tuple[tuple[LaneWindowPlacementAbsence, ...], frozenset[str], tuple[LaneWindowRowAbsence, ...]]:
    """Close original expected marks against final placements, without parsing IDs."""
    from chrona.presentation.layout.surface_quality import MarkPlacement
    if not isinstance(marks, tuple) or any(not isinstance(mark, MarkPlacement) for mark in marks):
        _invalid("invalid-final-placement")
    account = complete_lane_window_mark_account(
        projection, as_of=as_of, visibility_index=visibility_index)
    absences = complete_lane_window_placement_absences(
        account, projection=projection, as_of=as_of, visibility_index=visibility_index,
        row_admission=row_admission)
    owners = lane_instance_owners(projection, account.source)
    source_rows = {row.row_id: row for row in projection.rows}
    expected_keys = []
    admitted_rows = set()
    for mark in account.admitted:
        instance = mark.instance
        lane_id, occurrence_id = owners[instance]
        first = source_rows[instance.row_id].items[0]
        member_id = first.item_id or first.object_id
        original = visibility_index.lookup(
            MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
                           instance.object_id, instance.source_kind), projection=projection, as_of=as_of)
        try:
            final = visibility_index.lookup(
                MarkOccurrence(MarkOccurrenceKind.LANE_FINAL, lane_id, occurrence_id,
                               instance.object_id, instance.source_kind), projection=projection, as_of=as_of)
        except KeyError:
            _invalid("missing-final-occurrence")
        if original is not final:
            _invalid("placement-owner-mismatch")
        facet = next(item for item in original.facets if item.source.facet == mark.purpose)
        expected_keys.append((f"{mark_placement_facet(mark.purpose)}:{lane_id}:{occurrence_id}", instance.object_id,
                              lane_id, member_id, instance.source_kind, facet.source.semantic_id))
        admitted_rows.add(lane_id)
    # The surface also owns legend/decorative marks. Validate every typed lane
    # claim (including partial claims), without admitting unrelated surface paint.
    lane_marks = tuple(mark for mark in marks if any(value is not None for value in
                       (mark.lane_row_id, mark.lane_member_id, mark.lane_source_kind)))
    actual = [(mark.placement_id, mark.source_ref, mark.lane_row_id, mark.lane_member_id,
               mark.lane_source_kind, mark.semantic_id) for mark in lane_marks]
    if len(actual) != len(expected_keys) or set(actual) != set(expected_keys):
        _invalid("final-emission-mismatch")
    original_rows = {owners[mark.instance][0] for mark in account.source.expected_marks}
    omitted_rows = frozenset(original_rows - admitted_rows)
    row_absences: list[LaneWindowRowAbsence] = []
    if row_admission is not None and row_admission.omit_outside:
        lane_rows = {row.lane_id: row for row in projection.lane_rows}
        source_rows = {row.row_id: row for row in projection.rows}
        for instance in account.source.instances:
            lane_id, _occurrence_id = owners[instance]
            if lane_id not in row_admission.omitted_row_reasons:
                continue
            lane_row = lane_rows.get(lane_id)
            source_row = source_rows.get(instance.row_id)
            if lane_row is None or source_row is None:
                _invalid("missing-row-absence-owner")
            member_matches = [member_id for item, member_id in
                              zip(lane_row.items, lane_row.member_item_ids, strict=True)
                              if (item.item_id or item.object_id, item.object_id, item.source_kind)
                              == (instance.item_id, instance.object_id, instance.source_kind)]
            if len(member_matches) != 1:
                _invalid("row-absence-member-mismatch")
            occurrence = MarkOccurrence(
                MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
                instance.object_id, instance.source_kind)
            proof = row_admission.omission_for(occurrence)
            if proof is None:
                _invalid("missing-row-absence-proof")
            reason = row_admission.omitted_row_reasons.get(lane_id)
            if reason not in {"outside-window", "no-selected-temporal-facet"}:
                _invalid("missing-row-absence-reason")
            row_absences.append(LaneWindowRowAbsence(
                lane_id, member_matches[0], reason, proof, row_admission))
    return absences, omitted_rows, tuple(row_absences)


def complete_lane_window_mark_account(
    projection: ReviewProjection, *, as_of: date | None,
    visibility_index: ItemMarkVisibilityIndex,
) -> LaneWindowMarkAccount:
    """Read existing visibility without selecting dates or changing membership."""
    visibility_index.require_match(projection, as_of)
    source = close_lane_projection(projection, as_of=as_of)
    admitted: list[ExpectedLaneMark] = []
    absences: list[LaneWindowAbsence] = []
    by_instance: dict[LaneProjectionInstance, list[ExpectedLaneMark]] = {}
    for mark in source.expected_marks:
        by_instance.setdefault(mark.instance, []).append(mark)
    for instance in source.instances:
        try:
            visibility = visibility_index.lookup(
                MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, instance.row_id,
                               instance.item_id, instance.object_id, instance.source_kind),
                projection=projection, as_of=as_of,
            )
        except KeyError:
            _invalid("missing-source-occurrence")
        expected = by_instance.get(instance, ())
        facets = {facet.source.facet: facet for facet in visibility.facets}
        # A missing, duplicated, or extra source facet is not a window absence.
        if (len(facets) != len(visibility.facets)
                or set(facets) != {mark.purpose for mark in expected}
                or len(expected) != len(facets)
                or tuple(facet.source for facet in visibility.facets) != visibility.selection.facets
                or visibility.instance_id != instance.placement_key
                or visibility.selection.source_kind != instance.source_kind):
            _invalid("source-inventory-mismatch")
        for mark in expected:
            if facets[mark.purpose].disposition == FacetDisposition.OMITTED:
                absences.append(LaneWindowAbsence(mark, visibility.source_ref))
            else:
                admitted.append(mark)
    return LaneWindowMarkAccount(source, tuple(admitted), tuple(absences))


def validate_lane_window_mark_account(
    account: LaneWindowMarkAccount, *, projection: ReviewProjection,
    as_of: date | None, visibility_index: ItemMarkVisibilityIndex,
) -> None:
    """Reject forged/deleted/duplicate absence claims against the source cache."""
    canonical = complete_lane_window_mark_account(
        projection, as_of=as_of, visibility_index=visibility_index)
    if not isinstance(account, LaneWindowMarkAccount) or account != canonical:
        _invalid("account-mismatch")


def validate_lane_window_emission(
    account: LaneWindowMarkAccount, emitted: tuple[ExpectedLaneMark, ...],
    *, projection: ReviewProjection, as_of: date | None,
    visibility_index: ItemMarkVisibilityIndex,
) -> None:
    """An admitted mark must be emitted exactly once; an omitted one never is."""
    validate_lane_window_mark_account(
        account, projection=projection, as_of=as_of, visibility_index=visibility_index)
    if (not isinstance(emitted, tuple)
            or any(not isinstance(mark, ExpectedLaneMark) for mark in emitted)
            or len(emitted) != len(account.admitted)
            or set(emitted) != set(account.admitted)):
        _invalid("emission-mismatch")
