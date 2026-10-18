"""The sparse search memo stores only immutable visibility-graph facts."""

from chrona.presentation.layout import route_search
from chrona.presentation.layout.obstacles import (
    ROUTE_MEMO_LIMIT, ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex,
)


def _index():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:one", "mark", "timeline", ObstacleRect(4, -2, 6, 2)))
    return index


def test_bound_modes_partition_graph_memo_but_share_visibility_geometry(monkeypatch):
    original = route_search._reverse_bounds
    visibility_builder = route_search._build_visibility_base
    calls = []
    visibility_calls = []
    def counted(*args):
        calls.append(None)
        return original(*args)
    monkeypatch.setattr(route_search, "_reverse_bounds", counted)
    def visibility(*args, **kwargs):
        visibility_calls.append(None)
        return visibility_builder(*args, **kwargs)
    monkeypatch.setattr(route_search, "_build_visibility_base", visibility)
    index = _index()
    def path(exact):
        return next(route_search.orthogonal_route_candidates(
            (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5), exact_bound=exact))
    cheap = path(False)
    assert calls == []
    assert len(index._route_memo.results) == 1
    cheap_graph = next(iter(index._route_memo.results.values()))
    assert cheap_graph[2] == ()
    exact = path(True)
    assert len(calls) == 1
    assert len(index._route_memo.results) == 2
    exact_graph = next(value for value in index._route_memo.results.values() if value[2])
    assert cheap_graph[:2] == exact_graph[:2]
    assert path(False) == cheap and path(True) == exact
    assert len(calls) == 1  # neither mode borrowed or rebuilt the other's memo
    assert len(visibility_calls) == 1


def test_endpoint_geometry_is_shared_across_bound_modes_without_changing_order_or_budget(monkeypatch):
    from itertools import islice

    original_builder = route_search._build_sparse_graph
    original_reverse = route_search._reverse_bounds
    builds, reversals = [], []

    def counted_builder(*args, **kwargs):
        builds.append(None)
        return original_builder(*args, **kwargs)

    def counted_reverse(*args, **kwargs):
        reversals.append(None)
        return original_reverse(*args, **kwargs)

    monkeypatch.setattr(route_search, "_build_sparse_graph", counted_builder)
    monkeypatch.setattr(route_search, "_reverse_bounds", counted_reverse)

    def candidates(index, exact_bound):
        budget = route_search.RelationExpansionBudget(4096)
        found = tuple(islice(route_search.orthogonal_route_candidates(
            (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5),
            exact_bound=exact_bound, budget=budget), 2))
        return found, budget.expansions

    index = _index()
    before = candidates(index, False)
    assert len(index._route_memo.results) == 1
    relaxed_graph = next(iter(index._route_memo.results.values()))
    assert relaxed_graph[2] == ()

    after = candidates(index, True)
    assert len(builds) == 1  # only identical ordered graph geometry is reused
    assert len(reversals) == 1  # exact reverse data is completed for this mode
    assert len(index._route_memo.results) == 2  # existing exact/relaxed memo keys remain separate
    exact_graph = next(value for value in index._route_memo.results.values() if value[2])
    assert relaxed_graph[:2] == exact_graph[:2]

    # Reusing a previously completed endpoint geometry must match the same
    # candidate prefix and expansion accounting from a cold selection.
    cold = candidates(_index(), False)
    assert before == cold
    assert after == candidates(_index(), True)
    assert candidates(index, False) == before
    assert candidates(index, True) == after
    assert len(builds) == 3  # each cold selection builds its own geometry
    assert len(reversals) == 2


def test_endpoint_geometry_is_twelve_entry_fifo_per_selection(monkeypatch):
    index = _index()
    index.add(SurfaceObstacle("port:one", "port", "timeline", ObstacleRect(20, 20, 21, 21)))
    # Disable the separate bounded result memo so this exercises only the active geometry
    # cache, shared across visibility bases for the same prepared selection.
    memo = index._route_memo
    serial = 0
    while memo.content_id((f"occupied:{serial}",)) is not None:
        serial += 1
    assert memo.content_records < ROUTE_MEMO_LIMIT
    assert memo.content_id(tuple(repr(item) for item in index.select())) is None

    original_builder = route_search._build_sparse_graph
    calls = []

    def counted_builder(*args, **kwargs):
        calls.append(None)
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(route_search, "_build_sparse_graph", counted_builder)

    def query(start=(0, 0), *, bounds=(-2, -5, 12, 5), grid_offset=2.0, port_ids=()):
        try:
            return tuple(route_search.orthogonal_route_candidates(
                start, (10, 0), index, bounds=bounds, grid_offset=grid_offset,
                port_ids=port_ids, limit=8))
        except route_search.RouteSearchFailure as failure:
            assert str(failure) == "E_PRESENTATION_ROUTE_LIMIT"
            return ()

    scope = index.route_visibility_scope(None, None, ())
    assert scope.endpoint_geometry == {}
    entries = [
        ((0, 0), (-2, -5, 12, 5), 2.0, ()),
        ((0, 0), (-3, -5, 12, 5), 2.0, ()),
        ((0, 0), (-2, -5, 12, 5), 3.0, ()),
        ((0, 0), (-2, -5, 12, 5), 2.0, ("port:one",)),
        *[((0, start_y / 4), (-2, -5, 12, 5), 2.0, ()) for start_y in range(1, 9)],
    ]
    assert len(entries) == 12
    for start, bounds, grid_offset, port_ids in entries:
        query(start, bounds=bounds, grid_offset=grid_offset, port_ids=port_ids)
    assert len(scope.endpoint_geometry) == 12
    assert len(scope.bases) > 1  # endpoint slots are shared across these bases
    assert all(isinstance(value, tuple) and len(value) == 2
               for value in scope.endpoint_geometry.values())  # (ordered, adjacency) only
    fifo_keys = tuple(scope.endpoint_geometry)
    assert len(calls) == 12

    # A hit does not refresh insertion order; the next miss evicts the oldest
    # key (the first entry), not the recently-hit entry.
    query(entries[0][0], bounds=entries[0][1], grid_offset=entries[0][2],
          port_ids=entries[0][3])
    assert tuple(scope.endpoint_geometry) == fifo_keys
    query((9, 0))
    assert len(scope.endpoint_geometry) == 12
    assert tuple(scope.endpoint_geometry) == fifo_keys[1:] + (
        (repr(((9, 0), (10, 0), 2.0, (-2, -5, 12, 5))), frozenset()),)
    assert len(calls) == 13

    # A retained query still reuses geometry; the evicted first must rebuild.
    query(entries[1][0], bounds=entries[1][1], grid_offset=entries[1][2],
          port_ids=entries[1][3])
    assert len(calls) == 13
    query(entries[0][0], bounds=entries[0][1], grid_offset=entries[0][2],
          port_ids=entries[0][3])
    assert len(scope.endpoint_geometry) == 12
    assert len(calls) == 14


def test_endpoint_geometry_does_not_survive_selection_content_changes(monkeypatch):
    original_builder = route_search._build_sparse_graph
    calls = []

    def counted_builder(*args, **kwargs):
        calls.append(None)
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(route_search, "_build_sparse_graph", counted_builder)
    index = _index()
    first_scope = index.route_visibility_scope(None, None, ())
    next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5)))
    assert len(first_scope.endpoint_geometry) == 1
    unchanged = index.copy()
    assert unchanged.route_visibility_scope(None, None, ()).endpoint_geometry is first_scope.endpoint_geometry

    index.add(SurfaceObstacle("mark:two", "mark", "timeline", ObstacleRect(7, -3, 8, 3)))
    added_scope = index.route_visibility_scope(None, None, ())
    assert added_scope.endpoint_geometry is not first_scope.endpoint_geometry
    assert added_scope.endpoint_geometry == {}
    next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5)))
    assert len(added_scope.endpoint_geometry) == 1
    assert unchanged.route_visibility_scope(None, None, ()).endpoint_geometry is first_scope.endpoint_geometry

    overridden = index.copy(geometry_overrides={
        "mark:one": ObstacleRect(3, -3, 5, 3),
    })
    override_scope = overridden.route_visibility_scope(None, None, ())
    assert override_scope.endpoint_geometry is not added_scope.endpoint_geometry
    assert override_scope.endpoint_geometry == {}
    next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), overridden, bounds=(-2, -5, 12, 5)))
    assert len(override_scope.endpoint_geometry) == 1
    assert len(calls) == 3


def test_unselected_addition_preserves_the_existing_geometry_slot():
    index = _index()
    next(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5), classes=("mark",)))
    before = index.route_visibility_scope(("mark",), None, ()).endpoint_geometry
    assert len(before) == 1
    index.add(SurfaceObstacle("text:excluded", "text", "timeline", ObstacleRect(1, -1, 2, 1)))
    assert index.route_visibility_scope(("mark",), None, ()).endpoint_geometry is before
    assert len(before) == 1


def test_cheap_bound_keeps_alternative_prefixes_and_budget_accounting():
    from itertools import islice
    index = _index()
    budget = route_search.RelationExpansionBudget(128)
    paths = list(islice(route_search.orthogonal_route_candidates(
        (0, 0), (10, 0), index, bounds=(-2, -5, 12, 5),
        exact_bound=False, budget=budget), 2))
    assert len(paths) == 2 and paths[0] != paths[1]
    assert all(path[0] == (0, 0) and path[-1] == (10, 0) for path in paths)
    assert 0 < budget.expansions <= 128


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
    # The full result memo remains exhausted, but an identical copied
    # selection can reuse its one active endpoint-geometry slot.
    assert len(calls) == 2
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
