import pytest

from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.balloon_geometry import balloon_outline, nearest_eligible_edge, tail_base_points


@pytest.mark.parametrize("tip,expected_edge", [
    ((130, 60), "top"),
    ((130, 160), "bottom"),
    ((60, 115), "left"),
    ((200, 115), "right"),
])
def test_nearest_eligible_edge_picks_the_edge_the_tip_protrudes_past_most(tip, expected_edge) -> None:
    box = LabelRect(100, 100, 60, 30)
    assert nearest_eligible_edge(box, tip) == expected_edge


def test_tail_base_points_stay_on_the_declared_edge_and_are_ordered_clockwise() -> None:
    box = LabelRect(100, 100, 60, 30)
    a, b = tail_base_points(box, (130, 60), edge="top", tail_base=10, corner_radius=0)
    assert a[1] == box.y == b[1]
    assert a[0] < b[0]  # clockwise along the top edge: left point first


def test_tail_base_points_clear_rounded_corners() -> None:
    box = LabelRect(0, 0, 20, 10)
    a, b = tail_base_points(box, (10, -5), edge="top", tail_base=100, corner_radius=4)
    # A tail base wider than the edge is clamped clear of both corners.
    assert a[0] >= 4 - 1e-9 and b[0] <= 16 + 1e-9


def test_balloon_outline_is_closed_and_includes_the_tip_as_a_vertex() -> None:
    box = LabelRect(100, 100, 60, 30)
    tip = (60, 115)
    outline = balloon_outline(box, tip, corner_radius=4, tail_base=10)
    assert outline[0].kind == "move"
    assert outline[0].points[0] == outline[-1].points[0]
    assert tip in {point for command in outline for point in command.points}


def test_balloon_outline_without_rounding_is_a_simple_polygon_around_the_box() -> None:
    box = LabelRect(100, 100, 60, 30)
    outline = balloon_outline(box, (130, 60), corner_radius=0, tail_base=10)
    points = [point for command in outline for point in command.points]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    # Every vertex stays within the box's bounding extent widened only by the tail's tip.
    assert min(xs) >= box.x - 1e-9 and max(xs) <= box.right + 1e-9
    assert min(ys) >= 60 - 1e-9 and max(ys) <= box.bottom + 1e-9


def test_balloon_outline_rejects_non_finite_geometry() -> None:
    box = LabelRect(0, 0, 20, 10)
    with pytest.raises(ValueError):
        balloon_outline(box, (10, -5), corner_radius=-1, tail_base=4)
    with pytest.raises(ValueError):
        balloon_outline(box, (10, -5), corner_radius=1, tail_base=0)
