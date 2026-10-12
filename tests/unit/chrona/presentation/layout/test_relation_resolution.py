"""Real selector controls for staged obstacle relaxation, not terminal completion."""
import pytest

from chrona.presentation.layout.model import RelationUnroutableMode as Mode
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_resolution import (
    RelationResolutionStage as Stage, relaxed_domain, search_relation_resolution,
)
from chrona.presentation.layout.relation_shapes import shape_channels
from chrona.presentation.layout.routing import select_relation_route


PAIR = (ConnectorEgress("end", (10., 50.), (10., 50.), ()),
        ConnectorEgress("start", (90., 50.), (90., 50.), ()))


def _resolve(mode, index, *, hosts=frozenset(), reject=False, budget=None):
    def attempt(domain):
        return select_relation_route((PAIR,), obstacles=domain.obstacles,
            bounds=(0., 0., 100., 100.), source_host_id=None, target_host_id=None,
            relation_scene_id="relation:synthetic", max_bends=4, max_detour_ratio=10.,
            classes=("mark", "text", "label-visual"), search_policy="first-fit",
            channels=shape_channels(domain.obstacles, bounds=(0., 0., 100., 100.),
                                    row_edges=(), classes=("mark", "text", "label-visual")),
            search_budget=budget, accept=lambda points: not reject,
            rank=lambda points, source, target: (len(points), points))
    return search_relation_resolution(mode, obstacles=index, endpoint_host_ids=hosts, attempt=attempt)


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
    result = _resolve(mode, SurfaceObstacleIndex())
    assert not result.attempts and result.terminal_fallback is stage


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
