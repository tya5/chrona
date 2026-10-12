"""Close routing processing priority without changing declaration identity."""
from __future__ import annotations

from chrona.presentation.model.surface_content import RelationPresentationFact


def dependency_routing_order(
    declared: tuple[RelationPresentationFact, ...],
) -> tuple[tuple[int, RelationPresentationFact], ...]:
    """Critical first; stable arrivals-before-departures within each class.

    The original index travels with its immutable fact. Cyclic remainder and
    equal target ranks retain declaration order, as in the ordinary policy.
    Search eligibility, route geometry and emitted ordering are separate owners.
    """
    indegree: dict[str, int] = {}
    followers: dict[str, list[str]] = {}
    for item in declared:
        source, target = item.source_object_id, item.target_object_id
        indegree.setdefault(source, 0)
        indegree[target] = indegree.get(target, 0) + 1
        followers.setdefault(source, []).append(target)
    ready = [node for node in indegree if not indegree[node]]
    rank: dict[str, int] = {}
    for node in ready:
        rank[node] = len(rank)
        for target in followers.get(node, ()):
            indegree[target] -= 1
            if not indegree[target]:
                ready.append(target)
    return tuple(sorted(enumerate(declared), key=lambda pair: (
        not pair[1].critical, rank.get(pair[1].target_object_id, len(rank)),
    )))
