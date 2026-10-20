"""Actual network completion rejects ink introduced only by metro geometry."""
import pytest

from chrona.presentation.layout import network_routes
from chrona.presentation.layout.path_geometry import metro_orthogonal_path
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from tests.unit.chrona.presentation.layout.test_network_routes import _edge, _rect, _theme


@pytest.mark.parametrize("changed_kind", ["diagonal", "fillet"])
def test_network_completion_rejects_changed_ink_and_keeps_the_safe_selected_route(
        changed_kind, monkeypatch):
    skeleton = ((20.0, 20.0), (80.0, 20.0), (80.0, 140.0), (140.0, 140.0))
    # Hold only route selection fixed: the selected route clears the obstacle;
    # real terminal completion, style validation and fallback still run.
    monkeypatch.setattr(network_routes, "place_relation_route", lambda **_: skeleton)
    candidate = metro_orthogonal_path(skeleton, radius=20, start_run=10, end_run=10)
    current = candidate[0].points[0]
    point = None
    for command in candidate[1:]:
        endpoint = command.points[-1]
        if changed_kind == "diagonal" and command.kind == "line" and (
                current[0] != endpoint[0] and current[1] != endpoint[1]):
            point = ((current[0] + endpoint[0]) / 2, (current[1] + endpoint[1]) / 2)
            break
        if changed_kind == "fillet" and command.kind == "quadratic":
            control = command.points[0]
            point = tuple((current[axis] + 2 * control[axis] + endpoint[axis]) / 4
                          for axis in (0, 1))
            break
        current = endpoint
    assert point is not None
    obstacle = _rect(point[0] - 0.05, point[1] - 0.05, point[0] + 0.05, point[1] + 0.05)
    kwargs = dict(edges=(_edge(),),
        ports={"a": ((0.0, 20.0), skeleton[0]), "b": (skeleton[-1], (160.0, 140.0))},
        obstacles={"required": obstacle},
        subjects={"required": DiagnosticSubject.project_object("required")},
        bounds=_rect(0, 0, 200, 180), max_bends=4, max_detour_ratio=3,
        theme_tokens=_theme(), relation_corner_radius=20)
    baseline, baseline_warnings = network_routes.complete_network_routes(**kwargs)
    styled, styled_warnings = network_routes.complete_network_routes(**kwargs, relation_style="metro")
    assert baseline_warnings == styled_warnings == ()
    assert baseline[0].style_fallback is None
    assert styled[0].points == baseline[0].points
    assert styled[0].path_commands == baseline[0].path_commands
    assert styled[0].style_fallback.reason == "clearance"
    assert styled[0].style_fallback.requested == "metro"
