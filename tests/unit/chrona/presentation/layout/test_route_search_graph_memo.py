"""The sparse search memo stores only immutable visibility-graph facts."""

from chrona.presentation.layout import route_search
from chrona.presentation.layout.obstacles import (
    ROUTE_MEMO_LIMIT, ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex,
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
    graph = next(iter(index._route_memo.results.values()))
    nodes, edges, heuristic = graph
    assert index._route_memo.result_records == (
        1 + 2 * len(nodes) + sum(map(len, edges)) + len(heuristic))

    next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), copy, bounds=(-3, -5, 12, 5)))
    assert len(calls) == 2


def test_record_capacity_bypasses_graphs_without_changing_candidates(monkeypatch):
    index = _index()
    memo = index._route_memo
    # Leave one record: enough for a failure, not an immutable graph.
    memo.store(("occupied",), (), record_count=ROUTE_MEMO_LIMIT - 1)
    original_builder = route_search._build_sparse_graph
    calls = []

    def counted_builder(*args, **kwargs):
        graph = original_builder(*args, **kwargs)
        calls.append(graph)
        return graph

    monkeypatch.setattr(route_search, "_build_sparse_graph", counted_builder)
    def candidates(obstacles):
        paths = []
        try:
            paths.extend(route_search.orthogonal_route_candidates(
                (0, 0), (10, 0), obstacles, bounds=(-2, -5, 12, 5), limit=128))
        except route_search.RouteSearchFailure as failure:
            return tuple(paths), str(failure), failure.detail
        return tuple(paths), None, None

    fresh = candidates(_index())
    first = candidates(index)
    repeated = candidates(index.copy())
    assert fresh == first == repeated
    assert fresh[0] and fresh[1] == "E_PRESENTATION_ROUTE_LIMIT"
    assert len(calls) == 3
    assert list(memo.results) == [("occupied",)]
    assert memo.result_records == ROUTE_MEMO_LIMIT - 1


def test_payload_and_content_records_bound_retention_and_duplicate_admission():
    memo = _index()._route_memo
    value = tuple(range(ROUTE_MEMO_LIMIT))
    memo.store(("oversized",), value, record_count=1 + len(value))
    assert memo.results == {} and memo.result_records == 0
    memo.store(("fits",), value[:-1], record_count=ROUTE_MEMO_LIMIT)
    memo.store(("fits",), (), record_count=1)
    memo.store(("full",), (), record_count=1)
    assert list(memo.results) == [("fits",)]
    assert memo.results[("fits",)] == value[:-1]
    assert memo.result_records == ROUTE_MEMO_LIMIT

    oversized_content = tuple(str(n) for n in range(ROUTE_MEMO_LIMIT))
    assert memo.content_id(oversized_content) is None
    content = oversized_content[:-1]
    assert memo.content_id(content) == 0
    assert memo.content_id(content) == 0
    assert memo.content_id(("new",)) is None
    assert len(memo.contents) == 1 and memo.content_records == ROUTE_MEMO_LIMIT
