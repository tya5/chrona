"""Transit/metro routing is an opt-in, geometry-checked Layout style (#1047)."""
from __future__ import annotations

from dataclasses import replace

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.network_routes import complete_network_routes
from chrona.presentation.layout.path_geometry import metro_orthogonal_path
from chrona.presentation.layout.obstacles import ObstacleRect, obstacles_intersect
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.relation_style import complete_relation_style
from chrona.presentation.layout.surface_quality import PathCommand, RelationPlacement
from chrona.presentation.renderers.v05_svg import render_v05_svg
from tests.unit.chrona.presentation.layout.test_relation_entry_profile import (
    SOURCES, THEME, with_routing,
)
from tests.unit.chrona.presentation.layout.test_region_frame_profile import MEASUREMENTS
from tests.unit.chrona.presentation.layout.test_network_routes import _edge, _rect, _theme


def _profile_style(style):
    """Exercise the public YAML profile decoder and Layout solver, not a string stub."""
    profile = with_routing({"maxBends": 4, "maxDetourRatio": 3, "style": style})
    resolved = resolve_layout_profile(profile, available_sources=SOURCES, theme=THEME)
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=900,
                            measurements=MEASUREMENTS)
    assert manifest.relation_style == style
    return manifest.relation_style


def _quadratic_count(commands):
    return sum(command.kind == "quadratic" for command in commands)


def _diagonal_line_count(commands):
    count = 0
    current = None
    for command in commands:
        if command.kind == "move":
            current = command.points[-1]
        elif command.kind == "line":
            point = command.points[-1]
            count += current[0] != point[0] and current[1] != point[1]
            current = point
        else:
            current = command.points[-1]
    return count


@pytest.mark.parametrize(("radius", "expect_arcs", "diagonals", "quadratics"),
                         [(None, True, 4, 8), (0, False, 3, 0), (4, True, 4, 8)])
def test_yaml_profile_style_completes_real_table_scene_svg_and_png(
        radius, expect_arcs, diagonals, quadratics, tmp_path, monkeypatch):
    from tests.unit.chrona.presentation.scene import test_relation_rounded_corners as fixture

    style = _profile_style("metro")
    original_manifest = fixture._manifest
    monkeypatch.setattr(fixture, "_manifest", lambda *args, **kwargs: replace(
        original_manifest(*args, **kwargs), relation_style=style))
    monkeypatch.setattr(fixture, "_theme", lambda: _contrast_theme())

    # The fixture supplies a realistic table projection/measurement set; the
    # style itself comes from a decoded YAML profile solved through Layout.
    relation_fact = {"id": "dep", "from": {"object": "a", "endpoint": "start"},
                     "to": {"object": "b", "endpoint": "end"}}
    padded_window = (fixture.D(2026, 1, 15), fixture.D(2026, 3, 1))
    surface, relation = fixture._drawn(radius, relation=relation_fact, window=padded_window)
    assert _diagonal_line_count(relation.path_commands) == diagonals
    assert _quadratic_count(relation.path_commands) == quadratics

    head = relation.marker_start.head_length
    tail = relation.marker_end.head_length
    assert abs(relation.points[1][0] - relation.points[0][0]) + abs(
        relation.points[1][1] - relation.points[0][1]) >= head
    assert abs(relation.points[-1][0] - relation.points[-2][0]) + abs(
        relation.points[-1][1] - relation.points[-2][1]) >= tail

    svg = render_v05_svg(surface)
    assert "L" in svg and 'stroke="#c43d24"' in svg
    assert ("Q" in svg) is expect_arcs
    svg_path = tmp_path / f"metro-radius-{radius if radius is not None else 'absent'}.svg"
    png_path = tmp_path / f"metro-radius-{radius if radius is not None else 'absent'}.png"
    svg_path.write_text(svg, encoding="utf-8")
    resvg_py = pytest.importorskip("resvg_py")
    png_path.write_bytes(resvg_py.svg_to_bytes(svg_string=svg, dpi=96, skip_system_fonts=True))
    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def _contrast_theme():
    from tests.unit.chrona.presentation.layout.test_relation_style_surfaces import _contrasting_theme
    return _contrasting_theme()


def _network(style, *, radius=None):
    obstacle = _rect(55, 10, 65, 30)
    return complete_network_routes(
        (_edge(),), ports={
            "a": ((0.0, 20.0), (20.0, 20.0)),
            "b": ((100.0, 20.0), (120.0, 20.0)),
        }, obstacles={"detour": obstacle}, subjects={}, bounds=_rect(0, 0, 150, 60),
        max_bends=4, max_detour_ratio=3.0, theme_tokens=_theme(),
        relation_style=style,
        relation_corner_radius=None if radius is None else float(radius),
    )


@pytest.mark.parametrize(("radius", "expected_arcs"), [(None, 4), (0, 0), (2, 4)])
def test_yaml_profile_metro_reaches_network_route_completion_with_terminal_runs(radius, expected_arcs):
    baseline, baseline_warnings = _network("orthogonal")
    style = _profile_style("metro")
    routes, warnings = _network(style, radius=radius)
    relation = routes[0]

    assert warnings == baseline_warnings == ()
    assert relation.points == baseline[0].points
    assert relation.style_fallback is None
    assert _diagonal_line_count(relation.path_commands) == 2
    assert _quadratic_count(relation.path_commands) == expected_arcs
    assert abs(relation.path_commands[1].points[-1][0] - relation.points[0][0]) + abs(
        relation.path_commands[1].points[-1][1] - relation.points[0][1]) >= relation.marker_start.head_length
    assert abs(relation.points[-1][0] - relation.path_commands[-2].points[-1][0]) + abs(
        relation.points[-1][1] - relation.path_commands[-2].points[-1][1]) >= relation.marker_end.head_length


def test_default_and_curved_profile_styles_keep_their_original_surface_geometry(monkeypatch):
    from tests.unit.chrona.presentation.scene import test_relation_rounded_corners as fixture

    original_manifest = fixture._manifest
    default_surface, default_path = fixture._drawn(None)
    monkeypatch.setattr(fixture, "_manifest", lambda *args, **kwargs: replace(
        original_manifest(*args, **kwargs), relation_style=_profile_style("orthogonal")))
    orthogonal_surface, orthogonal_path = fixture._drawn(None)
    assert orthogonal_surface == default_surface
    assert orthogonal_path == default_path

    monkeypatch.setattr(fixture, "_manifest", lambda *args, **kwargs: replace(
        original_manifest(*args, **kwargs), relation_style=_profile_style("curved")))
    curved_surface, curved_path = fixture._drawn(None)
    assert curved_path.points == default_path.points
    assert _diagonal_line_count(curved_path.path_commands) == 0
    assert _quadratic_count(curved_path.path_commands) > 0
    assert _diagonal_line_count(default_path.path_commands) == 0


@pytest.mark.parametrize("blocked_kind", ["diagonal", "fillet"])
def test_changed_diagonal_or_fillet_collision_falls_back_to_original_skeleton(blocked_kind):
    points = ((0.0, 0.0), (0.0, 40.0), (40.0, 40.0), (40.0, 0.0))
    baseline = RelationPlacement("r", "a", "b", points)
    candidate = metro_orthogonal_path(points, radius=4.0)
    if blocked_kind == "diagonal":
        # Select an inserted diagonal by locating line commands between the
        # two turn clusters; its middle is strictly outside the old skeleton.
        current = None
        diagonal = None
        for item in candidate:
            point = item.points[-1]
            if item.kind == "move":
                current = point
            elif item.kind == "line":
                if current[0] != point[0] and current[1] != point[1]:
                    diagonal = (current, point)
                    break
                current = point
            else:
                current = point
        assert diagonal is not None
        a, b = diagonal
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        obstacle = ObstacleRect(center[0] - .1, center[1] - .1, center[0] + .1, center[1] + .1)
        def rejects(_placement, cover):
            return "clearance" if any(obstacles_intersect(segment, obstacle) for segment in cover) else None
    else:
        quadratic = next(item for item in candidate if item.kind == "quadratic")
        start = next(item.points[-1] for item in reversed(candidate[:candidate.index(quadratic)])
                     if item.kind in {"line", "move"})
        control, end = quadratic.points
        center = ((start[0] + 2 * control[0] + end[0]) / 4,
                  (start[1] + 2 * control[1] + end[1]) / 4)
        obstacle = ObstacleRect(center[0] - .1, center[1] - .1, center[0] + .1, center[1] + .1)
        def rejects(_placement, cover):
            return "clearance" if any(obstacles_intersect(segment, obstacle) for segment in cover) else None
    result, _ = complete_relation_style(baseline, style="metro", stroke_width=1.0,
        start_run=2.0, end_run=2.0, recovery=False, reject=rejects, join_radius=4.0)
    assert result.points == points
    assert result.path_commands == ()
    assert result.style_fallback is not None and result.style_fallback.reason == "clearance"


def test_metro_retains_mandatory_terminal_runs_and_straight_routes():
    points = ((0.0, 0.0), (0.0, 30.0), (40.0, 30.0))
    commands = metro_orthogonal_path(points, radius=4.0, start_run=6.0, end_run=7.0)
    assert commands[0].kind == "move" and commands[0].points == (points[0],)
    assert commands[-1].kind == "line" and commands[-1].points == (points[-1],)
    # The selected terminal stubs keep their required lengths; the jointly
    # budgeted cut/fillet consumes only the interior of the remaining leg.
    assert commands[1].points[-1] == pytest.approx((0.0, 6.0))
    assert abs(commands[-1].points[-1][0] - commands[-2].points[-1][0]) >= 7.0
    straight = ((0.0, 0.0), (40.0, 0.0))
    assert metro_orthogonal_path(straight, radius=4.0) == (
        PathCommand("move", (straight[0],)), PathCommand("line", (straight[-1],)))


