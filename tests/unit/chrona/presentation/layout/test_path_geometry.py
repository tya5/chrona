import pytest

from chrona.presentation.layout import path_geometry
from chrona.presentation.layout.path_geometry import (
    conservative_path_segments, curved_orthogonal_path, metro_orthogonal_path,
    path_extrema, rounded_diamond_path, rounded_orthogonal_path,
)
from chrona.presentation.layout.surface_quality import PathCommand


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


def test_curved_orthogonal_path_smooths_a_u_route_without_inventing_an_s():
    points = ((0, 0), (0, 10), (10, 10), (10, 0))

    commands = curved_orthogonal_path(points)

    assert tuple(command.kind for command in commands) == ("move", "line", "quadratic", "quadratic", "line")
    assert commands[1].points == ((0.0, 5.0),)
    assert commands[2].points == ((0.0, 10.0), (5.0, 10.0))
    assert commands[3].points == ((10.0, 10.0), (10.0, 5.0))
    assert commands[4].points == ((10.0, 0.0),)


def test_opposite_turns_form_a_true_s_with_opposite_signed_curvature():
    commands = curved_orthogonal_path(((0, 0), (80, 0), (80, 160), (160, 160)))
    current = commands[0].points[0]
    signs = []
    for command in commands[1:]:
        if command.kind == "quadratic":
            control, end = command.points
            signs.append((control[0] - current[0]) * (end[1] - control[1])
                         - (control[1] - current[1]) * (end[0] - control[0]))
        current = command.points[-1]
    assert len(signs) == 2 and signs[0] * signs[1] < 0
    assert tuple(command.kind for command in commands) == ("move", "quadratic", "quadratic")
    assert commands[1].points == ((80.0, 0.0), (80.0, 80.0))
    assert commands[2].points == ((80.0, 160.0), (160.0, 160.0))


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


def test_metro_path_inserts_45_degree_diagonals_and_quadratic_fillet_joins():
    commands = metro_orthogonal_path(
        ((0, 0), (20, 0), (20, 20), (0, 20)), radius=1)

    assert tuple(command.kind for command in commands) == (
        "move", "line", "quadratic", "line", "quadratic", "quadratic", "line", "quadratic", "line")
    assert commands[1].points == ((10.0, 0.0),)
    assert commands[2].points == ((10.414213562373096, 0.0), (10.707106781186548, 0.2928932188134525))
    assert commands[4].points == ((20.0, 9.585786437626904), (20.0, 10.0))
    assert commands[5].points == ((20.0, 10.414213562373096), (19.707106781186546, 10.707106781186548))
    assert commands[7].points == ((10.414213562373096, 20.0), (10.0, 20.0))
    current = commands[0].points[0]
    diagonal_lengths = []
    for command in commands[1:]:
        endpoint = command.points[-1]
        if command.kind == "line" and endpoint[0] != current[0] and endpoint[1] != current[1]:
            diagonal_lengths.append(((endpoint[0] - current[0]) ** 2
                                     + (endpoint[1] - current[1]) ** 2) ** 0.5)
        current = endpoint
    assert len(diagonal_lengths) == 2
    budget = 10.0
    setback = min(1 * (2**0.5 - 1), budget * 2**0.5 / (4 + 2**0.5))
    diagonal_length = 2**0.5 * (budget - setback)
    assert all(length >= diagonal_length / 2 for length in diagonal_lengths)


def test_metro_zero_radius_keeps_sharp_45_joins_and_terminal_runs():
    commands = metro_orthogonal_path(
        ((0, 0), (20, 0), (20, 20), (0, 20)), radius=0,
        start_run=4, end_run=3)

    assert not any(command.kind == "quadratic" for command in commands)
    assert commands[0].points == ((0.0, 0.0),)
    assert commands[1].points == ((10.0, 0.0),)
    assert commands[-1].points == ((0.0, 20.0),)
    assert commands[-2].points == ((10.0, 20.0),)


def test_metro_zero_cut_falls_back_to_the_complete_orthogonal_polyline():
    points = ((0, 0), (10, 0), (10, 10))

    commands = metro_orthogonal_path(points, radius=2, start_run=10)

    assert tuple(command.kind for command in commands) == ("move", "line", "line")
    assert tuple(command.points[0] for command in commands) == tuple(
        points)


def test_metro_straight_path_stays_straight_and_short_legs_remain_bounded():
    straight = metro_orthogonal_path(((0, 0), (10, 0), (20, 0)), radius=3)
    short = metro_orthogonal_path(
        ((0, 0), (4, 0), (4, 4), (0, 4)), radius=20)

    assert tuple(command.kind for command in straight) == ("move", "line")
    assert all(all(abs(value) < 100 for point in command.points for value in point)
               for command in short)
    assert sum(command.kind == "quadratic" for command in short) >= 1


def test_metro_radius_uses_tangent_setback_for_45_degree_join():
    commands = metro_orthogonal_path(
        ((0, 0), (20, 0), (20, 20), (0, 20)), radius=4)

    # A 45-degree deflection has setback r*tan(22.5°), capped by its legs.
    expected = 4 * (2**0.5 - 1)
    assert commands[1].points[0] == (10, 0)
    assert commands[2].points[0] == pytest.approx((10 + expected, 0))
    assert commands[2].points[1] == pytest.approx((10 + expected + expected / 2**0.5,
                                                     expected / 2**0.5))


def test_metro_rounds_each_45_degree_join_with_a_joint_terminal_budget():
    commands = metro_orthogonal_path(
        ((0, 0), (20, 0), (20, 20)), radius=1, start_run=4, end_run=4)

    assert sum(command.kind == "quadratic" for command in commands) == 2
    # The line before the first fillet and after the last one retains the
    # requested straight terminal run exactly.
    assert commands[1].points[0] == pytest.approx((4.0, 0.0))
    assert commands[-1].points == ((20.0, 20.0),)
    assert commands[-2].points[-1] == pytest.approx((20.0, 16.0))


def test_metro_final_fillet_setback_respects_half_short_terminal_orth_leg():
    commands = metro_orthogonal_path(((0, 0), (20, 0), (20, 10)), radius=1)

    # The final vertical terminal leg is much shorter than the first. Its
    # rounded join remains positive but is capped at half the adjacent leg.
    final_join = commands[4]
    assert final_join.kind == "quadratic"
    setback = final_join.points[1][1] - final_join.points[0][1]
    adjacent_leg = 10 - final_join.points[0][1]
    assert setback > 0
    assert setback <= adjacent_leg / 2


def test_path_extrema_include_quadratic_derivative_roots_between_four_chords():
    commands = (PathCommand("move", ((0.0, 0.0),)),
                PathCommand("quadratic", ((10.0, 16.0), (20.0, 8.0))))
    points = path_extrema(commands)

    assert any(point == pytest.approx((40 / 3, 32 / 3)) for point in points)
    four_chord_y = tuple(2 * (1 - t) * t * 16 + t * t * 8 for t in (0.25, 0.5, 0.75))
    assert max(four_chord_y) < 32 / 3
    assert max(point[1] for point in points) == pytest.approx(32 / 3)


@pytest.mark.parametrize("radius,start_run,end_run", [
    (-1, 0, 0), (float("nan"), 0, 0), (1, -1, 0), (1, 0, float("inf")),
])
def test_metro_rejects_invalid_radius_and_terminal_runs(radius, start_run, end_run):
    with pytest.raises(ValueError, match="E_LAYOUT_PATH_INPUT"):
        metro_orthogonal_path(((0, 0), (10, 0), (10, 10)), radius=radius,
                              start_run=start_run, end_run=end_run)


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
