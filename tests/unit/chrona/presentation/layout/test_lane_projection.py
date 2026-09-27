"""Identity and expected-emission closure for lane Review projections."""
from datetime import date

import pytest

from chrona.presentation.layout.lane_projection import close_lane_projection
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection


def _item(object_id, *, item_id=None, attached_to=None, source_kind="primary"):
    return ReviewItem(
        object_id=object_id, title=object_id, source_type="span",
        planned={"start": date(2026, 1, 1), "finish": date(2026, 1, 3)},
        actual=None, finish_delta=None, roles=("planned",), item_id=item_id or object_id,
        source_kind=source_kind, attached_to=attached_to,
    )


def _projection(*rows):
    return ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (), rows=tuple(rows))


def test_closure_returns_typed_instances_expected_ids_and_exact_attached_host():
    host = _item("host", item_id="host-view")
    point = _item("gate", item_id="gate-view", attached_to="host")
    projection = _projection(ReviewRowProjection("row:one", "One", "g", "host", (host, point)))

    result = close_lane_projection(projection, {
        ("row:one", "host-view"): ("planned", "actual"),
        ("row:one", "gate-view"): ("planned",),
    })

    assert [(mark.role, mark.placement_id) for mark in result.expected_marks] == [
        ("planned", "planned:row:one:host-view"),
        ("actual", "actual:row:one:host-view"),
        ("planned", "planned:row:one:gate-view"),
    ]
    child, resolved_host = result.attached_hosts[0]
    assert (child.object_id, child.item_id) == ("gate", "gate-view")
    assert (resolved_host.object_id, resolved_host.item_id) == ("host", "host-view")


@pytest.mark.parametrize("roles", [
    {("row", "item"): ("planned",), ("row", "extra"): ("actual",)},
    {("row", "item"): ("planned", "planned")},
    {("row", "item"): ("unrecognized",)},
])
def test_closure_rejects_incomplete_or_invalid_expected_sets(roles):
    projection = _projection(ReviewRowProjection("row", "Row", "g", "item", (_item("item"),)))
    with pytest.raises(LayoutError):
        close_lane_projection(projection, roles)


def test_attached_host_must_resolve_to_exactly_one_selected_instance_in_same_row():
    child = _item("child", attached_to="host")
    projection = _projection(ReviewRowProjection("row", "Row", "g", "child", (child,)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_ATTACHED_HOST_INVALID"):
        close_lane_projection(projection, {("row", "child"): ("planned",)})

    duplicate_hosts = _projection(ReviewRowProjection(
        "row", "Row", "g", "child", (_item("host", item_id="host-a"),
                                          _item("host", item_id="host-b"), child)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_ATTACHED_HOST_INVALID"):
        close_lane_projection(duplicate_hosts, {
            ("row", "host-a"): ("planned",), ("row", "host-b"): ("planned",),
            ("row", "child"): ("planned",),
        })


def test_folded_points_and_non_timeline_projection_fail_closed():
    folded = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
                              rows=(ReviewRowProjection("row", "Row", "g", "item", (_item("item"),)),),
                              folded_points=(object(),))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PROJECTION_UNSUPPORTED"):
        close_lane_projection(folded, {("row", "item"): ("planned",)})
    not_timeline = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
                                    rows=(ReviewRowProjection(
                                        "row", "Row", "g", "item", (_item("item"),)),),
                                    surface="dependency-network")
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PROJECTION_UNSUPPORTED"):
        close_lane_projection(not_timeline, {("row", "item"): ("planned",)})
