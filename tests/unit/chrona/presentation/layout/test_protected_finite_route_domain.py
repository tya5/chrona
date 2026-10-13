"""Critical guarantees exhaust the declared domain, not continuous space."""
import json

from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.routing import select_relation_route


def _select(*, pairs=None, obstacles=None, protected=True, accept=None, search_policy="first-fit", rank=None):
    pairs = pairs or ((ConnectorEgress("end", (0., 0.), (0., 0.), ()),
                       ConnectorEgress("start", (10., 10.), (10., 10.), ())),)
    return select_relation_route(pairs, obstacles=obstacles or SurfaceObstacleIndex(),
        bounds=(-2., -2., 12., 12.), source_host_id=None, target_host_id=None,
        relation_scene_id="critical", max_bends=0, max_detour_ratio=2.,
        search_policy=search_policy, search_budget=1, protected=protected, accept=accept, rank=rank)


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
