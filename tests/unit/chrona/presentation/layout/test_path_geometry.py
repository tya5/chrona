import pytest

from chrona.presentation.layout import path_geometry
from chrona.presentation.layout.path_geometry import (
    conservative_path_segments, curved_orthogonal_path, rounded_diamond_path,
    rounded_orthogonal_path,
)


def test_zero_radius_preserves_the_polyline_as_completed_commands():
    commands = rounded_orthogonal_path(((1, 1), (1, 9), (9, 9)), 0)
    assert tuple(command.kind for command in commands) == ("move", "line", "line")
    assert commands[-1].points == ((9, 9),)


def test_radius_is_clamped_by_both_adjoining_legs():
    commands = rounded_orthogonal_path(((0, 0), (0, 4), (3, 4)), 10)
    assert tuple(command.kind for command in commands) == ("move", "line", "quadratic", "line")
    assert commands[1].points == ((0.0, 2.5),)
    assert commands[2].points == ((0, 4), (1.5, 4.0))
    assert commands[-1].points == ((3, 4),)


def test_non_orthogonal_or_negative_input_is_rejected():
    with pytest.raises(ValueError, match="E_LAYOUT_PATH_INPUT"):
        rounded_orthogonal_path(((0, 0), (1, 1)), 1)
    with pytest.raises(ValueError, match="E_LAYOUT_PATH_INPUT"):
        rounded_orthogonal_path(((0, 0), (0, 1)), -1)


def test_rounded_diamond_is_a_closed_layout_owned_quadratic_path():
    commands = rounded_diamond_path(inline=0, block=0, inline_size=8, block_size=8, radius=2)
    assert commands[0].kind == "move"
    assert sum(command.kind == "quadratic" for command in commands) == 4
    assert commands[-1].points == commands[0].points


def test_curved_orthogonal_path_builds_a_true_s_from_opposite_turns():
    points = ((0, 0), (0, 10), (10, 10), (10, 0))

    commands = curved_orthogonal_path(points)

    assert tuple(command.kind for command in commands) == ("move", "line", "quadratic", "quadratic", "line")
    assert commands[1].points == ((0.0, 5.0),)
    assert commands[2].points == ((0.0, 10.0), (5.0, 10.0))
    assert commands[3].points == ((10.0, 10.0), (10.0, 5.0))
    assert commands[4].points == ((10.0, 0.0),)


def test_curved_path_reserves_terminal_runs_but_uses_available_terminal_leg():
    commands = curved_orthogonal_path(
        ((0, 0), (0, 10), (10, 10), (10, 0)), start_run=7, end_run=6)

    assert commands[1].points == ((0.0, 7.0),)
    assert commands[2].points == ((0.0, 10.0), (3.0, 10.0))
    assert commands[3].points == ((6.0, 10.0),)
    assert commands[4].points == ((10.0, 10.0), (10.0, 6.0))
    assert commands[5].points == ((10.0, 0.0),)


def test_curved_path_simplifies_only_repeated_and_forward_collinear_vertices():
    simplified = curved_orthogonal_path(((0, 0), (0, 0), (0, 4), (0, 8), (8, 8)))
    reversed_leg = curved_orthogonal_path(((0, 0), (0, 8), (0, 3), (5, 3)))

    assert simplified[0].points == ((0.0, 0.0),)
    assert sum(command.kind == "quadratic" for command in simplified) == 1
    assert tuple(command.points for command in reversed_leg if command.kind == "line") == (
        ((0.0, 8.0),), ((0.0, 5.5),), ((5.0, 3.0),))
    assert any(command.kind == "quadratic" and command.points == ((0.0, 3.0), (2.5, 3.0))
               for command in reversed_leg)


def test_curved_path_straight_route_has_no_invented_bend_and_legacy_rounding_is_unchanged():
    straight = curved_orthogonal_path(((1, 2), (1, 5), (1, 9)))
    legacy = rounded_orthogonal_path(((1, 2), (1, 5), (1, 9)), 4)

    assert tuple(command.kind for command in straight) == ("move", "line")
    assert straight[-1].points == ((1.0, 9.0),)
    assert tuple(command.kind for command in legacy) == ("move", "line", "line")


@pytest.mark.parametrize("points,start_run,end_run", [
    (((0, 0), (1, 1)), 0, 0),
    (((0, 0), (float("nan"), 1)), 0, 0),
    (((0, 0), (0, 1)), float("inf"), 0),
    (((0, 0), (0, 1)), 0, -1),
    (((0, 0), (0, 0)), 0, 0),
])
def test_curved_path_rejects_invalid_or_degenerate_geometry(points, start_run, end_run):
    with pytest.raises(ValueError, match="E_LAYOUT_PATH_INPUT"):
        curved_orthogonal_path(points, start_run=start_run, end_run=end_run)


def _distance_to_segment(point, segment):
    (x, y), (ax, ay), (bx, by) = point, segment.start, segment.end
    dx, dy = bx - ax, by - ay
    amount = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return ((x - (ax + amount * dx)) ** 2 + (y - (ay + amount * dy)) ** 2) ** 0.5


def test_conservative_curve_cover_inflates_subdivided_chords_between_legacy_samples():
    commands = (
        path_geometry.PathCommand("move", ((0.0, 0.0),)),
        path_geometry.PathCommand("quadratic", ((10.0, 10.0), (20.0, 0.0))),
    )
    cover = conservative_path_segments(commands, 2.0)
    samples = tuple((20 * t, 20 * t * (1 - t)) for t in (i / 32 for i in range(1, 32)))

    assert len(cover) > 4
    assert all(min(_distance_to_segment(sample, segment) - segment.stroke_width / 2
                   for segment in cover) <= 1e-10 for sample in samples)
    assert all(segment.stroke_width >= 2.0 for segment in cover)


def test_conservative_cover_remains_conservative_when_subdivision_cap_is_reached(monkeypatch):
    monkeypatch.setattr(path_geometry, "_QUADRATIC_COVER_MAX_DEPTH", 0)
    commands = (
        path_geometry.PathCommand("move", ((0.0, 0.0),)),
        path_geometry.PathCommand("quadratic", ((10.0, 10.0), (20.0, 0.0))),
    )

    cover = conservative_path_segments(commands, 2.0)

    assert len(cover) == 1
    assert cover[0].stroke_width >= 12.0
    assert all(_distance_to_segment((20 * t, 20 * t * (1 - t)), cover[0])
               <= cover[0].stroke_width / 2 for t in (i / 32 for i in range(33)))


@pytest.mark.parametrize("stroke_width,max_deviation", [
    (-1, 0.25), (float("nan"), 0.25), (True, 0.25), (1, 0), (1, float("inf")),
])
def test_conservative_path_cover_rejects_invalid_tolerances(stroke_width, max_deviation):
    commands = (path_geometry.PathCommand("move", ((0.0, 0.0),)),
                path_geometry.PathCommand("line", ((1.0, 0.0),)))
    with pytest.raises(ValueError, match="E_LAYOUT_PATH_INPUT"):
        conservative_path_segments(commands, stroke_width, max_deviation=max_deviation)
