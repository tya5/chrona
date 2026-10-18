from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.dependency_network import compose_dependency_network_layout
from chrona.presentation.layout.model import Rect
from tests.unit.chrona.presentation.layout.test_dependency_network import (
    _DeadlineTheme, _deadline_measured, _deadline_network, _measured, _network,
)


@pytest.mark.parametrize("flow", ("horizontal", "vertical-rl", "vertical-lr"))
@pytest.mark.parametrize("padding,size", ((None, (34, 31)), ((4, 5), (28, 27)), ((0, 0), (20, 17))))
def test_node_minima_include_actual_title_envelope_and_theme_insets(flow, padding, size):
    measured = _measured("a")
    metrics = {**measured.metric_values, "network.node.minInlineSize": Decimal(1),
               "network.node.minBlockSize": Decimal(1)}
    if padding is not None:
        metrics.update({"network.node.paddingInline": Decimal(padding[0]),
                        "network.node.paddingBlock": Decimal(padding[1])})
    placed = compose_dependency_network_layout(
        _network(("a",), ()), title_bounds=Rect(Decimal(0), Decimal(0), Decimal(200), Decimal(30)),
        bounds=Rect(Decimal(0), Decimal(40), Decimal(500), Decimal(400)),
        measured_sources=replace(measured, metric_values=metrics), flow_direction=flow)
    node, text = placed.nodes[0], placed.text[1]
    assert (node.bounds.inline_size, node.bounds.block_size) == size
    inline, block = padding or (7, 7)
    assert text.bounds.inline - node.bounds.inline >= inline
    assert node.bounds.inline + node.bounds.inline_size - text.bounds.inline - text.bounds.inline_size >= inline
    assert text.bounds.block - node.bounds.block >= block
    assert node.bounds.block + node.bounds.block_size - text.bounds.block - text.bounds.block_size >= block


def test_deadline_title_footer_and_completed_ink_fit_inside_padded_node():
    measured = _deadline_measured("a")
    measured = replace(measured, metric_values={**measured.metric_values,
        "network.node.paddingInline": Decimal(9), "network.node.paddingBlock": Decimal(11)})
    placed = compose_dependency_network_layout(
        _deadline_network(), title_bounds=Rect(Decimal(0), Decimal(0), Decimal(200), Decimal(30)),
        bounds=Rect(Decimal(0), Decimal(40), Decimal(500), Decimal(400)),
        measured_sources=measured, theme_tokens=_DeadlineTheme(), flow_direction="horizontal")
    node = next(item for item in placed.nodes if item.object_id == "a")
    for item in (*placed.text, *placed.shapes):
        if item.source_ref != "a":
            continue
        assert item.bounds.inline >= node.bounds.inline + 9
        assert item.bounds.block >= node.bounds.block + 11
        assert item.bounds.inline + item.bounds.inline_size <= node.bounds.inline + node.bounds.inline_size - 9
        assert item.bounds.block + item.bounds.block_size <= node.bounds.block + node.bounds.block_size - 11
