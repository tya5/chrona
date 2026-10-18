from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.dependency_network import (
    DependencyNetworkLayout, NetworkNodePlacement,
)
from chrona.presentation.layout.model import LayoutDecision, LayoutManifest, Rect
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.surface_quality import (
    GroupPlacement, MarkerGeometry, MarkPlacement, PathCommand, RelationPlacement, ShapePlacement,
    SlotPlacement, TextPlacement,
)
from chrona.presentation.layout.surface_legend import SurfaceLegendBatch
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.diagnostic_sources import (
    DiagnosticProvenance, DiagnosticSubject, PrimitiveProvenance,
)
from chrona.presentation.model.theme_paint import PaintFamily, resolve_theme_paint_witness
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.v05_builder import SceneBuildInput, project_review_surface
from tests.unit.chrona.presentation.scene.test_v05_builder import _theme, surface_content


def _rect(x, y, width, height):
    return Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))


def _text(placement_id, source_ref, content, x, y, slot_id, semantic_id):
    return TextPlacement(
        placement_id, source_ref, content, _rect(x, y, 40, 16), "groupHeader",
        baseline=(x, y + 12), lines=(content,), font_family="Test Sans", font_weight=400,
        font_size=12, line_height=14, font_asset_identity="sha256:test", slot_id=slot_id,
        semantic_id=semantic_id,
    )


def _scene_input(network_layout, network_nodes=(), theme=None):
    projection = SimpleNamespace(
        surface="dependency-network",
        network=SimpleNamespace(nodes=tuple(network_nodes), edges=()),
        items=(),
    )
    manifest_bounds = _rect(0, 0, 300, 200)
    decisions = [LayoutDecision("network-authored", "slot", manifest_bounds, "network")]
    if network_layout.legend is not None:
        decisions.append(LayoutDecision("legend-authored", "slot", manifest_bounds, "legend"))
    manifest = LayoutManifest(
        "review", "sha256:test", "horizontal", "horizontal", manifest_bounds,
        tuple(decisions),
    )
    return SceneBuildInput(
        projection, surface_content(), manifest, ThemeTokenView(theme or _theme()), {"svg": True}, network_layout,
    )


def test_dependency_network_scene_projects_completed_groups_nodes_routes_and_legend_verbatim():
    group_shape = ShapePlacement(
        "group-band:team-a", "team-a", "rect", _rect(5, 10, 190, 90), slot_id="network",
        paint_order=10, semantic_id="groupBand", visual_role="group-band",
    )
    normal_node = NetworkNodePlacement("task-a", 0, _rect(30, 45, 50, 20), (30, 55), (80, 55), False)
    container_node = NetworkNodePlacement(
        "group-team-a", 0, _rect(5, 10, 190, 90), (5, 10), (195, 100), False, is_container=True,
    )
    start = MarkerGeometry((PathCommand("move", ((0, 0),)), PathCommand("line", ((2, 1),))),
                          2, 2, 0, "stroke")
    end = MarkerGeometry((PathCommand("move", ((10, 0),)), PathCommand("line", ((8, 1),))),
                        2, 2, 0, "stroke")
    route = RelationPlacement(
        "edge-critical", "task-a:out", "task-b:in", points=((80, 55), (120, 55)),
        semantic_id="criticalEdge", path_commands=(PathCommand("move", ((80, 55),)),
                                                     PathCommand("line", ((120, 55),))),
        marker_start=start, marker_end=end, slot_id="network", source_ref="edge-source",
        from_instance_id="task-a", to_instance_id="task-b", paint_clip=None,
    )
    legend_slot = SlotPlacement("legend-completed", "legend", _rect(205, 15, 85, 35), "required")
    mark_part = SymbolPartPlacement((PathCommand("move", ((1, 1),)),
                                     PathCommand("line", ((5, 1),)),
                                     PathCommand("line", ((3, 5),))), paint_mode="fill")
    legend_mark = MarkPlacement(
        "legend-mark:critical", "critical-edge", _rect(210, 20, 8, 8), None, None,
        mark_shape="symbol", slot_id="legend-completed", symbol_parts=(mark_part,), theme_role="planned",
    )
    legend_shape = ShapePlacement(
        "legend-shape:critical", "critical-edge", "rect", _rect(220, 20, 8, 8),
        slot_id="legend-completed", semantic_id="legendEntry", visual_role="critical-edge",
        subjects=(DiagnosticSubject.project_object("task-a", "Task A"),),
        legend_paint=resolve_theme_paint_witness(ThemeTokenView(_theme()), "critical-edge", PaintFamily.SOLID),
    )
    legend_relation = RelationPlacement(
        "legend-route:critical", "swatch-start", "swatch-end", points=((230, 24), (240, 24)),
        semantic_id="criticalEdge", path_commands=(PathCommand("move", ((230, 24),)),
                                                     PathCommand("line", ((240, 24),))),
        slot_id="legend-completed", source_ref="critical-edge",
    )
    legend_text = _text("legend-label:critical", "critical-edge", "Critical", 245, 20,
                        "legend-completed", "legendLabel")
    legend = SurfaceLegendBatch(
        legend_slot, (legend_mark,), (legend_shape,), (legend_relation,), (legend_text,), (), legend_slot,
        diagnostic_provenance=(DiagnosticProvenance(
            "W_TEST_LEGEND", (DiagnosticSubject.project_object("task-a", "Task A"),)),),
    )
    layout = DependencyNetworkLayout(
        (container_node, normal_node),
        (_text("group-header:team-a", "team-a", "Team A", 10, 20, "network", "groupHeader"),),
        (route,), _rect(0, 0, 300, 150), shapes=(group_shape,),
        groups=(GroupPlacement("team-a", _rect(5, 10, 190, 90), _rect(5, 30, 190, 70)),), legend=legend,
    )
    value = _scene_input(layout, (container_node, normal_node))

    scene = project_review_surface(value)
    by_id = {item.scene_id: item for item in scene.primitives}

    assert len(scene.groups) == 1
    assert scene.groups[0].group_id == "team-a"
    assert scene.groups[0].header_bounds == (5.0, 30.0, 190.0, 70.0)
    assert scene.groups[0].content_bounds == (5.0, 10.0, 190.0, 90.0)
    assert by_id["group-band:team-a"].bounds == (5.0, 10.0, 190.0, 90.0)
    assert "network-node:group-team-a" not in by_id
    assert by_id["network-node:task-a"].bounds == (30.0, 45.0, 50.0, 20.0)
    projected_route = by_id["network-edge:edge-critical"]
    assert projected_route.source_ref == "edge-critical"
    assert projected_route.marker_start is start and projected_route.marker_end is end
    assert projected_route.path_commands == route.path_commands
    assert projected_route.points == route.points
    assert (projected_route.from_instance_id, projected_route.to_instance_id) == ("task-a", "task-b")
    assert projected_route.slot_id == "network"
    assert by_id["legend-mark:critical:part0"].bounds == (210.0, 20.0, 8.0, 8.0)
    assert by_id["legend-shape:critical"].bounds == (220.0, 20.0, 8.0, 8.0)
    assert by_id["legend-shape:critical"].paint is not None
    assert scene.diagnostic_provenance == legend.diagnostic_provenance
    assert scene.primitive_provenance == (PrimitiveProvenance(
        "network-node:task-a", (DiagnosticSubject.project_object("task-a"),)),
        PrimitiveProvenance("legend-shape:critical", (DiagnosticSubject.project_object("task-a", "Task A"),)))
    assert by_id["legend-route:critical"].path_commands == legend_relation.path_commands
    assert by_id["legend-label:critical"].text == "Critical"
    assert by_id["legend-label:critical"].slot_id == "legend-completed"
    assert [(slot.slot_id, slot.source, slot.bounds) for slot in scene.slots] == [
        ("network-authored", "network", (0.0, 0.0, 300.0, 200.0)),
        ("legend-completed", "legend", (205.0, 15.0, 85.0, 35.0)),
    ]
    assert semantic_binding("groupBand").purpose == by_id["group-band:team-a"].purpose


def test_dependency_network_scene_appends_intrinsic_legend_slot_when_no_authored_slot_exists():
    legend_slot = SlotPlacement("intrinsic-legend", "legend", _rect(210, 10, 80, 25))
    legend = SurfaceLegendBatch(legend_slot, (), (), (), (), (), legend_slot)
    layout = DependencyNetworkLayout((), (), (), _rect(0, 0, 300, 100), legend=legend)

    scene = project_review_surface(_scene_input(layout))

    assert [(slot.slot_id, slot.bounds) for slot in scene.slots] == [
        ("network-authored", (0.0, 0.0, 300.0, 200.0)),
        ("intrinsic-legend", (210.0, 10.0, 80.0, 25.0)),
    ]


def test_network_group_header_falls_back_to_body_ink_without_changing_semantic_purpose():
    theme = _theme()
    theme["body"]["roles"].pop("group-header")
    header = _text("group-header:team-a", "team-a", "Team A", 10, 20,
                   "network", "groupHeader")
    layout = DependencyNetworkLayout((), (header,), (), _rect(0, 0, 300, 100))

    scene = project_review_surface(_scene_input(layout, theme=theme))
    projected = next(item for item in scene.primitives if item.scene_id == "group-header:team-a")

    assert projected.purpose == semantic_binding("groupHeader").purpose
    assert projected.visual_role == "text"
