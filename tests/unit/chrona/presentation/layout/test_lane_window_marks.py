from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.lane_window_marks import (
    complete_lane_window_mark_account, validate_lane_window_emission,
    validate_lane_window_mark_account,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, build_item_mark_visibility_index,
)
from chrona.presentation.model.projection import (
    ObservationState, ReviewItem, ReviewLaneRowProjection, ReviewProjection,
    ReviewRowProjection, WindowMode,
)
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership


def _fixture(*, mode=WindowMode.EXPLICIT, window=(date(2026, 2, 3), date(2026, 2, 5)),
             source_kind="combined"):
    item = ReviewItem(
        "object", "Object", "span",
        {"start": date(2026, 2, 1), "end": date(2026, 2, 2)},
        {"start": date(2026, 2, 3), "finish": date(2026, 2, 6)},
        None, ("planned", "actual"), item_id="item", source_kind=source_kind,
        observation_state=ObservationState.RECORDED,
    )
    row = ReviewRowProjection("source-row", "Row", "group", "item", (item,))
    membership = LaneMembership(
        (Lane("lane", "group", ("item",)),),
        (LaneAssignment("item", "lane", "group", "dates", "fixed"),),
    )
    projection = ReviewProjection(
        (), window, (), (), rows=(row,), lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane", "group", (item,), ("item",)),),
        window_mode=mode,
    )
    index = build_item_mark_visibility_index(projection, as_of=None)
    return projection, index


def _account(projection, index):
    return complete_lane_window_mark_account(projection, as_of=None, visibility_index=index)


def _validate(account, projection, index):
    validate_lane_window_mark_account(account, projection=projection, as_of=None,
                                      visibility_index=index)


def test_partial_omission_retains_original_inventory_and_membership_without_reselection(monkeypatch):
    projection, index = _fixture()
    def forbidden(**kwargs):
        pytest.fail("window account must read the completed source cache")
    monkeypatch.setattr("chrona.presentation.layout.surface_mark_visibility.select_item_mark_facets", forbidden)
    account = _account(projection, index)
    assert tuple(mark.purpose for mark in account.source.expected_marks) == ("planned", "actual")
    assert tuple(mark.purpose for mark in account.admitted) == ("actual",)
    assert account.absences[0].expected is account.source.expected_marks[0]
    assert account.absences[0].source_ref == "/projection/rows/source-row/items/item"
    assert account.absences[0].reason == "outside-window"
    assert projection.lane_membership.lanes[0].member_item_ids == ("item",)
    _validate(account, projection, index)


def test_wholly_outside_member_is_fully_accounted_without_fake_geometry():
    projection, index = _fixture(window=(date(2026, 3, 1), date(2026, 3, 3)))
    account = _account(projection, index)
    assert account.admitted == ()
    assert tuple(absence.expected for absence in account.absences) == account.source.expected_marks
    validate_lane_window_emission(account, (), projection=projection, as_of=None, visibility_index=index)


@pytest.mark.parametrize("mode", (WindowMode.SELECTED_PLANNED, WindowMode.SELECTED_COMPARISON))
def test_derived_windows_never_relax_missing_emission(mode):
    projection, index = _fixture(mode=mode)
    account = _account(projection, index)
    assert account.absences == ()
    assert account.admitted == account.source.expected_marks
    with pytest.raises(LayoutError, match="emission-mismatch"):
        validate_lane_window_emission(account, (), projection=projection, as_of=None, visibility_index=index)


def test_containing_window_has_no_absence_metadata():
    projection, index = _fixture(window=(date(2026, 1, 1), date(2026, 3, 1)))
    account = _account(projection, index)
    assert account.absences == ()
    assert account.admitted == account.source.expected_marks


@pytest.mark.parametrize("forge", (
    lambda a: replace(a, absences=()),
    lambda a: replace(a, absences=a.absences * 2),
    lambda a: replace(a, admitted=a.source.expected_marks),
    lambda a: replace(a, absences=(replace(a.absences[0], reason="view-facet-omitted"),)),
    lambda a: replace(a, absences=(replace(a.absences[0], source_ref="other"),)),
    lambda a: replace(a, source=replace(a.source, expected_marks=a.admitted)),
))
def test_forged_deleted_or_duplicate_absence_is_rejected(forge):
    projection, index = _fixture()
    with pytest.raises(LayoutError, match="account-mismatch"):
        _validate(forge(_account(projection, index)), projection, index)


@pytest.mark.parametrize("emission", ("missing", "duplicate", "omitted"))
def test_missing_duplicate_or_omitted_mark_emission_is_rejected(emission):
    projection, index = _fixture()
    account = _account(projection, index)
    emitted = {"missing": (), "duplicate": account.admitted * 2,
               "omitted": account.source.expected_marks}[emission]
    with pytest.raises(LayoutError, match="emission-mismatch"):
        validate_lane_window_emission(account, emitted, projection=projection, as_of=None,
                                     visibility_index=index)


def test_cache_missing_source_facet_does_not_become_intentional_absence():
    projection, index = _fixture()
    entries = dict(index.entries)
    key = next(key for key in entries if key.kind == "lane-source")
    entries[key] = replace(entries[key], facets=entries[key].facets[1:])
    forged = ItemMarkVisibilityIndex(projection, None, entries)
    with pytest.raises(LayoutError, match="source-inventory-mismatch"):
        _account(projection, forged)


def test_stale_projection_cannot_reuse_omission_account():
    projection, index = _fixture()
    with pytest.raises(LayoutError, match="request-mismatch"):
        _account(replace(projection, window_mode=WindowMode.SELECTED_PLANNED), index)


def test_missing_source_occurrence_has_bounded_layout_error():
    projection, index = _fixture()
    entries = {key: value for key, value in index.entries.items() if key.kind != "lane-source"}
    with pytest.raises(LayoutError, match="missing-source-occurrence"):
        _account(projection, ItemMarkVisibilityIndex(projection, None, entries))


def test_duplicate_cached_facet_is_not_omission_evidence():
    projection, index = _fixture()
    entries = dict(index.entries)
    key = next(key for key in entries if key.kind == "lane-source")
    entries[key] = replace(entries[key], facets=entries[key].facets * 2)
    with pytest.raises(LayoutError, match="source-inventory-mismatch"):
        _account(projection, ItemMarkVisibilityIndex(projection, None, entries))


def test_malformed_emission_has_stable_layout_error():
    projection, index = _fixture()
    with pytest.raises(LayoutError, match="emission-mismatch"):
        validate_lane_window_emission(_account(projection, index), ({},),
                                     projection=projection, as_of=None, visibility_index=index)


@pytest.mark.parametrize("source_kind", ("primary", "actual", "snapshot", "scenario"))
def test_source_kind_is_retained_in_expected_omission_identity(source_kind):
    projection, index = _fixture(source_kind=source_kind)
    account = _account(projection, index)
    assert all(mark.instance.source_kind == source_kind for mark in account.source.expected_marks)
    _validate(account, projection, index)
