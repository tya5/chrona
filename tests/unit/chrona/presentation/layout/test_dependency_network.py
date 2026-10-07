from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.dependency_network import compose_dependency_network_layout
from chrona.presentation.layout.dependency_network import compose_dependency_network_surface
from chrona.presentation.layout.model import LayoutDecision, LayoutError, LayoutManifest, Measurement, Rect, SlotHeading
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme


def _network(nodes, edges):
    return SimpleNamespace(nodes=tuple(SimpleNamespace(object_id=item, title=item, order_key=(item,), critical=False, source_kind="primary") for item in nodes),
                           edges=tuple(SimpleNamespace(relation_id=relation, source_id=source, target_id=target,
                                                       source_endpoint="end", target_endpoint="start", critical=False)
                                       for relation, source, target in edges))


def _measured(*ids):
    return MeasuredSources({}, {}, {
        "network.node.minInlineSize": Decimal(60), "network.node.minBlockSize": Decimal(30),
        "network.rank.gap": Decimal(12),
    }, {"title": (MeasuredTextRun(None, "Network", "heading", Decimal(80), Decimal(24), Decimal(20),
                                   "Test Sans", 700, 20.0, 1.2, "sha256:test"),),
        "network": tuple(MeasuredTextRun(item, item, "text", Decimal(20), Decimal(14), Decimal(11),
                                            "Test Sans", 400, 14.0, 1.0, "sha256:test") for item in ids)})


def test_network_layout_does_not_reopen_common_projection_or_view_authoring():
    source = Path(__import__("chrona.presentation.layout.dependency_network", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    assert all(fragment not in source for fragment in (
        "projection.window", ".axis", ".markers", ".shading", ".annotations", ".table_columns",
    ))


def test_network_nodes_complete_inside_strokes_without_changing_ports():
    class Theme:
        def optional_choice(self, role, prop, allowed):
            return "inside" if prop == "strokeAlign" else None

        def optional_number(self, role, prop):
            return Decimal(2) if prop == "strokeWidth" else None

        def optional_color(self, role, prop):
            return "#000000"

        def optional_pattern(self, role):
            return None

    kwargs = dict(title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                  bounds=Rect(Decimal(0), Decimal(40), Decimal(400), Decimal(160)),
                  measured_sources=_measured("a"), flow_direction="horizontal")
    network = _network(("a",), ())
    baseline = compose_dependency_network_layout(network, **kwargs)
    aligned = compose_dependency_network_layout(network, theme_tokens=Theme(), **kwargs)
    assert aligned.nodes == baseline.nodes
    assert len(aligned.aligned_strokes) == 1
    stroke = aligned.aligned_strokes[0]
    assert stroke.primitive_id == "network-node:a"
    assert stroke.clip.stroke_width == 4
    assert stroke.clip.outline == () and not stroke.clip.outside


def test_network_layout_uses_longest_path_rank_measured_labels_and_stable_order():
    layout = compose_dependency_network_layout(_network(("b", "a", "c"), (("ab", "a", "b"), ("bc", "b", "c"))),
                                               title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                                               bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                               measured_sources=_measured("a", "b", "c"), flow_direction="horizontal")
    assert [(item.object_id, item.rank) for item in layout.nodes] == [("a", 0), ("b", 1), ("c", 2)]
    assert [item.placement_id for item in layout.text] == ["title", "network-label:a", "network-label:b", "network-label:c"]
    assert [item.semantic_id for item in layout.text] == ["titleText", "networkLabel", "networkLabel", "networkLabel"]
    assert all(len(item.points) >= 2 for item in layout.relations)


def test_network_layout_advances_ranks_in_block_direction_for_vertical_writing():
    layout = compose_dependency_network_layout(_network(("a", "b"), (("ab", "a", "b"),)),
                                               title_bounds=Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(40)),
                                               bounds=Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(240)),
                                               measured_sources=_measured("a", "b"), flow_direction="vertical-lr")
    first, second = layout.nodes
    assert first.bounds.block < second.bounds.block
    assert first.output_port[1] == float(first.bounds.block + first.bounds.block_size)
    assert second.input_port[1] == float(second.bounds.block)


def test_network_layout_rejects_cycle_and_missing_measurement_before_geometry():
    with pytest.raises(LayoutError, match="E_LAYOUT_NETWORK_CYCLE"):
        compose_dependency_network_layout(_network(("a", "b"), (("ab", "a", "b"), ("ba", "b", "a"))),
                                          title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                                          bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                          measured_sources=_measured("a", "b"), flow_direction="horizontal")
    with pytest.raises(LayoutError, match="E_LAYOUT_NETWORK_MEASUREMENT"):
        compose_dependency_network_layout(_network(("a",), ()),
                                          title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                                          bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                          measured_sources=_measured(), flow_direction="horizontal")


def test_network_layout_grows_canvas_for_a_natural_title():
    layout = compose_dependency_network_layout(_network(("a",), ()),
                                              title_bounds=Rect(Decimal(0), Decimal(0), Decimal(40), Decimal(20)),
                                              bounds=Rect(Decimal(0), Decimal(40), Decimal(400), Decimal(160)),
                                              measured_sources=_measured("a"), flow_direction="horizontal")
    assert layout.canvas_bounds.inline_size >= Decimal(400)
    assert layout.canvas_bounds.block_size >= Decimal(200)
    assert layout.fit_warnings[0].code == "W_LAYOUT_VISIBLE_OVERFLOW"


def test_network_layout_completes_rect_pattern_on_each_exact_node_placement():
    class Theme:
        def optional_pattern(self, role):
            assert role == "network-node"
            return {
                "kind": "catalog", "ref": "starter:hatch",
                "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 45,
                "densityBasisPoints": 5000,
                "primitives": [{"kind": "rect", "x": 0, "y": 0,
                                "inlineSize": 8, "blockSize": 4}],
            }

    layout = compose_dependency_network_layout(
        _network(("a", "b"), (("ab", "a", "b"),)),
        title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
        bounds=Rect(Decimal(0), Decimal(40), Decimal(400), Decimal(200)),
        measured_sources=_measured("a", "b"), flow_direction="horizontal", theme_tokens=Theme(),
    )

    assert tuple(pattern.placement_id for pattern in layout.patterns) == tuple(
        node.placement_id for node in layout.nodes
    )
    assert all(pattern.pattern.region == node.bounds
               for pattern, node in zip(layout.patterns, layout.nodes, strict=True))


def test_network_text_placements_carry_the_measured_horizontal_scale():
    measured = _measured("a", "b")
    squeezed = replace(measured, run_measurements={key: tuple(replace(run, horizontal_scale=0.6) for run in runs)
                                                  for key, runs in measured.run_measurements.items()})
    layout = compose_dependency_network_layout(_network(("a", "b"), (("ab", "a", "b"),)),
                                               title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                                               bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                               measured_sources=squeezed, flow_direction="horizontal")
    assert {item.placement_id: item.horizontal_scale for item in layout.text} == {
        "title": 0.6, "network-label:a": 0.6, "network-label:b": 0.6}
    plain = compose_dependency_network_layout(_network(("a", "b"), (("ab", "a", "b"),)),
                                              title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                                              bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                              measured_sources=measured, flow_direction="horizontal")
    assert {item.horizontal_scale for item in plain.text} == {1.0}


def test_native_network_heading_reduces_graph_viewport_and_route_region():
    resolved = theme()
    tokens = ThemeTokenView(resolved)
    metrics = SimpleNamespace(content_identity="sha256:network-heading",
                               width=lambda text, size, **kwargs: len(text) * size / 2,
                               baseline=lambda top, size, line_height: top + size)
    decisions = (
        LayoutDecision("title-slot", "slot", Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(50)),
                       source="title", heading=SlotHeading("Document")),
        LayoutDecision("network-slot", "slot", Rect(Decimal(0), Decimal(50), Decimal(400), Decimal(200)),
                       source="network", heading=SlotHeading("Dependencies")),
    )
    manifest = LayoutManifest("test", "sha256:test", "horizontal", "horizontal",
                              Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(250)), decisions)
    measured = _measured("a", "b")
    # The aggregate measurement includes caption space; native title geometry does not.
    from chrona.presentation.layout.sources import SourceInput, measure_sources
    title_measurement = measure_sources({"title": SourceInput(("Network",), typography_role="heading")},
                                       resolved, font_metrics=metrics)
    measured = replace(measured,
                       inputs={**measured.inputs, "title": title_measurement.inputs["title"]},
                       measurements={**measured.measurements, "title": Measurement(
                           title_measurement.measurements["title"].min_inline,
                           title_measurement.measurements["title"].preferred_inline,
                           title_measurement.measurements["title"].max_inline,
                           title_measurement.measurements["title"].min_block + 30,
                           title_measurement.measurements["title"].preferred_block + 30,
                           title_measurement.measurements["title"].max_block + 30,
                           title_measurement.measurements["title"].first_baseline + 30,
                           title_measurement.measurements["title"].last_baseline + 30)},
                       run_measurements={**measured.run_measurements, "title": title_measurement.run_measurements["title"]})
    request = SurfaceLayoutRequest(
        projection=SimpleNamespace(network=_network(("a", "b"), (("ab", "a", "b"),))),
        surface_content=SimpleNamespace(slot_heading_text=()), layout_manifest=manifest,
        measured_sources=measured, theme_tokens=tokens, font_metrics=metrics)
    layout = compose_dependency_network_surface(request)
    by_id = {item.placement_id: item for item in layout.text}
    assert by_id["slot-heading:network-slot"].semantic_id == "slotHeading"
    assert by_id["title"].baseline[1] > float(measured.run_measurements["title"][0].baseline)
    assert by_id["title"].baseline[1] < float(measured.run_measurements["title"][0].baseline + 50)
    network_heading_bottom = by_id["slot-heading:network-slot"].bounds.block + by_id["slot-heading:network-slot"].bounds.block_size
    assert min(node.bounds.block for node in layout.nodes) >= network_heading_bottom
    assert layout.relations
    assert all(point[1] >= network_heading_bottom for relation in layout.relations for point in relation.points)
    assert layout.canvas_bounds == manifest.viewport


def test_network_wrapper_keeps_native_title_on_raw_runs_without_aggregate_measurement():
    resolved = theme()
    metrics = SimpleNamespace(content_identity="sha256:transformed-network-title",
                               width=lambda text, size, **kwargs: len(text) * size / 2,
                               baseline=lambda top, size, line_height: top + size)
    decisions = (
        LayoutDecision("title-slot-id", "slot", Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(50)),
                       source="title", heading=SlotHeading("Caption")),
        LayoutDecision("graph-slot-id", "slot", Rect(Decimal(0), Decimal(50), Decimal(400), Decimal(200)),
                       source="network"),
    )
    manifest = LayoutManifest("test", "sha256:test", "horizontal", "horizontal",
                              Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(250)), decisions)
    measured = _measured("object-1")
    transformed = replace(measured.run_measurements["title"][0], content="NETWORK TITLE")
    measured = replace(measured, measurements={}, inputs={},
                       run_measurements={**measured.run_measurements, "title": (transformed,)})
    request = SurfaceLayoutRequest(
        projection=SimpleNamespace(network=_network(("object-1",), ())),
        surface_content=SimpleNamespace(slot_heading_text=()), layout_manifest=manifest,
        measured_sources=measured, theme_tokens=ThemeTokenView(resolved), font_metrics=metrics)

    layout = compose_dependency_network_surface(request)
    by_id = {item.placement_id: item for item in layout.text}
    assert set(by_id) == {"slot-heading:title-slot-id", "title", "network-label:object-1"}
    assert by_id["title"].content == "NETWORK TITLE"
    assert by_id["title"].semantic_id == "titleText"
    assert by_id["title"].source_ref == "title" and by_id["title"].slot_id == "title-slot-id"
    assert by_id["network-label:object-1"].slot_id == "graph-slot-id"
    assert layout.nodes[0].slot_id == "graph-slot-id"
    assert by_id["slot-heading:title-slot-id"].content == "Caption"
    assert by_id["slot-heading:title-slot-id"].semantic_id == "slotHeading"
    assert by_id["slot-heading:title-slot-id"].slot_id == "title-slot-id"
    assert by_id["title"].bounds.block >= (
        by_id["slot-heading:title-slot-id"].bounds.block
        + by_id["slot-heading:title-slot-id"].bounds.block_size)


@pytest.mark.parametrize("direction", ("horizontal", "vertical-lr", "vertical-rl"))
def test_title_caption_reserves_only_its_own_slot_not_graph_or_routes(direction):
    resolved = theme()
    metrics = SimpleNamespace(content_identity="sha256:own-slot-caption",
                               width=lambda text, size, **kwargs: len(text) * size / 2,
                               baseline=lambda top, size, line_height: top + size)
    decisions = (
        LayoutDecision("title", "slot", Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(60)),
                       source="title"),
        LayoutDecision("network", "slot", Rect(Decimal(0), Decimal(60), Decimal(400), Decimal(240)),
                       source="network"),
    )
    manifest = LayoutManifest("test", "sha256:test", "horizontal", direction,
                              Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(300)), decisions)
    measured = _measured("a", "b", "c")
    graph = _network(("a", "b", "c"), (("ab", "a", "b"), ("bc", "b", "c")))
    request = SurfaceLayoutRequest(
        projection=SimpleNamespace(network=graph), surface_content=SimpleNamespace(slot_heading_text=()),
        layout_manifest=manifest, measured_sources=measured,
        theme_tokens=ThemeTokenView(resolved), font_metrics=metrics)
    plain = compose_dependency_network_surface(request)
    core = compose_dependency_network_layout(
        graph, title_bounds=decisions[0].bounds, bounds=decisions[1].bounds,
        measured_sources=measured, flow_direction=direction,
        canvas_bounds=manifest.viewport, theme_tokens=request.theme_tokens)
    # Without declarations, the wrapper preserves every native completed field.
    assert plain == core
    headed_manifest = replace(manifest, decisions=(
        replace(decisions[0], heading=SlotHeading("Document")), decisions[1]))
    headed = compose_dependency_network_surface(replace(request, layout_manifest=headed_manifest))
    assert headed.nodes == plain.nodes
    assert headed.relations == plain.relations
    assert headed.canvas_bounds == plain.canvas_bounds
    assert headed.fit_warnings == plain.fit_warnings
    assert headed.patterns == plain.patterns
    assert headed.texture == plain.texture
    assert headed.aligned_strokes == plain.aligned_strokes
    assert tuple(item for item in headed.text if item.source_ref != "title") == tuple(
        item for item in plain.text if item.source_ref != "title")
    title = next(item for item in headed.text if item.placement_id == "title")
    caption = next(item for item in headed.text if item.placement_id == "slot-heading:title")
    assert title.bounds.block >= caption.bounds.block + caption.bounds.block_size
