from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.dependency_network import compose_dependency_network_layout
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun


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
