"""The relation terminal shape `none` draws no terminal and sets nothing back from the port (#1105).

Synthetic projections routed by the real surface composer; nothing reads `examples/`.
"""
from dataclasses import replace

import pytest

from chrona.presentation.layout.path_geometry import rounded_orthogonal_path
from chrona.presentation.layout.relation_terminals import SHAPES, centred_on_route, marker_geometry, terminal_run
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive

from tests.unit.chrona.presentation.scene.test_relation_round_terminals import (
    A, B, DEP, _compose, _end_port, _mark, _rows, _start_port,
)
from tests.unit.chrona.presentation.scene.test_v05_builder import _legend_surface, _theme

TOKEN = {"headLength": 8, "headWidth": 8, "attachmentOffset": 1}


def _path(source, target, **options):
    return _compose((A, B), _rows((A,), (B,)), DEP, source, target, **options)


def test_a_none_source_has_no_marker_and_the_route_starts_at_the_source_port():
    path, marks = _path("none", "triangle")
    assert path.marker_start is None and path.marker_end is not None
    assert path.points[0] == pytest.approx(_end_port(_mark(marks, "a")))
    assert path.points[-1] == pytest.approx(_start_port(_mark(marks, "b")))


def test_a_none_target_has_no_marker_and_the_route_ends_at_the_target_port():
    path, marks = _path("circle", "none")
    assert path.marker_end is None and path.marker_start is not None
    assert path.points[-1] == pytest.approx(_start_port(_mark(marks, "b")))


def test_both_none_draws_a_plain_stroke_and_no_marker_reaches_any_adapter():
    path, marks = _path("none", "none")
    assert path.marker_start is None and path.marker_end is None
    assert path.points[0] == pytest.approx(_end_port(_mark(marks, "a")))
    assert path.points[-1] == pytest.approx(_start_port(_mark(marks, "b")))


def test_none_with_a_corner_radius_keeps_the_ends_at_the_ports_and_rounds_the_turns():
    path, marks = _path("none", "none", radius=4)
    assert path.path_commands and path.path_commands[0].points[0] == path.points[0]
    assert path.path_commands[-1].points[-1] == path.points[-1]
    assert any(c.kind == "quadratic" for c in path.path_commands)


def test_none_reserves_no_head_run_on_an_explicit_short_leg_and_svg_keeps_layout_commands():
    points = ((0, 0), (0, 20), (4, 20))
    plain_commands = rounded_orthogonal_path(points, 4, end_run=terminal_run(None))
    headed_marker = marker_geometry({"shape": "triangle", "headLength": 10,
                                     "headWidth": 8, "attachmentOffset": 1})
    headed_commands = rounded_orthogonal_path(points, 4, end_run=terminal_run(headed_marker))
    assert [item.kind for item in plain_commands] == ["move", "line", "quadratic", "line"]
    assert plain_commands[2].points == ((0, 20), (2.0, 20.0))
    assert [item.kind for item in headed_commands] == ["move", "line", "line"]
    assert headed_commands[1].points == ((0, 20),)

    paint = ScenePaint(None, "#000000", 1, (), 1)
    plain = ScenePrimitive("plain", "Path", "plain", "relation", "dependency-connector", "dependency",
                           (0, 0, 4, 20), slot_id="s", paint=paint, points=points,
                           path_commands=plain_commands)
    headed = replace(plain, scene_id="headed", marker_end=headed_marker, path_commands=headed_commands)
    svg = render_v05_svg(_surface_with(plain, headed))
    assert 'd="M0 0L0 18Q0 20 2 20L4 20"' in svg
    assert 'd="M0 0L0 20L4 20"' in svg


def test_the_legend_key_of_a_none_terminal_is_the_plain_stroke():
    theme = _theme()
    theme["body"]["values"]["dependency-marker"] = {"type": "marker", "value": {"shape": "none", **TOKEN}}
    theme["body"]["roles"]["dependency"] = {**theme["body"]["roles"]["dependency"], "marker": "dependency-marker"}
    swatch = next(node for node in _legend_surface((("dependency", "Dependency"),), theme).primitives
                  if node.scene_id == "legend-swatch:dependency")
    assert swatch.kind == "Path" and swatch.marker_end is None and swatch.paint.stroke is not None


def test_svg_emits_no_marker_and_typst_and_tikz_draw_the_plain_path_and_lower_a_marker_to_a_shape():
    path, _ = _path("none", "none")
    headed, _ = _path("none", "triangle")
    surface = _surface_with(path)
    assert "marker-" not in render_v05_svg(surface)
    assert render_v05_typst(surface) and render_v05_tikz(surface)
    assert "marker-end" not in render_v05_typst(surface) and "marker-end" not in render_v05_tikz(surface)
    for render in (render_v05_typst, render_v05_tikz):
        assert "marker-end of scene-id" in render(_surface_with(headed))


def _surface_with(*paths):
    from datetime import date
    from chrona.presentation.scene.model import ScenePaint, SceneSurface, SurfaceScaleManifest
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 100, 0, 100)
    return SceneSurface("s", (), (), (), scale, tuple(replace(path, paint=path.paint or ScenePaint(None, "#000000", 1, (), 1))
                                                       for path in paths),
                        ScenePaint("#ffffff", None, None, (), 1), canvas_bounds=(0, 0, 1000, 1000))


@pytest.mark.parametrize("shape", sorted(SHAPES - {"none"}))
def test_every_other_shape_is_byte_identical_to_its_own_resolution(shape):
    path, _ = _path(shape, shape)
    expected = marker_geometry({"shape": shape, **TOKEN, "headLength": 6, "headWidth": 6, "attachmentOffset": 0})
    assert expected is not None
    assert path.marker_start == centred_on_route(expected, "source")
    assert path.marker_end == centred_on_route(expected, "target")


def test_none_validates_its_numbers_like_every_shape():
    assert marker_geometry({"shape": "none", **TOKEN}) is None
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        marker_geometry({"shape": "none", "headLength": 0, "headWidth": 8, "attachmentOffset": 0})
