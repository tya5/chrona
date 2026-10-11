"""The branch-local broad phase preserves the old full-history oracle."""

from dataclasses import dataclass
from itertools import islice
from random import Random

import pytest

from chrona.presentation.layout import route_search as search
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex


@dataclass(frozen=True)
class FullHistory:
    segments: tuple = ()

    def add(self, segment):
        return FullHistory((*self.segments, segment))

    def intersects(self, segment):
        return any(search._history_segments_intersect(segment, old) for old in self.segments)


@pytest.mark.parametrize("candidate", [
    ((4, 0), (4, 3)),  # exact perpendicular endpoint: allowed
    ((4, 0), (8, 0)),  # exact opposite rays: allowed
    ((4, 0), (2, 0)),  # same ray: collision
    ((4 + 5e-10, 0), (4 + 5e-10, 3)),
    ((4 + 1e-9, 0), (8, 0)),
    ((4 + 1.1e-9, 0), (8, 0)),
    ((0, 5e-10), (4, 5e-10)),
    ((0, 1.1e-9), (4, 1.1e-9)),
    ((2, -3), (2, 3)),
])
def test_shared_endpoints_and_epsilon_gaps_keep_exact_semantics(candidate):
    previous = ((0, 0), (4, 0))
    assert search._HistoryIndex().add(previous).intersects(candidate) == (
        search._history_segments_intersect(candidate, previous))


def test_index_matches_full_scan_for_random_and_epsilon_contacts():
    random = Random(1298)
    indexed, oracle = search._HistoryIndex(), FullHistory()
    for _ in range(2000):
        a = (random.randrange(-50, 50), random.randrange(-50, 50))
        axis = random.randrange(2)
        b = list(a)
        b[axis] += random.randrange(1, 20)
        segment = (a, tuple(b))
        assert indexed.intersects(segment) == oracle.intersects(segment)
        for epsilon in (0, 5e-10, 1e-9, 1.1e-9):
            shifted = tuple((p[0] + epsilon, p[1] + epsilon) for p in segment)
            assert indexed.intersects(shifted) == oracle.intersects(shifted)
        # Keep histories small enough to exercise both hits and misses.
        if _ % 20 == 0:
            indexed, oracle = search._HistoryIndex(), FullHistory()
        indexed, oracle = indexed.add(segment), oracle.add(segment)


def test_child_prefixes_do_not_mutate_parent_or_sibling():
    parent = search._HistoryIndex().add(((0, 0), (4, 0)))
    left = parent.add(((4, 0), (4, 4)))
    right = parent.add(((4, 0), (4, -4)))
    crossing = ((3, 2), (5, 2))
    assert left.intersects(crossing)
    assert not parent.intersects(crossing)
    assert not right.intersects(crossing)
    assert left.horizontal is parent.horizontal is right.horizontal


def test_distant_lines_and_intervals_do_not_call_exact_predicate(monkeypatch):
    index = search._HistoryIndex()
    for line in range(100):
        index = index.add(((0, line * 10), (5, line * 10)))
    original = search._history_segments_intersect
    calls = []

    def counted(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(search, "_history_segments_intersect", counted)
    assert not index.intersects(((20, 500), (30, 500)))
    assert calls == []
    assert index.intersects(((2, 499), (2, 501)))
    assert len(calls) == 1


@pytest.mark.parametrize("penalty", [None, 0.0, 2.0])
def test_candidate_order_and_terminal_exclusion_match_full_scan(monkeypatch, penalty):
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("one", "mark", "timeline", ObstacleRect(3, -1, 5, 2)))
    obstacles.add(SurfaceObstacle("two", "mark", "timeline", ObstacleRect(7, -3, 9, 1)))
    indexed_class = search._HistoryIndex
    graph_nodes = []
    original_build = search._build_sparse_graph
    original_push = search.heappush

    def remember_graph(*args, **kwargs):
        graph = original_build(*args, **kwargs)
        graph_nodes[:] = graph[0]
        return graph

    def check_prefix(queue, entry):
        state = entry[-1]
        if isinstance(state, tuple) and len(state) == 6 and isinstance(state[-1], CheckingHistory):
            path, history = state[-2:]
            expected = tuple((graph_nodes[path[i]], graph_nodes[path[i + 1]])
                             for i in range(len(path) - 2))
            assert history.segments == expected
        return original_push(queue, entry)

    class CheckingHistory(FullHistory):
        def add(self, segment):
            return CheckingHistory((*self.segments, segment))

        def intersects(self, segment):
            index = indexed_class()
            for previous in self.segments:
                index = index.add(previous)
            assert index.intersects(segment) == super().intersects(segment)
            return super().intersects(segment)

    def candidates():
        return tuple(islice(search.orthogonal_route_candidates(
            (0, 0), (12, 0), obstacles, bounds=(-2, -6, 14, 6),
            bend_penalty=penalty, limit=4096), 12))

    monkeypatch.setattr(search, "_build_sparse_graph", remember_graph)
    monkeypatch.setattr(search, "heappush", check_prefix)
    actual = candidates()
    monkeypatch.setattr(search, "_HistoryIndex", CheckingHistory)
    assert candidates() == actual
    assert candidates() == actual
