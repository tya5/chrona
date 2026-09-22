import pytest

from chrona.presentation.layout.path_geometry import rounded_orthogonal_path


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
