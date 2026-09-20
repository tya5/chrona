from datetime import date

import pytest

from chrona.presentation.layout.lanes import LaneItem, assign_stable_lanes


def item(name, start, end, group="team", **kwargs):
    return LaneItem(name, group, date(2027, 1, start), date(2027, 1, end), **kwargs)


def test_lanes_are_stable_lowest_nonoverlap_and_group_preserving():
    assigned = assign_stable_lanes([item("b", 1, 5), item("a", 1, 5), item("c", 5, 7), item("other", 1, 5, "other")], max_stack=2)
    assert [(entry.object_id, entry.group_id, entry.stack) for entry in assigned] == [("other", "other", 0), ("a", "team", 0), ("b", "team", 1), ("c", "team", 0)]


def test_required_label_bounds_participate_and_overflow_diagnoses():
    first = item("a", 1, 3, required_label=True, label_end=date(2027, 1, 5))
    second = item("b", 4, 6)
    assert [entry.stack for entry in assign_stable_lanes([first, second], max_stack=2)] == [0, 1]
    with pytest.raises(ValueError, match="E_PRESENTATION_STACK_OVERFLOW"):
        assign_stable_lanes([first, second], max_stack=1)
