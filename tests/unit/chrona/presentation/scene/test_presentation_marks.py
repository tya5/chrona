from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.scene.marks import comparison_marks


def span(actual=None):
    return SimpleNamespace(object_id="task-a", source_type="span", planned={"start": date(2026, 1, 5), "end": date(2026, 1, 12)}, actual=actual)


def test_span_marks_preserve_plan_actual_and_signed_finish_delta():
    marks = comparison_marks([span({"start": date(2026, 1, 6), "finish": date(2026, 1, 15)})], comparison_mode="stacked")
    assert [(mark.facet, mark.start, mark.end, mark.variance_days) for mark in marks] == [
        ("planned", date(2026, 1, 5), date(2026, 1, 12), None),
        ("actual", date(2026, 1, 6), date(2026, 1, 15), None),
        ("finish-delta", None, None, 3),
    ]


def test_missing_actual_endpoint_is_not_substituted_from_plan():
    marks = comparison_marks([span({"finish": date(2026, 1, 15)})], comparison_mode="overlaid")
    assert [mark.facet for mark in marks] == ["planned"]


def test_baseline_mode_and_zero_visibility_are_explicit():
    marks = comparison_marks([span({"start": date(2026, 1, 5), "finish": date(2026, 1, 12)})], comparison_mode="baseline-and-actual", show_zero=False)
    assert [mark.facet for mark in marks] == ["baseline", "actual"]


def test_point_actual_needs_observed_at_value():
    item = SimpleNamespace(object_id="gate", source_type="point", planned={"at": date(2026, 2, 1)}, actual={"finish": date(2026, 2, 2)})
    assert [mark.facet for mark in comparison_marks([item], comparison_mode="stacked")] == ["planned"]


@pytest.mark.parametrize("mode", ["", "sample-specific"])
def test_unknown_comparison_mode_is_rejected(mode):
    with pytest.raises(ValueError, match="E_PRESENTATION_COMPARISON_MODE"):
        comparison_marks([span()], comparison_mode=mode)
