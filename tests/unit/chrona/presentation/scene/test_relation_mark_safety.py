"""Synthetic published-Scene acceptance for #1114; no corpus data is an oracle."""
from datetime import timedelta

import pytest

from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, segment_length_inside_rect
from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, _item, _route, _rows
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate


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
