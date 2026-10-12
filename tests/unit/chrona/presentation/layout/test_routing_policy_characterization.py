"""#1426: an admissible heuristic change need not preserve finite-quota output."""
from chrona.presentation.layout import route_search as search
from chrona.presentation.layout import routing
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress


START, END = (0.0, 0.0), (30.0, 20.0)
BOUNDS = (-5.0, -5.0, 35.0, 25.0)
EXPECTED = tuple((START, (0.0, y), (30.0, y), END) for y in (14.0, 7.0, 5.0))


def _obstacles():
    index = SurfaceObstacleIndex()
    index.extend(SurfaceObstacle(f"mark:{number}", "mark", "timeline", ObstacleRect(*rect))
                 for number, rect in enumerate(((9, 16, 13, 21), (19, -2, 23, 3),
                                               (14, 1, 19, 5), (18, -1, 22, 2), (7, 2, 9, 5))))
    return index


def _geometric_graph(builder):
    """Negative control only: replace the exact bound by an admissible geometric one."""
    def build(start, end, *args, **kwargs):
        nodes, edges, remaining = builder(start, end, *args, **kwargs)

        def bound(key):
            node, direction = key
            x, y = nodes[node]
            dx, dy = abs(x - end[0]), abs(y - end[1])
            bends = (0 if dx == dy == 0 else int(direction != 1) if dx == 0
                     else int(direction != 0) if dy == 0 else 1)
            return bends, dx + dy

        return nodes, edges, tuple((key, bound(key)) for key, _ in remaining)
    return build


def _candidates():
    paths = []
    try:
        paths.extend(search.orthogonal_route_candidates(START, END, _obstacles(),
                                                        bounds=BOUNDS, limit=32))
    except search.RouteSearchFailure as failure:
        return tuple(paths), str(failure)
    return tuple(paths), None


def test_exact_candidate_order_and_exhaustion_have_a_geometric_bound_negative_control(monkeypatch):
    assert _candidates() == (EXPECTED, "E_PRESENTATION_ROUTE_LIMIT")
    monkeypatch.setattr(search, "_build_sparse_graph", _geometric_graph(search._build_sparse_graph))
    assert _candidates() == ((), "E_PRESENTATION_ROUTE_LIMIT")


def test_ranked_selection_can_be_lost_by_a_lower_bound_only_change(monkeypatch):
    source, target = ConnectorEgress("end", START, START, ()), ConnectorEgress("start", END, END, ())
    monkeypatch.setattr(routing, "RELATION_SEARCH_EXPANSIONS", 32)

    def select():
        return routing.select_relation_route(((source, target),), obstacles=_obstacles(),
            bounds=BOUNDS, source_host_id=None, target_host_id=None, relation_scene_id="relation:r",
            max_bends=4, max_detour_ratio=2.0,
            rank=lambda points, left, right: routing.route_quality_metrics(points))

    selected = select()
    assert selected.selected_pair == (source, target)
    assert selected.points == EXPECTED[0]
    monkeypatch.setattr(search, "_build_sparse_graph", _geometric_graph(search._build_sparse_graph))
    limited = select()
    assert limited.selected_pair is None
    assert limited.attempts[0].search_failure == "E_PRESENTATION_ROUTE_LIMIT"


def test_first_fit_rescues_real_exact_route_after_shapes_and_cheap_search_fail(monkeypatch):
    from chrona.presentation.layout.relation_shapes import RelationShapeChannels

    monkeypatch.setattr(routing, "RELATION_SEARCH_EXPANSIONS", 32)
    pair = (ConnectorEgress("end", START, START, ()),
            ConnectorEgress("start", END, END, ()))
    selected = routing.select_relation_route((pair,), obstacles=_obstacles(),
        bounds=BOUNDS, source_host_id=None, target_host_id=None,
        relation_scene_id="relation:rescue", max_bends=4, max_detour_ratio=2.0,
        search_policy="first-fit", channels=RelationShapeChannels((), ()),
        accept=lambda points: points == EXPECTED[0],
        rank=lambda points, left, right: routing.route_quality_metrics(points))

    assert selected.selected_pair == pair
    assert selected.points == EXPECTED[0]
    assert selected.search_used and not selected.settled_by_shape
    assert [attempt.outcome for attempt in selected.attempts] == ["no-route-found", "accepted"]
    assert selected.attempts[0].search_failure == "E_PRESENTATION_ROUTE_LIMIT"
