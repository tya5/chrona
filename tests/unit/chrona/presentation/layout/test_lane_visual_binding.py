from datetime import date

import pytest

from chrona.presentation.layout.lane_projection import (
    ExpectedLaneMark, LaneProjectionClosure, LaneProjectionInstance,
)
from chrona.presentation.layout.lane_visual_binding import bind_lane_visual_requests
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection


def _item(object_id, item_id, source_kind="primary", attached_to=None):
    return ReviewItem(
        object_id, object_id.title(), "point" if attached_to else "span",
        {"at": date(2026, 1, 1)} if attached_to else {
            "start": date(2026, 1, 1), "end": date(2026, 1, 2),
        }, None, None, ("planned",), item_id=item_id, source_kind=source_kind,
        attached_to=attached_to,
    )


def _visual(kind, selector, *, side="leading", source="/body/visuals/0"):
    return VisualRequest(kind, tuple(selector.items()), ref="icon", side=side, source_ref=source)


def _fixture():
    primary_a = LaneProjectionInstance("row-a", "work-a", "work", "primary")
    snapshot_a = LaneProjectionInstance("row-a", "work-snapshot", "work", "snapshot")
    attached_a = LaneProjectionInstance("row-a", "gate-a", "gate", "primary")
    primary_b = LaneProjectionInstance("row-b", "work-b", "work", "primary")
    row_a = ReviewRowProjection("row-a", "A", "g", "work-a", (
        _item("work", "work-a"), _item("work", "work-snapshot", "snapshot"),
        _item("gate", "gate-a", attached_to="work"),
    ))
    row_b = ReviewRowProjection("row-b", "B", "g", "work-b", (_item("work", "work-b"),))
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
                                  rows=(row_a, row_b))
    closure = LaneProjectionClosure(
        (primary_a, snapshot_a, attached_a, primary_b),
        (ExpectedLaneMark(primary_a, "planned", "planned", "planned:a"),
         ExpectedLaneMark(snapshot_a, "snapshot", "snapshot", "snapshot:a"),
         ExpectedLaneMark(attached_a, "planned", "planned", "planned:gate"),
         ExpectedLaneMark(primary_b, "planned", "planned", "planned:b")),
        (), ((attached_a, primary_a),),
    )
    return projection, closure, primary_a, snapshot_a, attached_a, primary_b


def test_object_plot_label_fans_out_per_countable_occurrence_and_attached_child():
    projection, closure, primary_a, snapshot_a, attached_a, primary_b = _fixture()
    labels, marks = bind_lane_visual_requests(
        projection, closure,
        (_visual("plot-label", {"id": "work"}), _visual("plot-label", {"id": "gate"})),
    )

    assert set(labels) == {primary_a, primary_b, attached_a}
    assert snapshot_a not in labels
    assert all(len(values) == 1 for values in labels.values())
    assert marks == {}


def test_semantic_mark_visual_fans_out_to_primary_and_comparison_roles():
    projection, closure, primary_a, snapshot_a, _attached_a, primary_b = _fixture()
    _labels, marks = bind_lane_visual_requests(
        projection, closure, (_visual("mark", {"object": "work", "facet": "planned"}),),
    )

    assert set(marks) == {(primary_a, "planned"), (snapshot_a, "snapshot"),
                          (primary_b, "planned")}


def test_unknown_visual_target_fails_closed():
    projection, closure, *_ = _fixture()
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        bind_lane_visual_requests(
            projection, closure, (_visual("plot-label", {"id": "unknown"}),),
        )


def test_unknown_semantic_mark_role_fails_closed():
    projection, closure, *_ = _fixture()
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        bind_lane_visual_requests(
            projection, closure,
            (_visual("mark", {"object": "work", "facet": "unsupported"}),),
        )


def test_duplicate_plot_label_side_fails_on_each_matching_occurrence():
    projection, closure, *_ = _fixture()
    visuals = (_visual("plot-label", {"id": "work"}, source="/body/visuals/0"),
               _visual("plot-label", {"id": "work"}, source="/body/visuals/1"))
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_DUPLICATE"):
        bind_lane_visual_requests(projection, closure, visuals)


def test_duplicate_mark_visual_fails_for_same_semantic_occurrence():
    projection, closure, *_ = _fixture()
    visuals = (_visual("mark", {"object": "work", "facet": "planned"}, source="/body/visuals/0"),
               _visual("mark", {"object": "work", "facet": "planned"}, source="/body/visuals/1"))
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_DUPLICATE"):
        bind_lane_visual_requests(projection, closure, visuals)
