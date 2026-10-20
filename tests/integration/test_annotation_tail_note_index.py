"""A numbered callout index must clear its own accepted balloon tail."""
from __future__ import annotations

from chrona.presentation.layout.balloon_geometry import balloon_outline
from chrona.presentation.layout.labels import LabelRect, place_label
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
    obstacles_intersect,
)
from chrona.presentation.layout.surface_annotations import _register_balloon_tail_edges


def test_note_index_obstacle_sees_completed_tail_edges(monkeypatch):
    box = LabelRect(100, 100, 80, 40)
    tip = (60.0, 50.0)
    outline = balloon_outline(box, tip, corner_radius=4, tail_base=12)
    points = tuple(point for command in outline for point in command.points)
    tip_index = points.index(tip)
    tail_segment = ObstacleSegment(points[tip_index - 1], tip)
    midpoint = ((tail_segment.start[0] + tail_segment.end[0]) / 2,
                (tail_segment.start[1] + tail_segment.end[1]) / 2)
    note_index = LabelRect(midpoint[0] - 2, midpoint[1] - 2, 4, 4)
    note_index_rect = ObstacleRect(note_index.x, note_index.y, note_index.right, note_index.bottom)
    box_rect = ObstacleRect(box.x, box.y, box.right, box.bottom)
    assert not obstacles_intersect(note_index_rect, box_rect)
    assert obstacles_intersect(tail_segment, note_index_rect)

    real_add = SurfaceObstacleIndex.add

    def without_tail_edges(index, obstacle):
        if ":tail:" not in obstacle.placement_id:
            real_add(index, obstacle)

    def candidate(index):
        return place_label(note_index, (note_index.width, note_index.height), ("inside",),
                           bounds=LabelRect(0, 0, 300, 300), obstacles=index,
                           required=False, overflow="suppress")

    missing = SurfaceObstacleIndex()
    missing.add(SurfaceObstacle("annotation-box:note", "annotation-box", "annotations", box_rect))
    monkeypatch.setattr(SurfaceObstacleIndex, "add", without_tail_edges)
    _register_balloon_tail_edges(missing, "note", outline, tip)
    assert candidate(missing) is not None, "without tail registration the colliding index is incorrectly admitted"

    monkeypatch.setattr(SurfaceObstacleIndex, "add", real_add)
    complete = SurfaceObstacleIndex()
    complete.add(SurfaceObstacle("annotation-box:note", "annotation-box", "annotations", box_rect))
    _register_balloon_tail_edges(complete, "note", outline, tip)
    assert {item.placement_id for item in complete.collisions(note_index_rect)} == {
        "annotation-box:note:tail:0",
    }
    assert candidate(complete) is None
