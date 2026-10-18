from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.network_routes import complete_network_routes
from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.render_progress import RenderProgress
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.scene.test_v05_builder import _theme as _scene_theme
from tests.unit.chrona.presentation.scene.test_v05_builder import _theme


def _rect(x1, y1, x2, y2):
    return Rect(Decimal(str(x1)), Decimal(str(y1)), Decimal(str(x2 - x1)), Decimal(str(y2 - y1)))


def _edge(relation_id="edge-a", source="a", target="b", *, critical=False):
    return SimpleNamespace(relation_id=relation_id, source_id=source, target_id=target,
                           source_endpoint="end", target_endpoint="start", critical=critical)


def _theme(*, marker_shape="triangle", head_length=10, head_width=10):
    result = _theme_source()
    result["body"]["values"]["dependency-marker"]["value"].update(
        shape=marker_shape, headLength=head_length, headWidth=head_width, attachmentOffset=1,
    )
    result["body"]["values"].update({
        "network-stroke": {"type": "number", "value": 1},
        "critical-stroke": {"type": "number", "value": 3},
        "network-opacity": {"type": "number", "value": "0.7"},
        "critical-opacity": {"type": "number", "value": "0.9"},
    })
    result["body"]["roles"]["network-edge"].update(
        strokeWidth="network-stroke", opacity="network-opacity")
    result["body"]["roles"]["critical-edge"].update(
        strokeWidth="critical-stroke", opacity="critical-opacity")
    return ThemeTokenView(result)


def _theme_source():
    # Reuse the repository's complete valid semantic test Theme, then specialize
    # the two network relation roles for these geometry-focused fixtures.
    return _scene_theme()


def _run(edges, *, ports=None, obstacles=None, theme=None, max_bends=4,
         max_detour_ratio=3.0, progress=None):
    ports = ports or {
        "a": ((0.0, 20.0), (20.0, 20.0)),
        "b": ((100.0, 20.0), (120.0, 20.0)),
    }
    return complete_network_routes(
        edges, ports=ports, obstacles=obstacles or {}, subjects={
            key: DiagnosticSubject.project_object(key, f"Node {key}")
            for key in (obstacles or {})
        }, bounds=_rect(0, 0, 150, 60), max_bends=max_bends,
        max_detour_ratio=max_detour_ratio, theme_tokens=theme, progress=progress,
    )


def test_network_route_completes_stable_direction_markers_and_role_specific_paint_identity():
    tokens = _theme()
    edges = (_edge("ordinary"), _edge("critical", critical=True))
    ports = {
        "a": ((0.0, 15.0), (20.0, 15.0)),
        "b": ((100.0, 15.0), (120.0, 15.0)),
        "c": ((0.0, 40.0), (20.0, 40.0)),
        "d": ((100.0, 40.0), (120.0, 40.0)),
    }
    routes, warnings = _run(edges, ports=ports, theme=tokens)

    ordinary, critical = routes
    assert not warnings
    assert ordinary.relation_id == "ordinary"
    assert ordinary.semantic_id == "networkEdge"
    assert ordinary.from_instance_id == "a" and ordinary.to_instance_id == "b"
    assert ordinary.source_port_id == "a:output" and ordinary.target_port_id == "b:input"
    assert ordinary.points == ((20.0, 15.0), (100.0, 15.0))
    assert ordinary.path_commands[0].kind == "move"
    assert tuple(item.kind for item in ordinary.path_commands[1:]) == ("line",)
    assert ordinary.marker_start is not None and ordinary.marker_end is not None
    source_outline = project_marker_outline(ordinary.marker_start, side="start", points=ordinary.points,
                                           path_commands=ordinary.path_commands, stroke_width=1)
    target_outline = project_marker_outline(ordinary.marker_end, side="end", points=ordinary.points,
                                           path_commands=ordinary.path_commands, stroke_width=1)
    assert max(point[0] for command in source_outline for point in command.points) == pytest.approx(21)
    assert min(point[0] for command in target_outline for point in command.points) == pytest.approx(91)
    assert critical.semantic_id == "criticalEdge"
    assert critical.marker_start is not None and critical.marker_end is not None
    critical_outline = project_marker_outline(critical.marker_start, side="start", points=critical.points,
                                              path_commands=critical.path_commands, stroke_width=3)
    assert max(point[0] for command in critical_outline for point in command.points) == pytest.approx(23)


def test_network_route_with_no_edges_does_not_resolve_unused_theme_roles():
    class NoRoleTheme:
        def __getattr__(self, name):
            raise AssertionError(f"unexpected Theme lookup: {name}")

    routes, warnings = _run((), theme=NoRoleTheme())

    assert routes == ()
    assert warnings == ()


def test_network_route_avoids_unrelated_node_using_stroke_aware_obstacle_search():
    obstacle = _rect(55, 15, 65, 25)
    routes, warnings = _run((_edge(),), obstacles={"blocker": obstacle}, theme=_theme())

    route = routes[0]
    assert not warnings
    assert len(route.points) > 2
    assert route.points[0] == (20.0, 20.0) and route.points[-1] == (100.0, 20.0)
    assert route.semantic_id == semantic_binding("networkEdge").semantic_id


def test_network_group_endpoint_keeps_the_layout_completed_container_port():
    group_port = (125.0, 35.0)
    edge = _edge("group-edge", source="group-a", target="b")
    routes, warnings = _run(
        (edge,),
        ports={"group-a": ((110.0, 20.0), group_port),
               "b": ((80.0, 35.0), (70.0, 35.0))},
        obstacles={"group-a": _rect(110, 10, 130, 60), "b": _rect(70, 25, 90, 45)},
        theme=None,
    )

    assert not warnings
    assert routes[0].points[0] == group_port
    assert routes[0].from_instance_id == "group-a"
    assert routes[0].source_port_id == "group-a:output"


def test_search_exhaustion_keeps_direct_path_and_reports_the_actual_crossing_subject():
    obstacle = _rect(50, 0, 55, 60)
    routes, warnings = _run((_edge(),), obstacles={"barrier": obstacle}, theme=_theme())

    assert len(routes) == 1
    assert routes[0].points == ((20.0, 20.0), (100.0, 20.0))
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.code == "W_LAYOUT_ROUTE_FALLBACK"
    assert warning.failure_kind == "route-search"
    assert warning.behaviour == "direct-path-crosses-node"
    assert warning.subjects == (DiagnosticSubject.project_object("barrier", "Node barrier"),)


def test_out_of_bounds_endpoint_keeps_direct_visible_fallback_and_names_bounds_failure():
    routes, warnings = _run(
        (_edge(),),
        ports={"a": ((-5.0, 20.0), (-5.0, 20.0)),
               "b": ((100.0, 20.0), (120.0, 20.0))},
        theme=None,
    )

    assert routes[0].points == ((-5.0, 20.0), (100.0, 20.0))
    assert len(warnings) == 1
    assert warnings[0].failure_kind == "route-bounds"
    assert warnings[0].behaviour == "direct-path-visible-overflow"
    assert not warnings[0].subjects


def test_oversized_terminal_ink_triggers_one_truthful_visible_fallback_warning():
    routes, warnings = _run(
        (_edge(),), obstacles={"nearby": _rect(14, 15, 18, 25)},
        theme=_theme(head_length=30, head_width=24),
    )

    assert len(routes) == 1
    assert routes[0].points == ((20.0, 20.0), (100.0, 20.0))
    assert routes[0].marker_start is not None
    assert len(warnings) == 1
    assert warnings[0].failure_kind == "route-terminal-obstacle-crossing"
    assert warnings[0].behaviour == "direct-path-crosses-node"
    assert warnings[0].subjects[0].source_ref == "/objects/nearby"


def test_quality_failure_falls_back_once_and_explicit_none_terminals_remain_absent():
    # The obstacle forces a detour; a zero-bend ceiling makes the original
    # route fail quality, while its visible direct fallback crosses that node.
    routes, warnings = _run(
        (_edge(),), obstacles={"blocker": _rect(55, 15, 65, 25)},
        theme=_theme(), max_bends=0,
    )
    assert routes[0].points == ((20.0, 20.0), (100.0, 20.0))
    assert len(warnings) == 1
    assert warnings[0].failure_kind == "route-quality-limit"
    assert warnings[0].behaviour == "direct-path-crosses-node"

    no_terminal = _run((_edge(),), theme=_theme(marker_shape="none"))[0][0]
    assert no_terminal.marker_start is None and no_terminal.marker_end is None
    synthetic = _run((_edge(),), theme=None)[0][0]
    assert synthetic.marker_start is None and synthetic.marker_end is None
    assert synthetic.semantic_id == "networkEdge"


def test_progress_counts_complete_only_after_each_network_edge_finishes():
    events = []
    observer = RenderProgress(events.append)
    routes, warnings = _run((_edge("one"), _edge("two", source="c", target="d")),
                            progress=observer, theme=_theme(), ports={
                                "a": ((0.0, 20.0), (20.0, 20.0)),
                                "b": ((100.0, 20.0), (120.0, 20.0)),
                                "c": ((0.0, 40.0), (20.0, 40.0)),
                                "d": ((100.0, 40.0), (120.0, 40.0)),
                            })

    assert len(routes) == 2 and not warnings
    assert [(event.completed, event.total, event.pass_name) for event in events] == [
        (0, 2, "network"), (1, 2, "network"), (2, 2, "network"),
    ]


def test_invalid_theme_geometry_error_is_not_converted_to_a_route_fallback():
    class BrokenTheme:
        def number(self, role, property_name):
            raise ValueError("E_THEME_TOKEN_TYPE: broken route stroke")

    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        _run((_edge(),), theme=BrokenTheme())

