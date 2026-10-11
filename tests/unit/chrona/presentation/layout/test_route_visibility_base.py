"""#1420: shared visibility must preserve the complete endpoint-specific graph."""
from collections import Counter
from random import Random

import pytest

from chrona.presentation.layout import route_search as search
from chrona.presentation.layout.obstacles import (
    ROUTE_MEMO_LIMIT, ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
    obstacle_envelope,
)


def _index():
    index = SurfaceObstacleIndex()
    index.extend(SurfaceObstacle(f"mark:{number}", "mark", "timeline",
                                 ObstacleRect(4 + number * 3, -2, 6 + number * 3, 2))
                 for number in range(8))
    # Force the old result memo to bypass graphs; active preparation still reuses.
    index._route_memo.store(("full",), (), record_count=ROUTE_MEMO_LIMIT)
    return index


def _outcome(index, start=(0, 0), end=(30, 0), **kwargs):
    paths = []
    try:
        paths.extend(search.orthogonal_route_candidates(
            start, end, index, bounds=(-2, -6, 32, 6), limit=32, **kwargs))
    except search.RouteSearchFailure as failure:
        return tuple(paths), str(failure), failure.detail
    return tuple(paths), None, None


def test_base_build_counter_depends_on_selected_content_not_endpoint_queries(monkeypatch):
    counts = Counter()
    builder = search._build_visibility_base
    assembler = search._build_sparse_graph

    def build(*args, **kwargs):
        counts["base_builds"] += 1
        return builder(*args, **kwargs)

    def assemble(*args, **kwargs):
        counts["endpoint_assemblies"] += 1
        reused = assembler(*args, **kwargs)
        kwargs.pop("visibility_base")
        fresh = assembler(*args, **kwargs)
        assert reused == fresh  # ordered nodes, adjacency AND reverse heuristic
        return reused

    monkeypatch.setattr(search, "_build_visibility_base", build)
    monkeypatch.setattr(search, "_build_sparse_graph", assemble)
    index = _index()
    copies = [index.copy() for _ in range(10)]  # before ANY routing filter is queried
    for number in range(10):
        clone = copies[number]
        _outcome(clone, (0, -0.1 * number), (30, 0.1 * number),
                 classes=("mark",))
    assert counts == {"base_builds": 1, "endpoint_assemblies": 10}
    index.add(SurfaceObstacle("port:excluded", "port", "timeline", ObstacleRect(-1, -1, 0, 0)))
    _outcome(index, classes=("mark",), port_ids=("port:excluded",))
    assert counts == {"base_builds": 1, "endpoint_assemblies": 11}
    index.add(SurfaceObstacle("new-mark", "mark", "timeline", ObstacleRect(27, -3, 28, 3)))
    _outcome(index, classes=("mark",))
    assert counts == {"base_builds": 2, "endpoint_assemblies": 12}


@pytest.mark.parametrize("offset", (0.0, 0.1, 2.0))
@pytest.mark.parametrize("bounds", (None, (-2, -8, 32, 8)))
def test_exact_base_edges_match_the_fresh_graph_with_strokes_clearance_and_boundaries(offset, bounds):
    rng = Random("visibility-base")
    index = _index()
    index.add(SurfaceObstacle("diagonal", "text", "timeline",
                              ObstacleSegment((3, -4), (24, 4), 0.2), clearance=0.1))
    index.add(SurfaceObstacle("port", "port", "timeline", ObstacleRect(0, 0, 1, 1)))
    rects = tuple((left - item.clearance, top - item.clearance,
                   right + item.clearance, bottom + item.clearance)
                  for item in index.all()
                  for left, top, right, bottom in (obstacle_envelope(item.geometry),))

    def clear(a, b):
        return not index.collisions(ObstacleSegment(a, b), port_ids=("port",))

    base = search._build_visibility_base(rects, grid_offset=offset, bounds=bounds, clear=clear)
    assert base.visibility
    for _ in range(12):
        start, end = (0, rng.choice((-3.0, -0.0, 1.0, 3.0))), (30, rng.choice((-3.0, 0.0, 1.0, 3.0)))
        fresh = search._build_sparse_graph(start, end, rects, grid_offset=offset, bounds=bounds, clear=clear)
        reused = search._build_sparse_graph(start, end, rects, grid_offset=offset, bounds=bounds,
                                             clear=clear, visibility_base=base)
        assert fresh == reused
        assert repr(fresh) == repr(reused)  # signed-zero representation as well


def test_candidate_sequences_and_exhaustion_equal_uncached_visibility(monkeypatch):
    index = _index()
    fast = [_outcome(index, (0, y), (30, -y)) for y in (-1, 0, 1)]
    assembler = search._build_sparse_graph

    def without_base(*args, **kwargs):
        kwargs.pop("visibility_base")
        return assembler(*args, **kwargs)

    monkeypatch.setattr(search, "_build_sparse_graph", without_base)
    slow = [_outcome(index.copy(), (0, y), (30, -y)) for y in (-1, 0, 1)]
    assert fast == slow
    assert any(paths for paths, _, _ in fast)
    assert all(code == "E_PRESENTATION_ROUTE_LIMIT" for _, code, _ in fast)


def test_geometry_override_does_not_replay_old_visibility():
    index = _index()
    _outcome(index, classes=("mark",))
    old_store = index.route_visibility_scope(("mark",), None, ()).bases
    overridden = index.copy(geometry_overrides={"mark:0": ObstacleRect(4, -5, 6, 5)})
    new_store = overridden.route_visibility_scope(("mark",), None, ()).bases
    assert new_store is not old_store and not new_store
    changed = _outcome(overridden, classes=("mark",))
    fresh = _index()
    fresh = fresh.copy(geometry_overrides={"mark:0": ObstacleRect(4, -5, 6, 5)})
    assert changed == _outcome(fresh, classes=("mark",))


def test_selected_port_exemptions_partition_bases_and_invalid_ports_still_fail():
    index = _index()
    index.add(SurfaceObstacle("port:selected", "port", "timeline", ObstacleRect(12, -4, 13, 4)))
    _outcome(index)
    _outcome(index, port_ids=("port:selected",))
    store = index.route_visibility_scope(None, None, ()).bases
    assert len(store) == 2
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        _outcome(index, port_ids=("missing",))


def test_multiple_selected_additions_incrementally_recheck_old_edges_without_a_snapshot_chain(monkeypatch):
    index = _index()
    _outcome(index, classes=("mark", "dependency-route"))
    old = index.route_visibility_scope(("mark", "dependency-route"), None, ()).bases
    additions = (
        SurfaceObstacle("route:one", "dependency-route", "timeline",
                        ObstacleSegment((1, -4), (29, -4), 0.2)),
        SurfaceObstacle("route:two", "dependency-route", "timeline",
                        ObstacleSegment((1, 4), (29, 4), 0.2)),
    )
    index.extend(additions)
    scope = index.route_visibility_scope(("mark", "dependency-route"), None, ())
    assert scope.previous_bases is old and scope.additions == additions
    builder = search._build_visibility_base
    inherited = []

    def build(*args, **kwargs):
        inherited.append(kwargs["previous"])
        incremental = builder(*args, **kwargs)
        kwargs.pop("previous")
        kwargs.pop("clear_additions")
        fresh = builder(*args, **kwargs)
        assert incremental == fresh  # includes blocked as well as clear edges
        return incremental

    monkeypatch.setattr(search, "_build_visibility_base", build)
    after = _outcome(index, classes=("mark", "dependency-route"))
    assert len(inherited) == 1 and inherited[0] is not None
    fresh = _index()
    fresh.extend(additions)
    monkeypatch.setattr(search, "_build_visibility_base", builder)
    assert after == _outcome(fresh, classes=("mark", "dependency-route"))
    current_store = scope.bases
    index.add(SurfaceObstacle("route:three", "dependency-route", "timeline",
                              ObstacleSegment((1, -3), (29, -3), 0.2)))
    next_scope = index.route_visibility_scope(("mark", "dependency-route"), None, ())
    assert next_scope.previous_bases is current_store
    assert len(next_scope.additions) == 1  # do not keep the old delta/history


def test_projection_line_work_is_reused_but_split_edges_keep_the_full_oracle(monkeypatch):
    index = _index()
    rects = tuple(obstacle_envelope(item.geometry) for item in index.all())
    calls = Counter()
    original_line = search._build_projection_line

    def build_line(*args, **kwargs):
        calls["line_builds"] += 1
        return original_line(*args, **kwargs)

    def clear(a, b):
        calls["collision_queries"] += 1
        return not index.collisions(ObstacleSegment(a, b))

    monkeypatch.setattr(search, "_build_projection_line", build_line)
    base = search._build_visibility_base(rects, grid_offset=2, bounds=(-2, -6, 32, 6), clear=clear)
    calls.clear()
    first = search._build_sparse_graph((0, 0), (30, 0), rects, grid_offset=2,
                                        bounds=(-2, -6, 32, 6), clear=clear, visibility_base=base)
    first_work = calls["collision_queries"]
    first_lines = calls["line_builds"]
    calls["collision_queries"] = 0
    second = search._build_sparse_graph((0, 0), (30, 0), rects, grid_offset=2,
                                         bounds=(-2, -6, 32, 6), clear=clear, visibility_base=base)
    assert first == second
    assert first_lines > 0 and calls["line_builds"] == first_lines
    assert 0 < calls["collision_queries"] < first_work  # endpoint splits are NOT cached blindly
    fresh = search._build_sparse_graph((0, 0), (30, 0), rects, grid_offset=2,
                                        bounds=(-2, -6, 32, 6), clear=clear)
    assert first == fresh


def test_projection_working_set_is_bounded_and_eviction_preserves_facts():
    index = _index()
    rects = tuple(obstacle_envelope(item.geometry) for item in index.all())

    def clear(a, b):
        return not index.collisions(ObstacleSegment(a, b))

    base = search._build_visibility_base(rects, grid_offset=2, bounds=(-2, -6, 32, 6), clear=clear)
    original = base.projection_line(0, 0.0, clear)
    for number in range(40):
        base.projection_line(number % 2, number / 10, clear)
        assert len(base._projection_lines) <= search._PROJECTION_LINE_LIMIT
        retained = sum(len(value) for value in base._projection_lines.values())
        assert retained <= search._PROJECTION_LINE_LIMIT * max(len(base.x_events), len(base.y_events))
    assert (0, repr(0.0)) not in base._projection_lines
    assert base.projection_line(0, 0.0, clear) == original


def test_selected_addition_does_not_inherit_projection_line_facts():
    index = _index()
    _outcome(index)
    before = index.copy()
    old = next(iter(index.route_visibility_scope(None, None, ()).bases.values()))
    assert old._projection_lines
    index.add(SurfaceObstacle("new-blocker", "mark", "timeline", ObstacleRect(0, -3, 1, 3)))
    _outcome(index, start=(0, -5), end=(30, 5))
    new = next(iter(index.route_visibility_scope(None, None, ()).bases.values()))
    assert new._projection_lines is not old._projection_lines
    assert new.projection_line(1, 0.5, lambda a, b: not index.collisions(ObstacleSegment(a, b))) != (
        old.projection_line(1, 0.5, lambda a, b: not before.collisions(ObstacleSegment(a, b))))
