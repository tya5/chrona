"""Both relation surfaces consume the global Layout route style (#1047)."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.network_routes import (
    _route_blockers, _terminal_blockers, complete_network_routes,
)
from chrona.presentation.layout.obstacles import ObstacleRect, obstacles_intersect
from chrona.presentation.layout.path_geometry import flatten_path
from chrona.presentation.layout.relation_style import curved_path_segments
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.surface_content import RelationPresentationFact
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.surface_pipeline import build_surface_input, compose_review_surface
from tests.unit.chrona.presentation.layout.test_network_routes import _edge, _rect, _theme
from tests.unit.chrona.presentation.layout.test_window_relation_completion import _request as _table_request
from tests.unit.chrona.presentation.scene.test_v05_builder import _theme as _base_theme


def _table_case(style: str | None = None):
    request = _table_request(containing=True)
    theme = deepcopy(_base_theme())
    theme["body"]["values"].update({
        "route-accent": {"type": "color", "value": "#c43d24"},
        "paper": {"type": "color", "value": "#f7f5ef"},
    })
    relation_role = theme["body"]["roles"][semantic_binding("dependency").scene_role]
    relation_role.update({"fill": "route-accent", "stroke": "route-accent"})
    theme["body"]["roles"]["background"]["fill"] = "paper"
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    fact = RelationPresentationFact(
        "dep", "object-1", "end", "object-6", "start", 0, None, "dependency"
    )
    request = replace(request, surface_content=replace(request.surface_content, relations=(fact,)))
    if style is not None:
        request = replace(request, layout_manifest=replace(request.layout_manifest, relation_style=style))
    return request


def _scene(request):
    value = build_surface_input(
        projection=request.projection,
        surface_content=request.surface_content,
        layout_manifest=request.layout_manifest,
        resolved_theme=request.theme_tokens.resolved_theme,
        font_metrics=request.font_metrics,
        measured_sources=request.measured_sources,
        capabilities=request.capabilities,
        icon_assets=request.icon_assets,
        visual_requests=request.visual_requests,
        fixed_lane_preflight=request.fixed_lane_preflight,
        capacity_short_sources=request.capacity_short_sources,
        declared_viewport=request.declared_viewport,
        auto_block_limit=request.auto_block_limit,
        previous_route_hints=request.previous_route_hints,
    )
    return compose_review_surface(value)


def test_curved_table_surface_keeps_route_skeleton_clears_marks_and_text_and_renders(tmp_path):
    from chrona.presentation.layout.surface_composer import compose_surface_layout

    request = _table_case("curved")
    layout = compose_surface_layout(request).placement
    relation = next(item for item in layout.relations if item.source_ref == "dep")

    assert len(relation.points) >= 4
    assert sum(command.kind == "quadratic" for command in relation.path_commands) == 2
    assert relation.style_fallback is None
    assert not any(item.startswith("I_LAYOUT_RELATION_STYLE_FALLBACK:") for item in layout.diagnostics)

    # Safety checks cover the changed curve ink. Endpoint hosts, the intervening
    # required mark, and required text must all remain clear of its conservative
    # stroke-inflated cover.
    arc_cover = curved_path_segments(relation.path_commands, stroke_width=1.0)
    for mark in layout.marks:
        bounds = mark.bounds
        obstacle = ObstacleRect(float(bounds.inline), float(bounds.block),
                                float(bounds.inline + bounds.inline_size),
                                float(bounds.block + bounds.block_size))
        assert all(not obstacles_intersect(segment, obstacle) for segment in arc_cover)
    for text in layout.text:
        bounds = text.bounds
        obstacle = ObstacleRect(float(bounds.inline), float(bounds.block),
                                float(bounds.inline + bounds.inline_size),
                                float(bounds.block + bounds.block_size))
        assert all(not obstacles_intersect(segment, obstacle) for segment in arc_cover)

    scene = _scene(request)
    scene_relation = next(item for item in scene.primitives
                          if item.source_kind == "relation" and item.source_ref == "dep")
    assert sum(command.kind == "quadratic" for command in scene_relation.path_commands) == 2
    svg = render_v05_svg(scene)
    # The renderer emits SVG command letters adjacent to the preceding command.
    assert "Q" in svg
    svg_path = tmp_path / "table-curved.svg"
    png_path = tmp_path / "table-curved.png"
    svg_path.write_text(svg, encoding="utf-8")
    resvg_py = pytest.importorskip("resvg_py")
    png = resvg_py.svg_to_bytes(svg_string=svg, dpi=96, skip_system_fonts=True)
    png_path.write_bytes(png)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert svg_path.stat().st_size > 0 and png_path.stat().st_size > 0
    assert 'stroke="#c43d24"' in svg
    image = pytest.importorskip("PIL.Image")
    from io import BytesIO
    pixels = image.open(BytesIO(png)).convert("RGB")
    assert len(pixels.getcolors(maxcolors=pixels.width * pixels.height) or ()) > 2


def test_omitted_and_explicit_orthogonal_table_surfaces_and_svg_are_identical():
    default_request = _table_case()
    explicit_request = _table_case("orthogonal")

    default_scene = _scene(default_request)
    explicit_scene = _scene(explicit_request)

    assert default_scene == explicit_scene
    assert render_v05_svg(default_scene) == render_v05_svg(explicit_scene)


def _network_routes(*, style=None, obstacle=None):
    ports = {
        "a": ((0.0, 20.0), (20.0, 20.0)),
        "b": ((100.0, 20.0), (120.0, 20.0)),
    }
    obstacles = ({} if obstacle is None else obstacle if isinstance(obstacle, dict)
                 else {"blocker": obstacle})
    kwargs = dict(
        edges=(_edge(),), ports=ports, obstacles=obstacles,
        subjects={key: DiagnosticSubject.project_object(key) for key in obstacles},
        bounds=_rect(0, 0, 150, 60), max_bends=4, max_detour_ratio=3.0,
        theme_tokens=_theme(),
    )
    if style is not None:
        kwargs["relation_style"] = style
    return complete_network_routes(**kwargs)


def test_network_route_style_curves_a_safe_two_turn_route_without_changing_skeleton():
    obstacle = _rect(55, 10, 65, 30)
    default, default_warnings = _network_routes(obstacle=obstacle)
    explicit, explicit_warnings = _network_routes(style="orthogonal", obstacle=obstacle)
    curved, curved_warnings = _network_routes(style="curved", obstacle=obstacle)

    assert default == explicit and default_warnings == explicit_warnings == ()
    baseline = default[0]
    route = curved[0]
    assert route.points == baseline.points
    assert sum(command.kind == "quadratic" for command in route.path_commands) == 2
    assert route.style_fallback is None and curved_warnings == ()

    blocker = ObstacleRect(55.0, 10.0, 65.0, 30.0)
    drawn = flatten_path(route.path_commands)
    assert not _route_blockers(drawn, 1.0, {"blocker": blocker}, source_id="a", target_id="b")
    assert not _terminal_blockers(route.points, route.path_commands, route.marker_start,
                                 route.marker_end, 1.0, {"blocker": blocker},
                                 source_id="a", target_id="b")


def test_network_curve_that_cannot_preserve_terminal_runs_has_one_typed_fallback():
    obstacle = _rect(55, 15, 65, 25)
    baseline, baseline_warnings = _network_routes(obstacle=obstacle)
    curved, curved_warnings = _network_routes(style="curved", obstacle=obstacle)
    route = curved[0]

    assert curved_warnings == baseline_warnings == ()
    assert route.points == baseline[0].points
    assert route.path_commands == baseline[0].path_commands
    assert route.style_fallback is not None
    assert route.style_fallback.reason == "terminal"
    assert route.style_fallback.diagnostic.startswith("I_LAYOUT_RELATION_STYLE_FALLBACK:")


def test_network_curve_clearance_fallback_preserves_required_node_and_orthogonal_route():
    # The small node is clear of the selected orthogonal route but intersects
    # its changed corner arc. The router must retain the admitted route rather
    # than emit a curved path through that required node.
    obstacles = {
        "route-detour": _rect(55, 10, 65, 30),
        "corner-node": _rect(20.5, 10.25, 20.75, 10.5),
    }
    baseline, _ = _network_routes(obstacle=obstacles)
    curved, warnings = _network_routes(style="curved", obstacle=obstacles)
    route = curved[0]

    assert warnings == ()
    assert route.points == baseline[0].points
    assert route.path_commands == baseline[0].path_commands
    assert route.style_fallback is not None
    assert route.style_fallback.reason == "clearance"


def test_scene_and_svg_render_an_s_curve_across_different_rows(tmp_path, monkeypatch):
    from tests.unit.chrona.presentation.scene import test_relation_rounded_corners as fixture

    manifest = fixture._manifest
    monkeypatch.setattr(fixture, "_manifest", lambda *args, **kwargs: replace(
        manifest(*args, **kwargs), relation_style="curved"))
    monkeypatch.setattr(fixture, "_theme", lambda: _contrasting_theme())
    relation = {"id": "dep", "from": {"object": "a", "endpoint": "start"},
                "to": {"object": "b", "endpoint": "end"}}
    surface, path = fixture._drawn(0, relation=relation)

    assert path.points[0][1] != path.points[-1][1]
    turns = []
    for first, corner, last in zip(path.points, path.points[1:], path.points[2:]):
        incoming = (corner[0] - first[0], corner[1] - first[1])
        outgoing = (last[0] - corner[0], last[1] - corner[1])
        turns.append(incoming[0] * outgoing[1] - incoming[1] * outgoing[0])
    assert len(turns) == 2 and turns[0] * turns[1] < 0
    assert sum(command.kind == "quadratic" for command in path.path_commands) == 2

    svg = render_v05_svg(surface)
    assert svg.count("Q") >= 2 and 'stroke="#c43d24"' in svg
    svg_path = tmp_path / "different-row-s-curve.svg"
    png_path = tmp_path / "different-row-s-curve.png"
    svg_path.write_text(svg, encoding="utf-8")
    resvg_py = pytest.importorskip("resvg_py")
    png = resvg_py.svg_to_bytes(svg_string=svg, dpi=96, skip_system_fonts=True)
    png_path.write_bytes(png)
    image = pytest.importorskip("PIL.Image")
    from io import BytesIO
    pixels = image.open(BytesIO(png)).convert("RGB")
    assert len(pixels.getcolors(maxcolors=pixels.width * pixels.height) or ()) > 2


def _contrasting_theme():
    theme = deepcopy(_base_theme())
    theme["body"]["values"].update({
        "route-accent": {"type": "color", "value": "#c43d24"},
        "paper": {"type": "color", "value": "#f7f5ef"},
    })
    relation_role = theme["body"]["roles"][semantic_binding("dependency").scene_role]
    relation_role.update({"fill": "route-accent", "stroke": "route-accent"})
    theme["body"]["roles"]["background"]["fill"] = "paper"
    return theme
