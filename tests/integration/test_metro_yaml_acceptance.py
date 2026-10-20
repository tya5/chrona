"""The declared Layout YAML metro style reaches both real surface pipelines."""
from datetime import date

import pytest

from tests.integration.test_revision_route_corridor import _inputs, _project
from tests.integration.test_network_layout_acceptance import _fixture as network_fixture
from tests.support import synthetic_review as sr


def _routes(rendered):
    return tuple(item for item in rendered.surface.primitives
                 if ((item.source_kind == "relation" and not item.scene_id.startswith("legend-swatch:"))
                     or item.scene_id.startswith("network-edge:")))


def _diagonal_count(commands):
    current = None
    count = 0
    for command in commands:
        point = command.points[-1]
        if command.kind == "move":
            current = point
        elif command.kind == "line":
            count += current[0] != point[0] and current[1] != point[1]
            current = point
        else:
            current = point
    return count


def test_table_yaml_metro_completes_safe_chamfer_and_fillets(tmp_path):
    parts, layout = _inputs("first-fit")
    source = _project(date(2027, 1, 10))
    baseline_parts = {**parts, "layout": layout}
    metro_layout = {**layout, "relationRouting": {
        **layout["relationRouting"], "style": "metro"}}
    metro_parts = {**parts, "layout": metro_layout}

    baseline_dir, metro_dir = tmp_path / "table-baseline", tmp_path / "table-metro"
    baseline_dir.mkdir()
    metro_dir.mkdir()
    baseline = sr.render(baseline_dir, source, presentation=baseline_parts)
    metro = sr.render(metro_dir, source, presentation=metro_parts)

    base_routes, metro_routes = _routes(baseline), _routes(metro)
    assert len(base_routes) == len(metro_routes) == 1
    assert base_routes[0].points == metro_routes[0].points
    assert not any(command.kind == "quadratic" for command in base_routes[0].path_commands)
    diagonal_count = _diagonal_count(metro_routes[0].path_commands)
    quadratic_count = sum(command.kind == "quadratic" for command in metro_routes[0].path_commands)
    assert diagonal_count > 0 and quadratic_count == diagonal_count * 2
    receipts = [item for item in metro.scene.diagnostics
                if item.startswith("I_LAYOUT_RELATION_STYLE_FALLBACK:")]
    assert not receipts
    assert not [item for item in baseline.scene.diagnostics
                if item.startswith("I_LAYOUT_RELATION_STYLE_FALLBACK:")]
    assert metro.artifact.content.startswith(b"<svg")
    resvg_py = pytest.importorskip("resvg_py")
    png_path = tmp_path / "table-metro.png"
    png_path.write_bytes(resvg_py.svg_to_bytes(
        svg_string=metro.artifact.content.decode("utf-8"), dpi=96, skip_system_fonts=True))
    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_network_yaml_metro_completes_real_45_degree_route_instead_of_ignoring_style(tmp_path):
    parts, source = network_fixture()
    route_limits = {"maxBends": 4, "maxDetourRatio": 3}
    baseline_parts = {**parts, "layout": {**parts["layout"],
        "relationRouting": {**route_limits, "style": "orthogonal"}}}
    metro_parts = {**parts, "layout": {**parts["layout"],
        "relationRouting": {**route_limits, "style": "metro"}}}

    baseline_dir, metro_dir = tmp_path / "network-baseline", tmp_path / "network-metro"
    baseline_dir.mkdir()
    metro_dir.mkdir()
    baseline = sr.render(baseline_dir, source, presentation=baseline_parts)
    metro = sr.render(metro_dir, source, presentation=metro_parts)

    base_routes, metro_routes = _routes(baseline), _routes(metro)
    assert len(base_routes) == len(metro_routes) == 1
    assert base_routes[0].points == metro_routes[0].points
    assert _diagonal_count(base_routes[0].path_commands) == 0
    assert _diagonal_count(metro_routes[0].path_commands) == 1
    assert sum(command.kind == "quadratic" for command in metro_routes[0].path_commands) == 2
    current = None
    diagonal = None
    for command in metro_routes[0].path_commands:
        point = command.points[-1]
        if command.kind == "move":
            current = point
        elif command.kind == "line":
            if current[0] != point[0] and current[1] != point[1]:
                diagonal = current, point
            current = point
        else:
            current = point
    assert diagonal is not None
    assert abs(diagonal[1][0] - diagonal[0][0]) == pytest.approx(
        abs(diagonal[1][1] - diagonal[0][1]))
    assert not [item for item in metro.scene.diagnostics
                if item.startswith("I_LAYOUT_RELATION_STYLE_FALLBACK:")]
    assert metro.artifact.content.startswith(b"<svg")
    assert "Q" in metro.artifact.content.decode("utf-8")
