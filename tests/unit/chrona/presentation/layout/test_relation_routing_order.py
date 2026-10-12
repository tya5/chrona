"""Priority is Layout policy; declaration identity is not processing order."""
from dataclasses import replace

import pytest

from chrona.presentation.layout.relation_routing_order import dependency_routing_order
from chrona.presentation.model.surface_content import RelationPresentationFact


def _fact(source, target, *, critical=False):
    return RelationPresentationFact(f"{source}-{target}", source, "end", target,
                                    "start", "0d", None, "dependency", critical=critical)


@pytest.mark.parametrize("edges, expected", [
    ((), ()),
    ((("b", "c"), ("a", "b")), (1, 0)),
    ((("a", "b"), ("c", "b")), (0, 1)),
    ((("a", "b"), ("b", "a")), (0, 1)),
    ((("a", "b"), ("b", "a"), ("x", "y")), (2, 0, 1)),
    ((("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")), (0, 1, 2, 3)),
])
def test_all_ordinary_retains_arrival_tie_cycle_and_branch_order(edges, expected):
    facts = tuple(_fact(*edge) for edge in edges)
    result = dependency_routing_order(facts)
    assert tuple(index for index, _ in result) == expected
    assert all(fact is facts[index] for index, fact in result)


@pytest.mark.parametrize("critical_indices", [(0,), (1,), (0, 2), (1, 3), (0, 1, 2, 3)])
def test_critical_partition_preserves_existing_within_class_order_and_indices(critical_indices):
    ordinary = tuple(_fact(*edge) for edge in (("b", "c"), ("a", "b"), ("c", "d"), ("x", "y")))
    ordinary_order = tuple(index for index, _ in dependency_routing_order(ordinary))
    facts = tuple(replace(fact, critical=index in critical_indices) for index, fact in enumerate(ordinary))
    result = dependency_routing_order(facts)
    assert tuple(index for index, _ in result) == (
        tuple(index for index in ordinary_order if index in critical_indices)
        + tuple(index for index in ordinary_order if index not in critical_indices))
    assert all(fact is facts[index] for index, fact in result)
    assert sorted(index for index, _ in result) == list(range(len(facts)))


def test_unrelated_ordinary_append_does_not_reorder_critical_processing():
    facts = (_fact("b", "c", critical=True), _fact("a", "b", critical=True), _fact("x", "y"))
    appended = (*facts, _fact("unrelated-a", "unrelated-b"))
    assert tuple(fact for _, fact in dependency_routing_order(appended) if fact.critical) == (
        tuple(fact for _, fact in dependency_routing_order(facts) if fact.critical))
