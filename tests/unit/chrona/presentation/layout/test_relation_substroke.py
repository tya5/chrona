from math import isclose
from dataclasses import replace

import pytest

from chrona.presentation.layout.relation_terminals import (
    complete_centred_terminals,
    marker_geometry,
    orient_terminal,
)
from chrona.presentation.layout.routing import remove_substroke_jogs


def _reduce(points, *, accept=lambda _candidate: True, minimum=1.0):
    return remove_substroke_jogs(points, minimum, accept=accept)


def test_substroke_jog_near_start_collapses_without_moving_ports():
    points = ((0.0, 0.0), (4.0, 0.0), (4.0, 0.4), (8.0, 0.4), (8.0, 5.0))
    result = _reduce(points)

    assert result == ((0.0, 0.0), (8.0, 0.0), (8.0, 5.0))
    assert result[0] == points[0] and result[-1] == points[-1]


def test_substroke_jog_near_end_collapses_without_moving_ports():
    points = ((0.0, 0.0), (0.0, 5.0), (4.0, 5.0), (4.0, 4.6), (8.0, 4.6))
    result = _reduce(points)

    assert result == ((0.0, 0.0), (0.0, 4.6), (8.0, 4.6))
    assert result[0] == points[0] and result[-1] == points[-1]


def test_interior_substroke_jog_collapses_and_keeps_exact_endpoints():
    points = ((0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (8.0, 5.0), (8.0, 5.4), (12.0, 5.4), (12.0, 9.0))
    result = _reduce(points)

    assert result == ((0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (12.0, 5.0), (12.0, 9.0))
    assert result[0] == points[0] and result[-1] == points[-1]


def test_obstacle_callback_can_reject_every_substroke_replacement():
    points = ((0.0, 0.0), (4.0, 0.0), (4.0, 0.4), (8.0, 0.4), (8.0, 5.0))

    assert _reduce(points, accept=lambda _candidate: False) == points


def test_wider_s_jog_is_not_reduced_by_the_substroke_pass():
    points = ((0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (8.0, 2.0), (8.0, 5.0))

    assert _reduce(points) == points


def test_collinear_and_straight_routes_keep_their_exact_coordinates():
    collinear = ((0.0, 0.0), (5.0, 0.0), (5.0, 0.4), (5.0, 5.0), (7.0, 5.0))
    straight = ((0.0, 0.0), (0.4, 0.0))

    assert _reduce(collinear) == ((0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (7.0, 5.0))
    assert _reduce(straight) == straight


def _marker(head_length=4.0):
    return marker_geometry({"shape": "triangle", "headLength": head_length,
                            "headWidth": 3.0, "attachmentOffset": 0.0})


@pytest.mark.parametrize("angle", [float("nan"), float("inf"), True, "90"])
def test_completed_marker_axis_rejects_nonfinite_or_nonnumeric_values(angle):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(_marker(), angle_degrees=angle)


def test_marker_uses_first_sufficient_source_leg_and_last_sufficient_target_leg():
    marker = _marker()
    points = ((0.0, 0.0), (0.5, 0.0), (0.5, 5.0), (4.0, 5.0), (4.5, 5.0))

    source = orient_terminal(marker, points, "at", source=True)
    target = orient_terminal(marker, points, "at", source=False)

    assert source is not None and isclose(source.angle_degrees, 90.0)
    assert target is not None and isclose(target.angle_degrees, 90.0)


def test_short_tangent_prefers_port_normal_even_when_a_longer_leg_exists():
    marker = _marker()
    points = ((0.0, 0.0), (0.5, 0.0), (0.5, 5.0), (4.0, 5.0), (4.5, 5.0))

    source = orient_terminal(marker, points, "start", source=True)
    target = orient_terminal(marker, points, "end", source=False)

    assert source is not None and isclose(source.angle_degrees, 180.0)
    assert target is not None and isclose(target.angle_degrees, 180.0)


def test_marker_uses_selected_port_normal_when_no_leg_reaches_head_length():
    marker = _marker()
    points = ((0.0, 0.0), (0.5, 0.0), (0.5, 0.5))

    source = orient_terminal(marker, points, "below", source=True)
    target = orient_terminal(marker, points, "below", source=False)

    assert source is not None and isclose(source.angle_degrees, 90.0)
    assert target is not None and isclose(target.angle_degrees, -90.0)


def test_short_gap_between_centred_terminals_keeps_stroke_run_and_marker_centres():
    circle = marker_geometry({"shape": "circle", "headLength": 4.0,
                              "headWidth": 4.0, "attachmentOffset": 0.0})
    points = ((0.0, 0.0), (3.0, 0.0))

    completed, start, end = complete_centred_terminals(points, circle, circle, minimum=1.0)

    assert completed == ((1.0, 0.0), (2.0, 0.0))
    assert completed[1][0] - completed[0][0] >= 1.0
    assert start is not None and start.attachment_offset == 1.0
    assert end is not None and end.attachment_offset == 3.0


def test_unconstrained_straight_route_preserves_exact_points_and_no_markers():
    points = ((0.0, 0.0), (0.4, 0.0))

    completed, start, end = complete_centred_terminals(points, None, None, minimum=1.0)

    assert completed == points
    assert start is None and end is None
