"""Real selector controls for staged obstacle relaxation, not terminal completion."""
import pytest

from chrona.presentation.layout.model import RelationUnroutableMode as Mode
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_resolution import (
    RelationResolutionStage as Stage, RelationRouteAttemptOutcome,
    relaxed_domain, search_relation_resolution,
)
from chrona.presentation.layout.relation_shapes import shape_channels
from chrona.presentation.layout.routing import select_relation_route


PAIR = (ConnectorEgress("end", (10., 50.), (10., 50.), ()),
        ConnectorEgress("start", (90., 50.), (90., 50.), ()))


def _resolve(mode, index, *, hosts=frozenset(), required_labels=frozenset(), reject=False, budget=None):
    def attempt(domain):
        return select_relation_route((PAIR,), obstacles=domain.obstacles,
            bounds=(0., 0., 100., 100.), source_host_id=None, target_host_id=None,
            relation_scene_id="relation:synthetic", max_bends=4, max_detour_ratio=10.,
            classes=("mark", "text", "label-visual"), search_policy="first-fit",
            channels=shape_channels(domain.obstacles, bounds=(0., 0., 100., 100.),
                                    row_edges=(), classes=("mark", "text", "label-visual")),
            search_budget=budget, accept=lambda points: not reject,
            rank=lambda points, source, target: (len(points), points))
    return search_relation_resolution(mode, obstacles=index, endpoint_host_ids=hosts,
        required_label_obstacle_ids=required_labels, attempt=attempt)


@pytest.mark.parametrize("obstacle_class,identity,stage", (
    ("label-visual", "chip", Stage.LABEL_VISUALS),
    ("text", "relation-label:r", Stage.LABEL_VISUALS),
    ("text", "member-label:a", Stage.TEXT),
    ("mark", "planned:blocker", Stage.MARKS),
))
def test_real_blocked_route_succeeds_at_first_permitted_stage(obstacle_class, identity, stage):
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle(identity, obstacle_class, "timeline", ObstacleRect(-1., -1., 101., 101.)))
    before = index.all()
    result = _resolve(Mode.RELAX, index)
    assert result.accepted is not None and result.accepted.stage is stage
    assert result.accepted.selection.points and result.terminal_fallback is None
    assert index.all() == before


def test_endpoint_host_is_preserved_and_exhaustion_requests_terminal_completion():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("host", "mark", "timeline", ObstacleRect(-1., -1., 101., 101.)))
    result = _resolve(Mode.RELAX, index, hosts=frozenset({"host"}))
    assert result.accepted is None
    assert len(result.attempts) == 4
    assert result.terminal_fallback is Stage.OVERLAP
    final = relaxed_domain(index, Stage.MARKS, frozenset({"host"}))
    assert final.obstacles.has("host") and final.required_primary_mark_ids == frozenset({"host"})


def test_suppress_executes_only_normal_attempt():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("blocked", "mark", "timeline", ObstacleRect(-1., -1., 101., 101.)))
    result = _resolve(Mode.SUPPRESS, index)
    assert result.accepted is None and result.terminal_fallback is None
    assert tuple(item.stage for item in result.attempts) == (Stage.NORMAL,)


@pytest.mark.parametrize("mode,stage", ((Mode.OVERLAP, Stage.OVERLAP), (Mode.STUB, Stage.STUB)))
def test_direct_modes_do_not_search(mode, stage):
    result = _resolve(mode, SurfaceObstacleIndex(), required_labels=frozenset({"hard-text"}))
    assert not result.attempts and result.terminal_fallback is stage


@pytest.mark.parametrize("stage", (Stage.LABEL_VISUALS, Stage.TEXT, Stage.MARKS))
def test_staged_relaxation_preserves_only_explicit_required_label_obstacles(stage):
    index = SurfaceObstacleIndex()
    for identity, obstacle_class in (
            ("required-text", "text"),
            ("label-footprint:required-text", "label-visual"),
            ("optional-text", "text"),
            ("label-footprint:optional-text", "label-visual")):
        index.add(SurfaceObstacle(identity, obstacle_class, "timeline",
                                  ObstacleRect(0., 0., 10., 10.)))
    protected = frozenset({"required-text", "label-footprint:required-text"})

    domain = relaxed_domain(index, stage, frozenset(), protected)

    assert domain.obstacles.has("required-text")
    assert domain.obstacles.has("label-footprint:required-text")
    if stage is Stage.LABEL_VISUALS:
        assert domain.obstacles.has("optional-text")
        assert not domain.obstacles.has("label-footprint:optional-text")
    else:
        assert not domain.obstacles.has("optional-text")
        assert not domain.obstacles.has("label-footprint:optional-text")


def test_normal_domain_retains_all_labels_and_empty_protection_preserves_existing_relaxation():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("required-text", "text", "timeline", ObstacleRect(0., 0., 1., 1.)))
    index.add(SurfaceObstacle("label-footprint:required-text", "label-visual", "timeline",
                              ObstacleRect(0., 0., 1., 1.)))
    assert relaxed_domain(index, Stage.NORMAL, frozenset()).obstacles.all() == index.all()
    assert not relaxed_domain(index, Stage.TEXT, frozenset()).obstacles.all()


def test_normal_success_never_retries():
    result = _resolve(Mode.RELAX, SurfaceObstacleIndex())
    assert result.accepted.stage is Stage.NORMAL and len(result.attempts) == 1


def test_each_real_search_stage_has_a_fresh_expansion_ceiling():
    result = _resolve(Mode.RELAX, SurfaceObstacleIndex(), reject=True, budget=1)
    assert len(result.attempts) == 4 and result.accepted is None
    assert all(item.selection.budget_hit and item.selection.search_expansions == 1
               for item in result.attempts)


@pytest.mark.parametrize("stage", (Stage.OVERLAP, Stage.STUB, "marks"))
def test_terminal_or_untyped_stage_is_not_a_search_domain(stage):
    with pytest.raises(ValueError):
        relaxed_domain(SurfaceObstacleIndex(), stage, frozenset())


def test_untyped_mode_is_rejected_not_treated_as_relax():
    with pytest.raises(ValueError):
        _resolve("relax", SurfaceObstacleIndex())


def test_side_entry_completion_keeps_search_receipt_without_forging_acceptance():
    result = _resolve(Mode.RELAX, SurfaceObstacleIndex(), reject=True, budget=1)
    receipt = result.attempts[0].search_receipt
    assert receipt.selected_pair is None and receipt.budget_hit
    outcome = RelationRouteAttemptOutcome(receipt, PAIR,
        ((10., 50.), (90., 50.)), used_back_route=True)
    assert outcome.search_receipt is receipt and outcome.selected_pair == PAIR
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        RelationRouteAttemptOutcome(receipt, PAIR, outcome.points)
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        RelationRouteAttemptOutcome(receipt, None, (), used_back_route=True)
