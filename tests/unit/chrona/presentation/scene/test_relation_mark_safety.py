"""Synthetic published-Scene acceptance for #1114; no corpus data is an oracle."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, segment_length_inside_rect
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface
from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, _item, _route, _rows
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)


@pytest.mark.parametrize("entry", ["any", "side-when-free", "side"])
@pytest.mark.parametrize("endpoints", [("start", "at"), ("start", "start"), ("end", "end")])
def test_route_clears_own_and_foreign_marks_and_leaves_outward(entry, endpoints):
    mirrored = endpoints[0] == "end"
    source_start = D(2026, 2, 20) if mirrored else D(2026, 2, 3)
    target_start = D(2026, 2, 3) if mirrored else D(2026, 2, 20)
    source = _item("a", source_start, source_start + timedelta(days=7))
    target = (gate("b", target_start) if endpoints[1] == "at"
              else _item("b", target_start, target_start + timedelta(days=6)))
    relation = {"id": "dep", "from": {"object": "a", "endpoint": endpoints[0]},
                "to": {"object": "b", "endpoint": endpoints[1]}}
    points, marks = _route((source, target), _rows((source,), (target,)), relation, entry,
                          window=(D(2026, 1, 25), D(2026, 3, 5)), distribution="pack", max_detour=6)
    for mark in marks.values():
        x, y, w, h = mark.bounds
        rect = ObstacleRect(x + .5, y + .5, x + w - .5, y + h - .5)
        for a, b in zip(points, points[1:]):
            if a != b:
                assert segment_length_inside_rect(ObstacleSegment(a, b), rect) == 0, (mark.scene_id, points)
    assert points[1][0] >= points[0][0] if mirrored else points[1][0] <= points[0][0]


@pytest.mark.parametrize(("blocked_side", "row_order", "safe_side"), (
    ("above", ("a", "c", "b"), "below"),
    ("below", ("a", "b", "c"), "above"),
))
def test_route_uses_open_side_when_foreign_bar_closes_above_or_below(
        blocked_side, row_order, safe_side):
    """An adjacent foreign bar closes one vertical corridor; Layout uses the open side."""
    source = _item("a", D(2026, 2, 3), D(2026, 2, 10))
    target = _item("b", D(2026, 2, 20), D(2026, 2, 27))
    blocker = _item("c", D(2026, 2, 1), D(2026, 2, 28))
    by_id = {"a": source, "b": target, "c": blocker}
    rows = tuple(row for item_id in row_order for row in _rows((by_id[item_id],)))
    relation = {"id": "dep", "from": {"object": "a", "endpoint": "start"},
                "to": {"object": "b", "endpoint": "start"}}
    items = tuple(by_id[item_id] for item_id in row_order)
    projection = ReviewProjection(items, (D(2026, 1, 25), D(2026, 3, 5)), (), (), rows)
    measurements = MeasuredSources(
        {"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(8), "timeline.row.paddingBlock": Decimal(0),
         "timeline.mark.blockSize": Decimal(8)})
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
                       relation_entry="any", row_distribution="pack",
                       relation_max_detour_ratio=6)
    value = build_scene_input(
        projection=projection, surface_content=surface_content(relations=(relation,)),
        layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(),
        measured_sources=measurements, capabilities={"svg": True})
    surface = compose_review_surface(value)
    scene_relations = [item for item in surface.primitives
                       if item.scene_id.startswith("relation:")
                       and not item.scene_id.startswith("relation-label")]
    assert len(scene_relations) == 1
    points = scene_relations[0].points
    marks = {item.scene_id: item for item in surface.primitives
             if item.scene_id.startswith("planned:")}

    assert points  # an open side exists, so suppression is not an acceptable outcome
    source_bounds = marks["planned:a:a"].bounds
    assert points[1] != points[0]
    assert points[0][0] == pytest.approx(source_bounds[0])
    # The first leg may leave tangentially along the start boundary, but never
    # points back into the temporal bar; the inset-interior check below verifies it.
    assert points[1][0] <= points[0][0]

    blocker_bounds = marks["planned:c:c"].bounds
    target_bounds = marks["planned:b:b"].bounds
    left, top, width, height = blocker_bounds
    blocker_right, blocker_bottom = left + width, top + height
    target_left, target_top, target_width, target_height = target_bounds
    target_right, target_bottom = target_left + target_width, target_top + target_height
    assert min(blocker_right, target_right) > max(left, target_left)
    if blocked_side == "above":
        assert blocker_bottom == pytest.approx(target_top)
    else:
        assert top == pytest.approx(target_bottom)
    crossed_projection_on_open_side = False
    for start, end in zip(points, points[1:]):
        if start[1] != end[1]:
            continue
        projection_overlap = min(max(start[0], end[0]), blocker_right) - max(min(start[0], end[0]), left)
        if projection_overlap <= 0:
            continue
        if safe_side == "below" and start[1] > blocker_bottom:
            crossed_projection_on_open_side = True
        if safe_side == "above" and start[1] < top:
            crossed_projection_on_open_side = True
    assert crossed_projection_on_open_side, (blocked_side, safe_side, points, blocker_bounds)

    for mark in marks.values():
        x, y, mark_width, mark_height = mark.bounds
        # Inset by half the 1-unit relation stroke: boundary ink contact is legal.
        interior = ObstacleRect(x + 0.5, y + 0.5, x + mark_width - 0.5, y + mark_height - 0.5)
        for start, end in zip(points, points[1:]):
            if start != end:
                assert segment_length_inside_rect(ObstacleSegment(start, end), interior) == 0, (
                    blocked_side, mark.scene_id, points)


def test_diagonal_segments_are_measured_not_silently_ignored():
    assert segment_length_inside_rect(ObstacleSegment((0, 0), (20, 20)),
                                      ObstacleRect(5, 5, 15, 15)) == pytest.approx(10 * 2 ** .5)
    assert segment_length_inside_rect(ObstacleSegment((0, 5), (20, 5)), ObstacleRect(5, 5, 15, 15)) == 0


def test_unsafe_visible_fallback_is_suppressed_with_a_reason():
    source, target = _item("a", D(2026, 2, 3), D(2026, 2, 10)), _item("b", D(2026, 2, 20), D(2026, 2, 26))
    relation = {"id": "dep", "from": {"object": "a", "endpoint": "start"},
                "to": {"object": "b", "endpoint": "start"}}
    points, _, diagnostics = _route((source, target), _rows((source,), (target,)), relation, "any",
        max_bends=0, max_detour=1, window=(D(2026, 1, 25), D(2026, 3, 5)), distribution="pack",
        diagnostics=True, allow_suppressed=True)
    assert not points
    assert any(line.startswith("I_LAYOUT_RELATION_MARK_BLOCKED:") for line in diagnostics)
    assert any(line.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for line in diagnostics)
