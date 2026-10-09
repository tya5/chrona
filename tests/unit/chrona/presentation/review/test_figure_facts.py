"""Projection-owned figure count facts are gathered from selected ReviewItems (#927)."""
from dataclasses import FrozenInstanceError

import pytest

from chrona.core.figures import COUNT_SOURCES
from chrona.presentation.model.projection import ObservationState, ReviewItem
from chrona.presentation.review.figure_facts import projected_counts


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

    assert tuple(counts.value(source) for source in COUNT_SOURCES) == (0,) * len(COUNT_SOURCES)


def test_count_bundle_is_frozen_and_does_not_retain_or_follow_input_sequence(primary_and_non_primary_items):
    counts = projected_counts(primary_and_non_primary_items, as_of_available=True)
    primary_and_non_primary_items.clear()

    assert counts.selected == 6
    with pytest.raises(FrozenInstanceError):
        counts.selected = 99
