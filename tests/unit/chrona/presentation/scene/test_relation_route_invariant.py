"""A relation route never reverses along its own line (#1059).

Since the side entry (#1030) a source that drops closer to the target's start than the stub length made the router
overshoot to `start - stub` and turn back over the same segment into the arrowhead. Synthetic Projects only, routed by
the real surface composer.
"""
from datetime import date, timedelta

import pytest

from chrona.presentation.model.projection import ReviewItem

from tests.unit.chrona.presentation.scene.test_relation_entry_side import (
    D, DEP, _bends, _horizontal_last, _item, _route, _rows,
)


def reverses(points) -> bool:
    """Whether three consecutive points are collinear with opposite directions."""
    for a, b, c in zip(points, points[1:], points[2:]):
        if a[1] == b[1] == c[1] and (b[0] - a[0]) * (c[0] - b[0]) < 0:
            return True
        if a[0] == b[0] == c[0] and (b[1] - a[1]) * (c[1] - b[1]) < 0:
            return True
    return False


def gate(oid: str, day: date) -> ReviewItem:
    return ReviewItem(oid, oid.upper(), "point", {"at": day}, None, None, (), item_id=oid, source_kind="primary")


def window(days: int) -> tuple[date, date]:
    return date(2026, 1, 20), date(2026, 1, 20) + timedelta(days=days)


def target(gap: int) -> ReviewItem:
    first = date(2026, 2, 8) + timedelta(days=gap)
    return _item("b", first, first + timedelta(days=6))


def route(source, tgt, relation=DEP, *, entry="side-when-free", days=90, max_bends=4):
    return _route((source, tgt), _rows((source,), (tgt,)), relation, entry, window=window(days), distribution="pack",
                  max_bends=max_bends)[0]


@pytest.mark.parametrize(("days", "gap"), [(45, 1), (60, 1), (90, 1), (90, 2), (120, 1), (120, 2)])
def test_a_gate_source_dropping_inside_the_stub_distance_does_not_reverse(days, gap):
    points = route(gate("a", date(2026, 2, 8)), target(gap), days=days)
    assert not reverses(points), points
    assert _horizontal_last(points), "a non-reversing route with a horizontal entry exists and is preferred"


@pytest.mark.parametrize(("days", "gap"), [(90, 1), (120, 2), (200, 1)])
def test_a_bar_source_does_not_reverse_either(days, gap):
    points = route(_item("a", D(2026, 2, 1), D(2026, 2, 8)), target(gap), days=days)
    assert not reverses(points), points


def test_the_mirrored_end_entry_does_not_reverse():
    relation = {"id": "ff", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "end"}}
    for days in (60, 90, 120, 200):
        for gap in (1, 2):
            late = gate("a", date(2026, 2, 20) + timedelta(days=gap))
            early = _item("b", D(2026, 2, 14), D(2026, 2, 20))
            points = route(late, early, relation, days=days)
            assert not reverses(points), (days, gap, points)


def test_the_repair_is_an_honest_extra_bend_bounded_by_max_bends():
    # 120 days, gap 1: the drop lies inside the stub; the repaired route jogs before dropping.
    free = route(gate("a", date(2026, 2, 8)), target(1), days=120)
    assert _horizontal_last(free) and _bends(free) <= 4
    # Too few bends for the repair: the unchanged candidate order is used, still without a reversal.
    tight = route(gate("a", date(2026, 2, 8)), target(1), days=120, max_bends=_bends(free) - 1)
    assert not reverses(tight) and _bends(tight) < _bends(free)
    any_points = route(gate("a", date(2026, 2, 8)), target(1), entry="any", days=120)
    assert not reverses(any_points)
