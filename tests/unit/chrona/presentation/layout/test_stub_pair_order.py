"""Every source exit is tried with the horizontal entry stub before any other pair (#1072).

A pure ordering rule on candidate pairs; no geometry and no `examples/` input.
"""
from chrona.presentation.layout.ports import ConnectorEgress, stub_pairs_first


def egress(side: str, *, stub: bool = False) -> ConnectorEgress:
    return ConnectorEgress(side, (0.0, 0.0), (1.0, 0.0), ("host",), stub)


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


def test_every_source_exit_with_a_stub_target_is_promoted_in_original_order():
    end, above = egress("end"), egress("above")
    end_stub, above_stub = egress("start", stub=True), egress("end", stub=True)
    pairs = ((end, above), (above, above_stub), (end, end_stub))
    assert stub_pairs_first(pairs) == ((above, above_stub), (end, end_stub), (end, above))
