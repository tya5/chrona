from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.network_group_bands import place_network_bands
from chrona.presentation.model.projection import DependencyNetworkNode


def _node(identity, *, parent=None, group=False):
    return DependencyNetworkNode(identity, identity, (identity,), False, "primary",
                                 is_container=group, container_id=parent)


def _place(nodes, horizontal, *, member_gap=Decimal(16)):
    return place_network_bands(
        nodes, ranks={node.object_id: int(node.object_id in {"b", "c"}) for node in nodes},
        sizes={node.object_id: (Decimal(80), Decimal(40)) for node in nodes},
        insets={node.object_id: (Decimal(8), Decimal(8)) for node in nodes},
        bounds=Rect(Decimal(0), Decimal(0), Decimal(500), Decimal(400)),
        gap=Decimal(16), member_gap=member_gap, horizontal=horizontal)


def _contains(outer, inner):
    return (outer.inline <= inner.inline and outer.block <= inner.block
            and outer.inline + outer.inline_size >= inner.inline + inner.inline_size
            and outer.block + outer.block_size >= inner.block + inner.block_size)


@pytest.mark.parametrize("horizontal", (False, True))
def test_nested_and_unrelated_containers_have_closed_disjoint_bands(horizontal):
    nodes = (_node("p", group=True), _node("q", parent="p", group=True),
             _node("a", parent="q"), _node("b", parent="p"),
             _node("z", group=True), _node("c", parent="z"))
    boxes, groups = _place(nodes, horizontal)
    by_id = {group.group_id: group for group in groups}
    assert boxes.keys() == {node.object_id for node in nodes}
    assert by_id.keys() == {"p", "q", "z"}
    for node in nodes:
        if node.container_id is not None:
            assert _contains(by_id[node.container_id].content_bounds, boxes[node.object_id])
    for group in groups:
        assert _contains(boxes[group.group_id], group.header_bounds)
        assert _contains(boxes[group.group_id], group.content_bounds)
    p, z = boxes["p"], boxes["z"]
    assert ((p.block + p.block_size <= z.block) if horizontal
            else (p.inline + p.inline_size <= z.inline))
    assert _place(tuple(reversed(nodes)), horizontal) == (boxes, groups)


@pytest.mark.parametrize("horizontal", (False, True))
def test_empty_selected_group_retains_header_and_empty_content_area(horizontal):
    boxes, groups = _place((_node("empty", group=True),), horizontal)
    assert groups[0].group_id == "empty"
    assert groups[0].content_bounds.inline_size > 0
    assert groups[0].content_bounds.block_size > 0
    assert _contains(boxes["empty"], groups[0].header_bounds)
    assert _contains(boxes["empty"], groups[0].content_bounds)


@pytest.mark.parametrize("horizontal", (False, True))
def test_ordinary_nodes_keep_rank_packing_without_containers(horizontal):
    boxes, groups = _place((_node("a"), _node("b"), _node("c")), horizontal)
    assert groups == ()
    assert boxes["a"] == Rect(Decimal(16), Decimal(16), Decimal(80), Decimal(40))
    assert boxes["b"] == (Rect(Decimal(112), Decimal(16), Decimal(80), Decimal(40)) if horizontal
                           else Rect(Decimal(16), Decimal(72), Decimal(80), Decimal(40)))
    assert boxes["c"] == (Rect(Decimal(112), Decimal(72), Decimal(80), Decimal(40)) if horizontal
                           else Rect(Decimal(112), Decimal(72), Decimal(80), Decimal(40)))


@pytest.mark.parametrize("horizontal", (False, True))
def test_member_gap_changes_only_secondary_axis_separation(horizontal):
    nodes = (_node("a"), _node("b"), _node("c"))
    legacy = _place(nodes, horizontal)
    explicit_same = _place(nodes, horizontal, member_gap=Decimal(16))
    compact = _place(nodes, horizontal, member_gap=Decimal(0))
    assert legacy == explicit_same
    legacy_boxes, _ = legacy
    compact_boxes, _ = compact
    # The second rank stays on the same primary coordinate while same-rank
    # members close together on the orthogonal axis.
    if horizontal:
        assert compact_boxes["b"].inline == legacy_boxes["b"].inline
        assert compact_boxes["b"].block == Decimal(0)
        assert compact_boxes["c"].block == compact_boxes["b"].block + Decimal(40)
    else:
        assert compact_boxes["b"].block == legacy_boxes["b"].block
        assert compact_boxes["b"].inline == Decimal(0)
        assert compact_boxes["c"].inline == compact_boxes["b"].inline + Decimal(80)


@pytest.mark.parametrize("horizontal", (False, True))
def test_member_gap_separates_nested_groups_and_headers_independently(horizontal):
    nodes = (_node("p", group=True), _node("q", parent="p", group=True),
             _node("a", parent="q"), _node("b", group=True), _node("c", parent="b"))
    legacy = _place(nodes, horizontal)
    explicit_same = _place(nodes, horizontal, member_gap=Decimal(16))
    assert legacy == explicit_same
    zero_gap, groups = _place(nodes, horizontal, member_gap=Decimal(0))
    assert set(zero_gap) == {node.object_id for node in nodes}
    assert {group.group_id for group in groups} == {"p", "q", "b"}
    for group in groups:
        assert _contains(zero_gap[group.group_id], group.header_bounds)
        assert _contains(zero_gap[group.group_id], group.content_bounds)


@pytest.mark.parametrize("nodes", ((_node("a", parent="missing"),),
                                   (_node("a", parent="a", group=True),),
                                   (_node("a"), _node("b", parent="a"))))
def test_invalid_selected_containment_is_a_typed_graph_error(nodes):
    with pytest.raises(LayoutError, match="E_LAYOUT_NETWORK_GRAPH"):
        _place(nodes, True)
