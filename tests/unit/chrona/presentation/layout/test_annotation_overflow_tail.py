import math

import pytest

from chrona.presentation.layout.annotations import visible_overflow_tail_box
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex


def _empty_obstacles():
    return SurfaceObstacleIndex()


def test_visible_overflow_tail_box_uses_nearest_separated_anchor_side():
    region = LabelRect(0, 0, 100, 100)
    anchor = LabelRect(49.5, 45, 1, 10)

    box, tip = visible_overflow_tail_box(region=region, anchor=anchor, box_size=(20, 10),
                                        obstacles=_empty_obstacles(), obstacle_classes=("text", "annotation-box"),
                                        corner_radius=0, tail_base=2)

    assert box == LabelRect(40, 30, 20, 10)
    assert tip == (50, 45)
    assert box.bottom < anchor.y


def test_visible_overflow_tail_box_prefers_least_plot_overflow_then_stable_ties():
    # The anchor is at the upper edge, so the top placement overflows more;
    # equal-distance horizontal candidates are resolved by block then inline.
    box, tip = visible_overflow_tail_box(
        region=LabelRect(0, 0, 100, 100), anchor=LabelRect(49.5, 0, 1, 10), box_size=(20, 10),
        obstacles=_empty_obstacles(), obstacle_classes=("text", "annotation-box"),
        corner_radius=0, tail_base=2)

    assert box == LabelRect(40, 15, 20, 10)
    assert tip == (50, 10)
    assert box.y >= 0


def test_visible_overflow_tail_prefers_clear_far_side_over_covering_prior_note():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("prior-note", "text", "annotations",
                                  ObstacleRect(40, 25, 70, 45)))
    obstacles.add(SurfaceObstacle("lower-mark", "mark", "plot", ObstacleRect(40, 65, 70, 85)))
    obstacles.add(SurfaceObstacle("left-mark", "mark", "plot", ObstacleRect(5, 40, 35, 60)))

    box, tip = visible_overflow_tail_box(
        region=LabelRect(0, 0, 120, 100), anchor=LabelRect(50, 45, 10, 10),
        box_size=(30, 20), obstacles=obstacles,
        obstacle_classes=("text", "annotation-box", "mark"), corner_radius=0, tail_base=2)

    assert box == LabelRect(75, 40, 30, 20)
    assert tip == (60, 50)
    assert not obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom), classes=("text", "annotation-box"))


@pytest.mark.parametrize(("region", "anchor", "box_size"), [
    (LabelRect(0, 0, float("nan"), 10), LabelRect(1, 1, 1, 1), (2, 2)),
    (LabelRect(0, 0, 10, 10), LabelRect(1, 1, 1, 1), (0, 2)),
    (LabelRect(0, 0, 10, 10), LabelRect(1, 1, 1, 1), (math.inf, 2)),
])
def test_visible_overflow_tail_box_rejects_invalid_geometry(region, anchor, box_size):
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT: visible-overflow tail box"):
        visible_overflow_tail_box(region=region, anchor=anchor, box_size=box_size,
                                  obstacles=_empty_obstacles(), obstacle_classes=("text", "annotation-box"),
                                  corner_radius=0, tail_base=2)
