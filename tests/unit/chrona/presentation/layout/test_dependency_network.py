from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.dependency_network import compose_dependency_network_layout
from chrona.presentation.layout.model import LayoutError, Rect


def _network(nodes, edges):
    return SimpleNamespace(nodes=tuple(SimpleNamespace(object_id=item, title=item, order_key=(item,), critical=False, source_kind="primary") for item in nodes),
                           edges=tuple(SimpleNamespace(relation_id=relation, source_id=source, target_id=target,
                                                       source_endpoint="end", target_endpoint="start", critical=False)
                                       for relation, source, target in edges))


def test_network_layout_uses_longest_path_rank_and_stable_order():
    layout = compose_dependency_network_layout(_network(("b", "a", "c"), (("ab", "a", "b"), ("bc", "b", "c"))),
                                               bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                               node_inline=Decimal(60), node_block=Decimal(30))
    assert [(item.object_id, item.rank) for item in layout.nodes] == [("a", 0), ("b", 1), ("c", 2)]
    assert all(len(item.points) >= 2 for item in layout.relations)


def test_network_layout_rejects_a_cycle_before_inventing_geometry():
    with pytest.raises(LayoutError, match="E_LAYOUT_NETWORK_CYCLE"):
        compose_dependency_network_layout(_network(("a", "b"), (("ab", "a", "b"), ("ba", "b", "a"))),
                                          bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)),
                                          node_inline=Decimal(60), node_block=Decimal(30))
