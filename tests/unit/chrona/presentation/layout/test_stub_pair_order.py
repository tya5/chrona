"""Every source exit is tried with the horizontal entry stub before any other pair (#1072).

A pure ordering rule on candidate pairs; no geometry and no `examples/` input.
"""
from chrona.presentation.layout.ports import ConnectorEgress, stub_pairs_first


def egress(side: str, *, stub: bool = False, through_body: bool = False) -> ConnectorEgress:
    return ConnectorEgress(side, (0.0, 0.0), (1.0, 0.0), ("host",), stub, through_body)


def test_stub_target_pairs_of_every_source_exit_come_first_and_the_order_inside_each_group_is_kept():
    below, end = egress("below"), egress("end")
    stub, above, start = egress("start", stub=True), egress("above"), egress("start")
    # The nearest exit (below) pairs with the stub first, but its other targets come before the end exit's stub.
    pairs = ((below, stub), (below, above), (below, start), (end, stub), (end, above), (end, start))
    assert stub_pairs_first(pairs) == ((below, stub), (end, stub), (below, above), (below, start), (end, above), (end, start))


def test_without_a_stub_candidate_the_order_is_unchanged():
    a, b, c = egress("above"), egress("below"), egress("start")
    pairs = ((a, c), (a, b), (b, c))
    assert stub_pairs_first(pairs) == pairs


def test_an_exit_through_the_sources_own_bar_is_not_promoted():
    # The far-side exit of a span crosses its own mark: it keeps its place behind the ordinary exits.
    end, through = egress("end"), egress("start", through_body=True)
    stub, above = egress("start", stub=True), egress("above")
    pairs = ((end, above), (through, stub), (end, stub))
    assert stub_pairs_first(pairs) == ((end, stub), (end, above), (through, stub))
