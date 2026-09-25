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


def test_network_layout_uses_longest_path_rank_measured_labels_and_stable_order():
    layout = compose_dependency_network_layout(_network(("b", "a", "c"), (("ab", "a", "b"), ("bc", "b", "c"))),
                                               title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
                                               bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                               measured_sources=_measured("a", "b", "c"), flow_direction="horizontal")
    assert [(item.object_id, item.rank) for item in layout.nodes] == [("a", 0), ("b", 1), ("c", 2)]
    assert [item.placement_id for item in layout.text] == ["title", "network-label:a", "network-label:b", "network-label:c"]
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


def test_network_layout_rejects_title_overflow_before_scene_projection():
    with pytest.raises(LayoutError, match="E_LAYOUT_NETWORK_OVERFLOW"):
        compose_dependency_network_layout(_network(("a",), ()),
                                          title_bounds=Rect(Decimal(0), Decimal(0), Decimal(40), Decimal(20)),
                                          bounds=Rect(Decimal(0), Decimal(40), Decimal(400), Decimal(160)),
                                          measured_sources=_measured("a"), flow_direction="horizontal")
