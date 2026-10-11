"""Synthetic contracts for first-anchored regular axis-label thinning."""

import pytest

from chrona.presentation.layout.axis import AxisThinningSchedule, thinning_schedule


@pytest.mark.parametrize(
    ("fits", "retained"),
    [
        ((True, False, True, False, True, False), (0, 2, 4)),
        ((True, False, False, True, False, False), (0, 3)),
        ((True, False, False, False, True), (0, 4)),
        ((True, False, True, True, True), (0, 2, 4)),
        ((True, True, False, True, True), (0, 3)),
        ((True, True, False, False, True), (0, 4)),
    ],
)
def test_smallest_regular_stride_keeps_only_fitting_candidates_at_phase_zero(fits, retained):
    schedule = thinning_schedule(fits)

    assert schedule == AxisThinningSchedule(
        retained_positions=retained,
        thinned_positions=tuple(index for index in range(len(fits)) if index not in retained),
    )


def test_stride_selects_candidates_without_widening_their_own_intervals():
    # Candidate 2 and 4 fit their own intervals; stride two retains those
    # candidates while the intervening non-fitting candidates remain omitted.
    fits = (True, False, True, False, True)

    schedule = thinning_schedule(fits)

    assert schedule.retained_positions == (0, 2, 4)
    assert all(fits[index] for index in schedule.retained_positions)
    assert schedule.thinned_positions == (1, 3)


def test_first_candidate_false_means_no_phase_zero_regular_subset_fits():
    fits = (False, True, True, True)

    assert thinning_schedule(fits) == AxisThinningSchedule((), (0, 1, 2, 3))


@pytest.mark.parametrize("fits", [(), (False,), (False, False, False)])
def test_empty_or_no_fit_candidates_produce_an_honest_empty_schedule(fits):
    assert thinning_schedule(fits) == AxisThinningSchedule((), tuple(range(len(fits))))


def test_all_fitting_candidates_use_stride_one():
    fits = (True, True, True, True)

    assert thinning_schedule(fits) == AxisThinningSchedule((0, 1, 2, 3), ())


def test_regular_schedule_is_deterministic_for_repeated_calls():
    fits = (True, False, True, False, True, False)

    assert thinning_schedule(fits) == thinning_schedule(fits)
