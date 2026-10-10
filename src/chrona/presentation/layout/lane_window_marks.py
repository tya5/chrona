"""Account for every original lane mark using cached window admission."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from chrona.presentation.layout.lane_projection import (
    ExpectedLaneMark, LaneProjectionClosure, LaneProjectionInstance, close_lane_projection,
)
from chrona.presentation.layout.mark_facet_visibility import FacetDisposition
from chrona.presentation.layout.model import LayoutError
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


def _invalid(reason: str) -> None:
    raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/laneRows",
                      detail=f"stage=expected-mark-account; reason={reason}")


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
