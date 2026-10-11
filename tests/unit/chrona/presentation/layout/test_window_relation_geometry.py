from dataclasses import replace

import pytest

from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_quality import PaintClip, PathCommand
from chrona.presentation.layout.window_relation_geometry import relation_geometry_inside_plot


def _marker(shape="triangle", **extra):
    return marker_geometry({"shape": shape, "headLength": 4, "headWidth": 8, **extra}, stroke_width=1)


def test_route_containment_uses_completed_plot_not_canvas_or_path_endpoints_only():
    clip = PaintClip((10, 20, 30, 40))
    assert relation_geometry_inside_plot(clip, ((10, 20), (40, 60)), stroke_width=1)
    assert not relation_geometry_inside_plot(clip, ((10, 20), (9, 40), (40, 60)), stroke_width=1)
    assert not relation_geometry_inside_plot(clip, ((10, 20), (40, 61)), stroke_width=1)
    assert not relation_geometry_inside_plot(clip, (), stroke_width=1)


@pytest.mark.parametrize("shape", ["triangle", "open-triangle", "chevron", "circle", "open-circle",
                                   "stealth", "rounded-triangle", "dot", "half", "double-chevron"])
def test_whole_terminal_contour_must_fit_not_only_its_attached_route(shape):
    marker = _marker(shape)
    points = ((2, 5), (8, 5))
    assert relation_geometry_inside_plot(PaintClip((0, 0, 10, 10)), points,
        marker_end=marker, stroke_width=1)
    assert not relation_geometry_inside_plot(PaintClip((0, 4, 10, 2)), points,
        marker_end=marker, stroke_width=1)


def test_explicit_terminal_angle_and_legacy_stroke_units_are_completed_before_containment():
    marker = replace(_marker(attachmentOffset=0), angle_degrees=90)
    points = ((2, 5), (8, 5))
    assert relation_geometry_inside_plot(PaintClip((0, 0, 12, 12)), points,
        marker_end=marker, stroke_width=1)
    assert not relation_geometry_inside_plot(PaintClip((0, 0, 12, 12)), points,
        marker_end=marker, stroke_width=4)


def test_completed_curve_controls_and_source_terminal_are_checked_too():
    clip = PaintClip((0, 0, 10, 10))
    points = ((2, 5), (8, 5))
    commands = (PathCommand("move", ((2, 5),)), PathCommand("quadratic", ((5, -1), (8, 5))))
    assert not relation_geometry_inside_plot(clip, points, path_commands=commands, stroke_width=1)
    assert not relation_geometry_inside_plot(PaintClip((0, 4, 10, 2)), points,
        marker_start=_marker(), stroke_width=1)
