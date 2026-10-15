"""Projection-owned figure count facts are gathered from selected ReviewItems (#927)."""
from dataclasses import FrozenInstanceError, replace
from datetime import date

import pytest

from chrona.core.figures import COUNT_SOURCES
from chrona.presentation.model.projection import ObservationState, ReviewItem
from chrona.presentation.review.figure_facts import projected_counts, projected_last_planned_finish


def _item(item_id, *, source_kind="primary", state=ObservationState.UNAVAILABLE, delta=None):
    return ReviewItem(
        object_id=item_id,
        title=item_id,
        source_type="span",
        planned={},
        actual=None,
        finish_delta=delta,
        roles=(),
        item_id=item_id,
        source_kind=source_kind,
        observation_state=state,
    )


@pytest.fixture
def primary_and_non_primary_items():
    return [
        _item("recorded-late", state=ObservationState.RECORDED, delta=4),
        _item("recorded-ahead", state=ObservationState.RECORDED, delta=-2),
        _item("recorded-on-time", state=ObservationState.RECORDED, delta=0),
        _item("due", state=ObservationState.DUE_UNOBSERVED),
        _item("not-yet-due", state=ObservationState.NOT_YET_DUE),
        _item("unavailable", state=ObservationState.UNAVAILABLE),
        # Comparison and actual rows must not leak into selected-Project counts.
        _item("snapshot-ghost", source_kind="snapshot", state=ObservationState.RECORDED, delta=9),
        _item("scenario-ghost", source_kind="scenario", state=ObservationState.DUE_UNOBSERVED, delta=8),
        _item("actual-observation", source_kind="actual", state=ObservationState.RECORDED, delta=-7),
    ]


def test_projected_counts_cover_each_closed_count_source_and_signed_delta_state(primary_and_non_primary_items):
    counts = projected_counts(primary_and_non_primary_items, as_of_available=True)

    assert tuple(counts.value(source) for source in COUNT_SOURCES) == (
        6,  # selected Primary items only
        3,  # recorded
        1,  # dueUnobserved
        1,  # notYetDue
        1,  # unavailable
        1,  # missingActual: due-unobserved items when an as-of is available
        3,  # knownFinishVariance includes positive, negative and zero deltas
        1,  # behind: positive finish deltas
        1,  # ahead: negative finish deltas
        0,  # no nonempty selected group identities
        None,  # placed narrative is unavailable before Layout, not zero
    )
    assert counts.selected == 6
    assert counts.behind == 1
    assert counts.ahead == 1


def test_missing_actual_is_unavailable_without_as_of_but_due_state_count_remains(primary_and_non_primary_items):
    counts = projected_counts(primary_and_non_primary_items, as_of_available=False)

    assert counts.due_unobserved == 1
    assert counts.missing_actual is None


def test_zero_primary_selection_yields_zero_counts(primary_and_non_primary_items):
    ghosts_only = [item for item in primary_and_non_primary_items if item.source_kind != "primary"]
    counts = projected_counts(ghosts_only, as_of_available=True)

    assert tuple(counts.value(source) for source in COUNT_SOURCES) == (0,) * (len(COUNT_SOURCES) - 1) + (None,)


def test_selected_identities_and_groups_are_distinct_while_ghosts_do_not_count():
    first = replace(_item("first"), group_id="a")
    combined = replace(_item("second", source_kind="combined"), group_id="b")
    third = _item("third")
    ghost = replace(_item("ghost", source_kind="snapshot"), group_id="ghost")
    counts = projected_counts((first, first, combined, combined, third, ghost), as_of_available=False)
    assert counts.selected == 3 and counts.groups == 2
    assert counts.placed_notes is None


def test_count_bundle_is_frozen_and_does_not_retain_or_follow_input_sequence(primary_and_non_primary_items):
    counts = projected_counts(primary_and_non_primary_items, as_of_available=True)
    primary_and_non_primary_items.clear()

    assert counts.selected == 6
    with pytest.raises(FrozenInstanceError):
        counts.selected = 99


def test_projected_last_finish_uses_span_end_and_point_at_and_ignores_nonprimary_rows():
    span = replace(_item("span"), planned={"start": date(2026, 1, 1), "end": date(2026, 2, 1)})
    point = replace(_item("point"), source_type="point", planned={"at": date(2026, 3, 1)})
    ghost = replace(_item("ghost", source_kind="snapshot"), planned={"end": date(2030, 1, 1)})
    scenario = replace(_item("scenario", source_kind="scenario"), planned={"end": date(2031, 1, 1)})
    actual = replace(_item("actual", source_kind="actual"), planned={"end": date(2032, 1, 1)})
    assert projected_last_planned_finish((span, point, ghost, scenario, actual)) == date(2026, 3, 1)


def test_projected_last_finish_deduplicates_identity_and_keeps_first_selected_occurrence():
    earlier = replace(_item("same"), planned={"end": date(2026, 2, 1)})
    duplicate_later = replace(earlier, planned={"end": date(2027, 2, 1)})
    combined = replace(_item("combined", source_kind="combined"), planned={"end": date(2026, 4, 1)})
    assert projected_last_planned_finish((earlier, duplicate_later, combined)) == date(2026, 4, 1)


def test_projected_last_finish_is_unavailable_without_a_selected_finish():
    point_without_date = replace(_item("point"), source_type="point", planned={})
    ghost = replace(_item("ghost", source_kind="snapshot"), planned={"end": date(2030, 1, 1)})
    assert projected_last_planned_finish((point_without_date, ghost)) is None
