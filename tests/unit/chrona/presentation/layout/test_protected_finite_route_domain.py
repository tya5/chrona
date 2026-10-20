"""Critical guarantees exhaust the declared domain, not continuous space."""
import json

from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_shapes import RelationShapeChannels
from chrona.presentation.layout.routing import select_relation_route


def _select(*, pairs=None, obstacles=None, protected=True, accept=None, search_policy="first-fit", rank=None,
            bounds=(-2., -2., 12., 12.), channels=None, protected_lead_runs=None,
            max_bends=0, search_budget=1, prepare=None):
    pairs = pairs or ((ConnectorEgress("end", (0., 0.), (0., 0.), ()),
                       ConnectorEgress("start", (10., 10.), (10., 10.), ())),)
    return select_relation_route(pairs, obstacles=obstacles or SurfaceObstacleIndex(),
        bounds=bounds, channels=channels, protected_lead_runs=protected_lead_runs,
        source_host_id=None, target_host_id=None,
        relation_scene_id="critical", max_bends=max_bends, max_detour_ratio=2.,
        search_policy=search_policy, search_budget=search_budget, protected=protected, accept=accept, rank=rank,
        prepare=prepare)


def test_safe_quality_fallback_outlives_ordinary_budget_and_keeps_measurements():
    assert _select(protected=False).selected_pair is None
    selected = _select()
    assert selected.selected_pair is not None
    assert selected.budget_hit  # Ordinary work receipt is unchanged, not forged.
    evidence = selected.critical_evidence
    assert not evidence.exhausted  # Quality lower bound proves no eligible alternative.
    assert evidence.quality_fallback.search_disposition == "quality-infeasible"
    assert evidence.quality_fallback.bends > evidence.quality_fallback.max_bends
    code, payload = evidence.diagnostic("critical").split(":", 1)
    assert code == "I_LAYOUT_CRITICAL_RELATION_QUALITY_FALLBACK"
    assert json.loads(payload)["searchDomain"] == "finite-port-event"


def test_later_quality_eligible_pair_beats_safe_over_quality_candidate():
    start = ConnectorEgress("end", (0., 0.), (0., 0.), ())
    pairs = ((start, ConnectorEgress("start", (10., 10.), (10., 10.), ())),
             (start, ConnectorEgress("below", (10., 0.), (10., 0.), ())))
    selected = _select(pairs=pairs)
    assert selected.selected_pair == pairs[1]
    assert selected.critical_evidence.quality_fallback is None
    assert not selected.critical_evidence.exhausted


def test_true_domain_exhaustion_has_distinct_diagnostic_and_no_quota_claim():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("wall", "mark", "timeline", ObstacleRect(4., -3., 6., 13.)))
    selected = _select(obstacles=obstacles)
    assert selected.selected_pair is None
    assert selected.critical_evidence.exhausted
    assert selected.critical_evidence.quality_fallback is None
    assert selected.critical_evidence.diagnostic("critical").startswith(
        "W_LAYOUT_CRITICAL_RELATION_SEARCH_DOMAIN_EXHAUSTED:")
    failures = json.loads(selected.critical_evidence.diagnostic("critical").split(":", 1)[1])["failureEvidence"]
    assert failures
    assert all(item["searchFailure"] != "E_PRESENTATION_ROUTE_LIMIT" for item in failures)


def test_completed_safety_rejection_is_never_waived_by_quality_fallback():
    selected = _select(accept=lambda path: False)
    assert selected.selected_pair is None
    assert selected.critical_evidence.exhausted


def test_protected_best_compares_eligible_pairs_with_existing_rank():
    start = ConnectorEgress("end", (0., 0.), (0., 0.), ())
    pairs = tuple((start, ConnectorEgress(side, point, point, ()))
                  for side, point in (("start", (10., 10.)), ("above", (0., 10.)), ("below", (10., 0.))))
    selected = _select(pairs=pairs, search_policy="best", rank=lambda path, source, target: (target.side != "below",))
    assert selected.selected_pair == pairs[2]
    assert sum(item.outcome == "accepted" for item in selected.attempts) == 1
    assert any(item.outcome == "eligible-not-selected" for item in selected.attempts)


def test_first_fit_safe_fallback_keeps_first_pair_while_best_retains_rank():
    start = ConnectorEgress("end", (0., 0.), (0., 0.), ())
    pairs = ((start, ConnectorEgress("start", (10., 10.), (10., 10.), ())),
             (start, ConnectorEgress("above", (2., 2.), (2., 2.), ())))
    assert _select(pairs=pairs).selected_pair == pairs[0]
    assert _select(pairs=pairs, search_policy="best",
                   rank=lambda path, source, target: (target.side != "above",)).selected_pair == pairs[1]


def test_blocked_egress_domain_is_exhausted_without_entering_search():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("blocked-exit", "mark", "timeline", ObstacleRect(.5, -.5, 1.5, .5)))
    obstacles.add(SurfaceObstacle("source-host", "mark", "timeline", ObstacleRect(-1., -.5, 0., .5)))
    pairs = ((ConnectorEgress("end", (0., 0.), (2., 0.), ("source-host",)),
              ConnectorEgress("start", (10., 10.), (10., 10.), ())),)
    selected = _select(pairs=pairs, obstacles=obstacles)
    assert selected.selected_pair is None
    assert selected.critical_evidence.exhausted
    assert selected.critical_evidence.expansions == 0
    assert not selected.search_used


def _barrier_selection(*, prepare=None, preserves=False, barriers=True, extra_pair=False,
                       accept=None):
    rect = ObstacleRect(-10., 4., 10., 6.)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("required", "mark", "timeline", rect))
    start = ConnectorEgress("end", (0., 0.), (0., 0.), ())
    target = ConnectorEgress("start", (0., 10.), (0., 10.), ())
    pairs = ((start, target),)
    if extra_pair:
        pairs += ((start, ConnectorEgress("above", (-15., 0.), (-15., 0.), ())),)
    return select_relation_route(pairs, obstacles=obstacles, bounds=(-20., -2., 20., 12.),
        source_host_id=None, target_host_id=None, relation_scene_id="critical",
        max_bends=4, max_detour_ratio=2., search_policy="first-fit", search_budget=1,
        protected=True, prepare=prepare, accept=accept, endpoint_preserving_prepare=preserves,
        protected_quality_barriers=(lambda source, target: (rect,)) if barriers else None)


def test_required_interior_proves_detour_infeasible_without_exhausting_paths():
    result = _barrier_selection()
    evidence = result.critical_evidence
    assert result.selected_pair is not None and result.budget_hit
    assert not evidence.exhausted
    assert evidence.quality_fallback.search_disposition == "quality-infeasible"
    assert evidence.quality_fallback.length > 2 * evidence.quality_fallback.direct_length
    assert evidence.expansions == 0  # A finite shape is already hard-safe.


def test_detour_proof_still_searches_later_pairs_for_quality_eligible_path():
    result = _barrier_selection(extra_pair=True)
    assert result.selected_pair[1].semantic_port == (-15., 0.)
    assert result.critical_evidence.quality_fallback is None


def test_detour_proof_is_disabled_when_preparation_may_move_endpoints(monkeypatch):
    from chrona.presentation.layout import routing

    def unexpected_bound(*args):
        raise AssertionError("opaque completion cannot use semantic-endpoint proof")
    monkeypatch.setattr(routing, "rectangular_detour_lower_bound", unexpected_bound)
    # An admissible completion moves the target to the same side of the barrier.
    result = _barrier_selection(prepare=lambda points, source, target: ((0., 0.), (0., 2.)))
    assert result.selected_pair is not None


def test_detour_proof_remains_available_for_endpoint_preserving_completion():
    result = _barrier_selection(prepare=lambda points, source, target: points, preserves=True)
    assert result.critical_evidence.quality_fallback.search_disposition == "quality-infeasible"


def test_detour_proof_does_not_claim_a_safe_path_when_full_validation_rejects(monkeypatch):
    from chrona.presentation.layout import route_search

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", lambda *args, **kwargs:
        iter((((0., 0.), (-12., 0.), (-12., 10.), (0., 10.)),)))
    result = _barrier_selection(accept=lambda path: False)
    assert result.selected_pair is None
    assert result.critical_evidence.exhausted
    assert result.critical_evidence.quality_fallback is None


def test_protected_graph_searches_between_minimum_lead_tips(monkeypatch):
    from chrona.presentation.layout import route_search

    source = ConnectorEgress("end", (0., 0.), (2., 0.), ("source-host",))
    target = ConnectorEgress("start", (20., 10.), (18., 10.), ("target-host",))
    pairs = ((source, target),)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("source-host", "mark", "timeline", ObstacleRect(-10., -10., -9., -9.)))
    obstacles.add(SurfaceObstacle("target-host", "mark", "timeline", ObstacleRect(30., 30., 31., 31.)))
    graph_queries = []

    def candidates(start, end, obstacles, **kwargs):
        if kwargs["limit"] is None:
            graph_queries.append((start, end))
            assert (start, end) == ((5., 0.), (15., 10.))
            yield ((5., 0.), (5., 10.), (15., 10.))

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", candidates)
    channels = RelationShapeChannels((0., 10., 20.), (0., 10., 20.))
    prepared, accepted = [], []
    def prepare(points, *_):
        prepared.append(points)
        return points
    def accept(points):
        accepted.append(points)
        return (5., 0.) in points and points[0] == (0., 0.) and points[-1] == (20., 10.)
    selected = _select(pairs=pairs, obstacles=obstacles, protected=True, search_policy="best", search_budget=1,
        bounds=(0., 0., 20., 20.), channels=channels,
        protected_lead_runs=lambda left, right: (3., 3.),
        max_bends=4,
        prepare=prepare, accept=accept)

    assert graph_queries == [((5., 0.), (15., 10.))]
    assert selected.selected_pair == pairs[0], (selected.attempts, prepared, accepted)
    assert selected.points == ((0., 0.), (2., 0.), (5., 0.), (5., 10.), (18., 10.), (20., 10.))
    assert selected.critical_evidence is not None


def test_short_straight_protected_shape_precedes_overlapping_lead_query(monkeypatch):
    from chrona.presentation.layout import route_search

    source = ConnectorEgress("end", (0., 0.), (0., 0.), ())
    target = ConnectorEgress("start", (10., 0.), (10., 0.), ())
    pairs = ((source, target),)
    graph_queries = []

    def candidates(start, end, obstacles, **kwargs):
        if kwargs["limit"] is None:
            graph_queries.append((start, end))
            return iter(())
        return iter(())

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", candidates)
    channels = RelationShapeChannels((0., 10.), (0., 10.))
    selected = _select(pairs=pairs, protected=True, search_policy="best", search_budget=1,
        bounds=(0., 0., 10., 10.), channels=channels,
        protected_lead_runs=lambda left, right: (6., 6.),
        max_bends=0,
        prepare=lambda points, *_: points,
        accept=lambda points: points[0] == (0., 0.) and points[-1] == (10., 0.)
            and all(point[1] == 0. for point in points))

    assert selected.selected_pair == pairs[0]
    assert selected.points == ((0., 0.), (10., 0.))
    assert graph_queries == []
