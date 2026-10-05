"""The sparse search memo stores only immutable visibility-graph facts."""

from chrona.presentation.layout import route_search
from chrona.presentation.layout.obstacles import (
    ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex,
)


def _index():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:one", "mark", "timeline", ObstacleRect(4, -2, 6, 2)))
    return index


def test_identical_copy_reuses_graph_but_query_parameters_remain_part_of_key(monkeypatch):
    original_builder = route_search._build_sparse_graph
    calls = []

    def counted_builder(*args, **kwargs):
        calls.append(None)
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(route_search, "_build_sparse_graph", counted_builder)
    index = _index()
    copy = index.copy()
    first = next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5)))
    same = next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), copy, bounds=(-2, -5, 12, 5)))
    assert first == same
    assert len(calls) == 1

    next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), copy, bounds=(-3, -5, 12, 5)))
    assert len(calls) == 2
