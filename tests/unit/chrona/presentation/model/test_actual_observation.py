from datetime import date

from chrona.presentation.model.actual_observation import InProgressActual, finish_variance, in_progress_actual


def test_open_actual_is_selected_independently_of_progress_and_not_completed_in_source():
    start, cutoff = date(2026, 10, 8), date(2026, 10, 16)
    for progress in (0.0, 0.6, 1.0, None):
        actual = {"start": start, "progress": progress}
        source = in_progress_actual(actual, cutoff)
        assert source is not None and source.drawable
        assert (source.start, source.as_of) == (start, cutoff)
        assert "finish" not in actual


def test_open_actual_retains_missing_cutoff_and_zero_length_as_explicit_states():
    start = date(2026, 10, 8)
    assert in_progress_actual({"start": start}, None) == InProgressActual(start, None)
    zero = in_progress_actual({"start": start}, start)
    assert zero is not None and not zero.drawable
    assert in_progress_actual({"progress": 0.6}, date(2026, 10, 16)) is None


def test_finish_variance_uses_as_of_only_after_planned_end_without_synthesizing_finish():
    planned_end = date(2026, 10, 12)
    actual = {"start": date(2026, 10, 8), "progress": 0.6}
    assert finish_variance({"end": planned_end}, actual, date(2026, 10, 11)) is None
    assert finish_variance({"end": planned_end}, actual, date(2026, 10, 16)) == 4
    assert "finish" not in actual
    assert finish_variance({"end": planned_end}, {"start": date(2026, 10, 8),
                                                     "finish": date(2026, 10, 10)}, None) == -2

