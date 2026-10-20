import pytest

from chrona.core.completion import actual_occurrence_completed, rollup_completed


@pytest.mark.parametrize(("kind", "actual", "expected"), [
    ("span", {"start": "2026-01-01"}, False),
    ("span", {"start": "2026-01-01", "progress": 1}, False),
    ("span", {"finish": "2026-01-03"}, True),
    ("point", {"at": "2026-01-03"}, True),
    ("point", {"progress": 1}, False),
    ("span", None, False),
])
def test_actual_completion_uses_observed_temporal_endpoint(kind, actual, expected):
    assert actual_occurrence_completed(kind, actual) is expected


def test_rollup_completion_requires_every_temporal_child():
    assert rollup_completed((True, True))
    assert not rollup_completed((True, False))
    # Match the existing forecast all-children rule for an empty rollup.
    assert rollup_completed(())


def test_unknown_actual_occurrence_kind_is_not_guessed():
    with pytest.raises(ValueError, match="unknown temporal occurrence kind"):
        actual_occurrence_completed("milestone", {"at": "2026-01-03"})
