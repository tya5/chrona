"""NORMAL graph search begins beyond mandatory completed terminal tangents."""

from chrona.presentation.layout import route_search
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.routing import select_relation_route


def _pair(target=(10.0, 10.0)):
    return ((ConnectorEgress("end", (0.0, 0.0), (0.0, 0.0), ()),
             ConnectorEgress("start", target, target, ())),)


def _select(pairs, *, lead_runs, **kwargs):
    obstacles = kwargs.pop("obstacles", SurfaceObstacleIndex())
    return select_relation_route(pairs, obstacles=obstacles,
        bounds=(-10.0, -10.0, 20.0, 20.0), source_host_id=None,
        target_host_id=None, relation_scene_id="normal-lead", max_bends=10,
        max_detour_ratio=10.0, endpoint_lead_runs=lead_runs,
        search_policy="best", search_budget=1000, **kwargs)


def test_normal_graph_queries_once_from_remaining_lead_ends_and_reassembles(monkeypatch):
    calls = []
    original = route_search.orthogonal_route_candidates

    def observed(start, end, *args, **kwargs):
        calls.append((start, end, kwargs.get("limit"), kwargs.get("budget")))
        yield from original(start, end, *args, **kwargs)

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", observed)
    pairs = _pair()
    selected = _select(pairs, lead_runs=lambda *_: (2.0, 3.0))

    assert selected.selected_pair == pairs[0]
    assert len(calls) == 1
    assert calls[0][:3] == ((2.0, 0.0), (7.0, 10.0), 4096)
    assert calls[0][3] is not None
    assert selected.search_used
    assert selected.search_expansions <= selected.search_budget
    assert selected.search_expansions == calls[0][3].expansions
    assert selected.points[0] == pairs[0][0].semantic_port
    assert selected.points[-1] == pairs[0][1].semantic_port
    assert selected.points[1] == (2.0, 0.0)
    assert selected.points[-2][1] == 10.0
    assert selected.points[-1][0] - selected.points[-2][0] >= 3.0


def test_aligned_exposed_straight_is_completed_before_shifted_graph(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("aligned exposed route should settle before graph search")

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", forbidden)
    pairs = _pair(target=(10.0, 0.0))
    selected = _select(pairs, lead_runs=lambda *_: (2.0, 3.0))

    assert selected.selected_pair == pairs[0]
    assert selected.points == ((0.0, 0.0), (10.0, 0.0))
    assert not selected.search_used


def test_aligned_candidates_remain_in_best_cross_pair_ranking(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("accepted aligned candidates should not invoke graph search")

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", forbidden)
    source = ConnectorEgress("end", (0.0, 0.0), (0.0, 0.0), ())
    pairs = ((source, ConnectorEgress("start", (10.0, 0.0), (10.0, 0.0), ())),
             (source, ConnectorEgress("above", (0.0, 10.0), (0.0, 10.0), ())))
    selected = _select(pairs, lead_runs=lambda *_: (2.0, 3.0),
                       rank=lambda _points, _source, target: (target.side != "above",))

    assert selected.selected_pair == pairs[1]
    assert not selected.search_used
    assert sum(attempt.outcome == "eligible-not-selected" for attempt in selected.attempts) == 1


def test_preferred_hint_keeps_its_exposed_geometry_before_graph(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("accepted preferred path must precede ordinary graph search")

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", forbidden)
    pairs = _pair()
    hint = ((0.0, 0.0), (0.0, 10.0), (10.0, 10.0))
    selected = _select(pairs, lead_runs=lambda *_: (2.0, 3.0),
                       preferred_routes=((pairs[0], hint),))

    assert selected.selected_pair == pairs[0]
    assert selected.settled_by_hint
    assert selected.points == hint
    assert not selected.search_used


def test_zero_remaining_leads_keep_exposed_graph_endpoints(monkeypatch):
    calls = []
    original = route_search.orthogonal_route_candidates

    def observed(start, end, *args, **kwargs):
        calls.append((start, end))
        yield from original(start, end, *args, **kwargs)

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", observed)
    pairs = _pair()
    selected = _select(pairs, lead_runs=lambda *_: (0.0, 0.0))

    assert selected.selected_pair == pairs[0]
    assert calls == [((0.0, 0.0), (10.0, 10.0))]


def test_completed_corridors_subtract_from_required_leads(monkeypatch):
    calls = []
    original = route_search.orthogonal_route_candidates

    def observed(start, end, *args, **kwargs):
        calls.append((start, end))
        yield from original(start, end, *args, **kwargs)

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", observed)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("source-host", "mark", "timeline", ObstacleRect(-1., -1., 1., 1.)))
    obstacles.add(SurfaceObstacle("target-host", "mark", "timeline", ObstacleRect(9., 9., 11., 11.)))
    pairs = ((ConnectorEgress("end", (0.0, 0.0), (2.0, 0.0), ("source-host",)),
              ConnectorEgress("start", (10.0, 10.0), (8.0, 10.0), ("target-host",))),)

    def remaining(source, target):
        source_corridor = abs(source.exposed_port[0] - source.semantic_port[0])
        target_corridor = abs(target.exposed_port[0] - target.semantic_port[0])
        return max(0.0, 2.0 - source_corridor), max(0.0, 2.0 - target_corridor)

    selected = _select(pairs, lead_runs=remaining, obstacles=obstacles)

    assert selected.selected_pair == pairs[0]
    assert calls == [(pairs[0][0].exposed_port, pairs[0][1].exposed_port)]
    assert selected.points[0] == pairs[0][0].semantic_port
    assert selected.points[-1] == pairs[0][1].semantic_port


def test_graph_fixed_lead_does_not_receive_text_clearance_exemption(monkeypatch):
    def one_middle_path(_start, _end, *_args, **_kwargs):
        yield ((2.0, 0.0), (2.0, 10.0), (7.0, 10.0))

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", one_middle_path)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("text-on-lead", "text", "timeline", ObstacleRect(.5, -.5, 1.5, .5)))
    pairs = _pair()

    selected = _select(pairs, lead_runs=lambda *_: (2.0, 3.0), obstacles=obstacles,
                       protected=False)

    assert selected.selected_pair is None
    assert selected.search_used
    assert selected.attempts[0].search_failure == "E_LAYOUT_ROUTE_THROUGH_MARK"
