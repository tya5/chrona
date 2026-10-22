"""Router-boundary checks for a required member-name yield (#1841)."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout import surface_route_label_plan as route_plan
from chrona.presentation.layout import surface_routes as routes
from chrona.presentation.layout.member_name_yield import (
    MemberNameYieldResult, endpoint_candidate_blocker_ids, endpoint_candidate_ink,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_routes import prepare_normal_relation_routes
from tests.support import synthetic_review as sr
from tests.integration.test_synthetic_lane_route_corridors import _parts


_TASKS = (
    ("a0", "team-0", "2026-01-02", "2026-01-06"),
    ("b0", "team-0", "2026-01-10", "2026-01-14"),
    ("a1", "team-1", "2026-03-02", "2026-03-06"),
    ("b1", "team-1", "2026-03-10", "2026-03-14"),
)


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


def _seed_context(tmp_path, monkeypatch):
    captured = []
    compose = route_plan.compose_surface_routes

    def snapshot(context):
        # The saved index is the pre-route baseline; the seed render below may
        # then mutate its own inventory while completing both stub relations.
        captured.append(replace(context, obstacles=context.obstacles.copy(), member_name_yield=None))
        return compose(replace(context, member_name_yield=None))

    monkeypatch.setattr(route_plan, "compose_surface_routes", snapshot)
    seed_directory = tmp_path / "seed"
    seed_directory.mkdir()
    seed = sr.render(seed_directory, _project(), presentation=_parts(unroutable="stub"))
    context, = captured
    return context, seed


def _blocked_context(context, blocker_id="member-label:synthetic-name"):
    index = context.obstacles.copy()
    row_marks = [mark for mark in context.marks if mark.source_ref in {"a1", "b1"}]
    top = min(float(mark.bounds.block) for mark in row_marks) - 1
    bottom = max(float(mark.bounds.block + mark.bounds.block_size) for mark in row_marks) + 1
    left, _, width, _ = context.timeline_bounds
    index.add(SurfaceObstacle(blocker_id, "label-visual", "timeline",
                              ObstacleRect(left, top, left + width, bottom)))
    required = context.required_label_obstacle_ids | {blocker_id}
    return replace(context, obstacles=index, required_label_obstacle_ids=required), blocker_id


def _relation_paths(seed, prefix):
    return {item.scene_id: item.points for item in seed.surface.primitives
            if item.kind == "Path" and item.source_kind == "relation"
            and item.scene_id.startswith(prefix)}


def test_yield_waits_for_admissible_stub_exhaustion_and_preserves_completed_route(
        tmp_path, monkeypatch):
    context, seed = _seed_context(tmp_path, monkeypatch)
    context, blocker_id = _blocked_context(context)
    prepared = prepare_normal_relation_routes(context)
    expected_stub_candidates = 1 + len(prepared.entries[1].occurrences[0].port_pairs)
    pair_calls = []
    original_pair = routes.paired_stub_geometry

    def count_pair(*args, **kwargs):
        pair_calls.append(None)
        return original_pair(*args, **kwargs)

    monkeypatch.setattr(routes, "paired_stub_geometry", count_pair)
    requests = []
    checked_ink = []
    check_blockers = routes.endpoint_candidate_blocker_ids

    def record_checked_ink(ink, index):
        checked_ink.append(ink)
        return check_blockers(ink, index)

    monkeypatch.setattr(routes, "endpoint_candidate_blocker_ids", record_checked_ink)

    def yield_name(request, obstacle_index):
        assert len(pair_calls) == expected_stub_candidates
        requests.append(request)
        assert request.blocker_ids == (blocker_id,)
        assert request.protected_ink
        # The discovery check and the owner request share the same immutable
        # candidate ink; post-yield validation must inspect it again unchanged.
        assert any(ink is request.protected_ink for ink in checked_ink)
        assert all(item.obstacle_class == "dependency-route"
                   and item.route_owner_id.startswith("relation:relation:id:r1:")
                   for item in request.protected_ink)
        assert any(isinstance(item.geometry, ObstacleSegment) and item.geometry.stroke_width > 0
                   for item in request.protected_ink)
        assert any(isinstance(item.geometry, ObstacleRect) for item in request.protected_ink)
        # r0 is already complete when the r1 callback is offered its protected
        # candidate; yielding a name must not restart or erase that route.
        prior_owners = {item.route_owner_id for item in obstacle_index.all()
                        if item.obstacle_class == "dependency-route"}
        assert any(owner and owner.startswith("relation:relation:id:r0:") for owner in prior_owners)
        cleaned = obstacle_index.copy(excluded_ids=(blocker_id,))
        assert any(item.route_owner_id in prior_owners for item in cleaned.all()
                   if item.obstacle_class == "dependency-route")
        return MemberNameYieldResult(cleaned, context.text,
                                     context.required_label_obstacle_ids - {blocker_id})

    completed = routes.compose_surface_routes(replace(context, member_name_yield=yield_name))
    assert len(requests) == 1
    baseline_first = _relation_paths(seed, "relation:relation:id:r0:")
    completed_first = {item.relation_id: item.points for item in completed.relations
                       if item.relation_id.startswith("relation:relation:id:r0:")}
    assert completed_first == baseline_first
    second = [item for item in completed.relations
              if item.relation_id.startswith("relation:relation:id:r1:")]
    assert len(second) == 2 and all(not item.suppressed for item in second)


def test_head_only_required_text_collision_blocks_candidate_ink():
    marker = marker_geometry({"shape": "open-triangle", "headLength": 8,
                              "headWidth": 6, "paintMode": "stroke"}, stroke_width=2)
    assert marker is not None
    ink = endpoint_candidate_ink(
        "relation:test", ((0.0, 0.0), (20.0, 0.0)), ((20.0, 0.0), (40.0, 0.0)),
        marker, None, 2.0,
    )
    head = next(item.geometry for item in ink
                if isinstance(item.geometry, ObstacleRect) and item.route_owner_id == "relation:test")
    line_only = SurfaceObstacleIndex()
    for item in ink:
        if isinstance(item.geometry, ObstacleSegment):
            line_only.add(item)

    # Find a tiny text box inside the painted head bounds but outside every
    # route stroke segment: this distinguishes terminal ink from its lead.
    left, top, right, bottom = head.left, head.top, head.right, head.bottom
    text_box = None
    for row in range(24):
        for column in range(24):
            x = left + (right - left) * (column + 0.2) / 24
            y = top + (bottom - top) * (row + 0.2) / 24
            candidate = ObstacleRect(x, y, x + 0.1, y + 0.1)
            if not line_only.collisions(candidate, classes=("dependency-route",)):
                text_box = candidate
                break
        if text_box is not None:
            break
    assert text_box is not None

    required_text = SurfaceObstacleIndex()
    required_text.add(SurfaceObstacle("member-label:head-only", "text", "timeline", text_box))
    assert endpoint_candidate_blocker_ids(ink, required_text) == ("member-label:head-only",)
    # An unchanged/stale owner snapshot still blocks the exact same head ink;
    # it cannot be converted into an admissible route by the yield response.
    assert endpoint_candidate_blocker_ids(ink, required_text.copy()) == ("member-label:head-only",)


def test_physical_host_failure_does_not_offer_member_name_yield(tmp_path, monkeypatch):
    context, _ = _seed_context(tmp_path, monkeypatch)
    context, blocker_id = _blocked_context(context)
    calls = []

    def refuse_if_offered(request, obstacle_index):
        calls.append(request)
        return None

    monkeypatch.setattr(routes, "_stub_fragment_clears_physical_hosts",
                        lambda *args, **kwargs: False)
    with pytest.raises(LayoutError, match="paired stub endpoint corridors are unavailable"):
        routes.compose_surface_routes(replace(context, member_name_yield=refuse_if_offered))
    assert blocker_id not in {identity for request in calls for identity in request.blocker_ids}
    assert not calls


@pytest.mark.parametrize("response", ["none", "stale"])
def test_none_or_still_blocked_yield_result_keeps_stub_refusal(tmp_path, monkeypatch, response):
    context, _ = _seed_context(tmp_path, monkeypatch)
    context, blocker_id = _blocked_context(context)
    calls = []

    def yield_name(request, obstacle_index):
        calls.append(request)
        assert request.blocker_ids == (blocker_id,)
        if response == "none":
            return None
        # A result object is not authority to waive an unresolved required-ink
        # collision; the exact blocking geometry remains in this snapshot.
        return MemberNameYieldResult(obstacle_index, context.text,
                                    context.required_label_obstacle_ids)

    with pytest.raises(LayoutError, match="paired stub endpoint corridors are unavailable"):
        routes.compose_surface_routes(replace(context, member_name_yield=yield_name))
    assert calls


def test_nonmember_name_blocker_refusal_is_not_treated_as_a_yield(tmp_path, monkeypatch):
    context, _ = _seed_context(tmp_path, monkeypatch)
    context, blocker_id = _blocked_context(context, "label-footprint:unowned-decoration")
    requests = []

    def owner_refuses_unregistered_name(request, obstacle_index):
        requests.append(request)
        assert request.blocker_ids == (blocker_id,)
        return None  # No registered member-name owner can authorize this identity.

    with pytest.raises(LayoutError, match="paired stub endpoint corridors are unavailable"):
        routes.compose_surface_routes(replace(context, member_name_yield=owner_refuses_unregistered_name))
    assert requests
