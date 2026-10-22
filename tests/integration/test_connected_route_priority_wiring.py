"""A connected recovery precedes a paired stub; stubs stay the last resort (#1908)."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout import surface_route_label_plan as route_plan
from chrona.presentation.layout import surface_routes as routes
from chrona.presentation.layout.member_name_yield import MemberNameYieldResult
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle
from chrona.presentation.model.info_diagnostics import RelationResolutionInfo, RelationResolutionStage
from tests.support import synthetic_review as sr
from tests.integration.test_synthetic_lane_route_corridors import _parts

_TASKS = (
    ("a0", "team-0", "2026-01-02", "2026-01-06"),
    ("b0", "team-0", "2026-01-10", "2026-01-14"),
    ("a1", "team-1", "2026-03-02", "2026-03-06"),
    ("b1", "team-1", "2026-03-10", "2026-03-14"),
)
_NAME = "member-label:synthetic-name"


def _project():
    objects = {}
    for object_id, owner, start, end in _TASKS:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        objects[object_id] = sr.span(object_id, first, (last - first).days,
                                     owner=owner, title=f"Task {object_id}")
    return sr.project(objects, [
        {"id": "r0", "type": "dependency", "from": {"object": "a0", "endpoint": "end"},
         "to": {"object": "b0", "endpoint": "start"}},
        {"id": "r1", "type": "dependency", "from": {"object": "a1", "endpoint": "end"},
         "to": {"object": "b1", "endpoint": "start"}},
    ])


@pytest.fixture
def blocked(tmp_path, monkeypatch):
    """The pre-route baseline of a relax render, plus one hard name group across r1's rows."""
    captured = []
    compose = route_plan.compose_surface_routes

    def snapshot(context):
        captured.append(replace(context, obstacles=context.obstacles.copy(), member_name_yield=None))
        return compose(replace(context, member_name_yield=None))

    monkeypatch.setattr(route_plan, "compose_surface_routes", snapshot)
    seed = tmp_path / "seed"
    seed.mkdir()
    sr.render(seed, _project(), presentation=_parts(unroutable="relax"))
    context, = captured
    index = context.obstacles.copy()
    first, second = (next(mark for mark in context.marks if mark.source_ref == name) for name in ("a1", "b1"))
    wall_left = float(first.bounds.inline + first.bounds.inline_size) + 22
    wall_right = float(second.bounds.inline) - 22
    top, left_, _, height = context.timeline_bounds[1], context.timeline_bounds[0], 0, context.timeline_bounds[3]
    assert wall_left < wall_right
    # a full-height wall between r1's endpoints: nothing can route around it, but the short
    # stub fragments at each endpoint stay on their own side of it
    index.add(SurfaceObstacle(_NAME, "label-visual", "timeline", ObstacleRect(wall_left, top, wall_right, top + height)))
    return replace(context, obstacles=index,
                   required_label_obstacle_ids=context.required_label_obstacle_ids | {_NAME},
                   yieldable_name_ids=frozenset({_NAME}))


def _r1(batch):
    return [item for item in batch.relations if item.relation_id.startswith("relation:relation:id:r1:")]


def _stages(batch):
    return {info.relation_id: info.stage for info in batch.resolution_info
            if isinstance(info, RelationResolutionInfo)}


def _yielding(blocked_context, calls, *, accept):
    def yield_name(request, index):
        calls.append(request)
        if not accept:
            return None
        return MemberNameYieldResult(index.copy(excluded_ids=request.blocker_ids), blocked_context.text,
                                     blocked_context.required_label_obstacle_ids - set(request.blocker_ids))
    return yield_name


def test_a_route_only_the_member_name_blocks_is_connected_not_stubbed(blocked):
    calls = []
    batch = routes.compose_surface_routes(replace(blocked, member_name_yield=_yielding(blocked, calls, accept=True)))
    r1 = _r1(batch)
    assert len(r1) == 1 and not r1[0].suppressed and r1[0].from_instance_id and r1[0].to_instance_id
    assert not any(item.fragment_endpoint for item in batch.relations)
    assert _stages(batch)[r1[0].relation_id] is RelationResolutionStage.EDGE
    assert len(calls) == 1 and calls[0].blocker_ids == (_NAME,) and calls[0].protected_ink
    assert all(item.obstacle_class == "dependency-route" for item in calls[0].protected_ink)
    # the first relation was routed normally and is untouched by the later yield
    assert RelationResolutionStage.STUB not in set(_stages(batch).values())


def test_a_refused_yield_falls_back_to_the_last_resort_stub_without_refusing_the_render(blocked):
    calls = []
    batch = routes.compose_surface_routes(replace(blocked, member_name_yield=_yielding(blocked, calls, accept=False)))
    assert calls
    assert {item.fragment_endpoint for item in _r1(batch)} == {"source", "target"}
    assert RelationResolutionStage.STUB in set(_stages(batch).values())


def test_a_blocker_that_is_not_a_yieldable_name_is_never_offered_to_the_yield(blocked):
    calls = []
    batch = routes.compose_surface_routes(replace(blocked, yieldable_name_ids=frozenset(),
        member_name_yield=_yielding(blocked, calls, accept=True)))
    assert not calls
    assert {item.fragment_endpoint for item in _r1(batch)} == {"source", "target"}


def test_without_a_yield_owner_the_stub_is_unchanged(blocked):
    batch = routes.compose_surface_routes(replace(blocked, member_name_yield=None))
    assert {item.fragment_endpoint for item in _r1(batch)} == {"source", "target"}


def test_an_ink_that_a_stale_yield_leaves_blocked_is_discarded_for_the_stub(blocked):
    def stale(request, index):
        return MemberNameYieldResult(index, blocked.text, blocked.required_label_obstacle_ids)

    batch = routes.compose_surface_routes(replace(blocked, member_name_yield=stale))
    assert {item.fragment_endpoint for item in _r1(batch)} == {"source", "target"}


def test_edge_stage_is_the_diagnosed_recovery_for_a_route_only_closed_contact_blocks(blocked, monkeypatch):
    """Closed contact fails every stage above `edge`; the same route then completes there, haloed."""
    real = routes._primary_mark_contact_is_clear

    def strict_unless_edge(parts, bounds, **kwargs):
        # model a corpus case whose only route slides along its host edge: the strict rule rejects
        # every candidate; the edge exception evaluates the true geometry
        return real(parts, bounds, **kwargs) if kwargs.get("edge_contact") else False

    monkeypatch.setattr(routes, "_primary_mark_contact_is_clear", strict_unless_edge)
    unblocked = replace(blocked, obstacles=blocked.obstacles.copy(excluded_ids=(_NAME,)),
                        required_label_obstacle_ids=blocked.required_label_obstacle_ids - {_NAME})
    batch = routes.compose_surface_routes(replace(unblocked, member_name_yield=None))
    stages = _stages(batch)
    assert stages and set(stages.values()) == {RelationResolutionStage.EDGE}
    assert not any(item.fragment_endpoint for item in batch.relations)
    assert len([item for item in batch.relations if item.from_instance_id]) == 2
