"""Routing consumes completed content once, then completes dependent labels."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.layout.surface_routes import SurfaceRoutesContext, TerminalLabelPlacementError
from chrona.presentation.layout import surface_route_label_plan as plan


def _request(identifier):
    return LabelRequest(identifier, identifier, "Name", LabelRect(0, 0, 4, 4), ("end", "start"),
        "text", "plot-label", CollisionDomain("timeline", "overlay"), "suppress",
        semantic_id="memberLabel")


def _text(identifier):
    return SimpleNamespace(placement_id=identifier, content=identifier, overflow="fit")


def _context(index, calls):
    requests = (_request("optional-a"), _request("optional-b"))
    base_text = (_text("required-label"),)

    def routes_for(obstacles, text):
        calls.append(("context", obstacles, text))
        return SurfaceRoutesContext(None, None, (), (), (), (), (0, 0, 200, 100), None, {}, text, obstacles)

    return plan.RouteLabelPlanContext(None, requests, base_text, index, routes_for)


def test_routes_once_around_completed_content_then_places_terminal_names_and_ordinary_labels(monkeypatch):
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("required-label", "text", "timeline", ObstacleRect(0, 0, 10, 10)))
    calls = []
    routed_indexes = []
    context = _context(index, calls)
    routes_batch = SimpleNamespace(relations=())
    terminal_batch = SimpleNamespace(text=(_text("terminal-label"),), diagnostics=("terminal",),
                                     visible_label_overflows=())
    member_batch = SimpleNamespace(text=(_text("optional-a"), _text("optional-b")), diagnostics=(),
                                    visible_overflows=())
    ordinary_batch = SimpleNamespace(text=(_text("ordinary-label"),), diagnostics=("ordinary",),
                                     visible_label_overflows=())

    def compose_routes(route_context):
        calls.append(("routes", route_context))
        routed_indexes.append(route_context.obstacles)
        assert route_context.progress_pass == "route-content-baseline"
        assert route_context.obstacles is not index
        assert route_context.obstacles.has("required-label")
        assert route_context.text == (_text("required-label"),)
        route_context.obstacles.add(SurfaceObstacle("route-paint", "dependency-route", "timeline",
                                  ObstacleRect(20, 20, 80, 21)))
        return routes_batch

    def place_relation_labels(route_context, routes, *, terminal):
        calls.append(("terminal" if terminal else "ordinary", route_context))
        assert routes is routes_batch
        assert route_context.obstacles is routed_indexes[0]
        if terminal:
            assert route_context.obstacles.has("route-paint")
            route_context.obstacles.add(SurfaceObstacle("terminal-label", "text", "timeline", ObstacleRect(30, 30, 40, 40)))
            return terminal_batch
        assert route_context.obstacles.has("terminal-label")
        assert route_context.obstacles.has("optional-a") and route_context.obstacles.has("optional-b")
        assert route_context.text == (_text("required-label"), _text("terminal-label"),
                                      _text("optional-a"), _text("optional-b"))
        return ordinary_batch

    def place_members(_member_context, requests, obstacles):
        calls.append(("members", obstacles, requests))
        assert obstacles is routed_indexes[0]
        assert requests == context.post_route_requests
        assert obstacles.has("terminal-label")
        assert obstacles.has("route-paint")
        for identifier in ("optional-a", "optional-b"):
            obstacles.add(SurfaceObstacle(identifier, "text", "timeline", ObstacleRect(50, 50, 60, 60)))
        return member_batch

    monkeypatch.setattr(plan, "compose_surface_routes", compose_routes)
    monkeypatch.setattr(plan, "place_relation_labels", place_relation_labels)
    monkeypatch.setattr(plan, "place_member_labels", place_members)

    result = plan.compose_routes_and_member_labels(context)

    assert [event[0] for event in calls] == ["context", "routes", "terminal", "members", "ordinary"]
    assert calls[0][1] is routed_indexes[0]
    assert result.routes is routes_batch
    assert result.members is member_batch
    assert result.obstacles is routed_indexes[0]
    assert result.relation_labels.text == (*terminal_batch.text, *ordinary_batch.text)
    assert result.relation_labels.diagnostics == ("terminal", "ordinary")
    assert result.obstacles.has("required-label")
    assert result.obstacles.has("route-paint")
    assert result.obstacles.has("terminal-label")
    assert result.obstacles.has("optional-a") and result.obstacles.has("optional-b")
    assert not index.has("route-paint")


def test_ordinary_relation_labels_keep_pre_route_names_after_route_completion(monkeypatch):
    index = SurfaceObstacleIndex()
    calls = []
    context = _context(index, calls)
    routes_batch = SimpleNamespace(relations=())
    pre_name = _text("pre-route-name")
    terminal_text = _text("terminal-label")
    post_name = _text("post-route-name")

    class PreRouteNames:
        obstacles = index
        text = (pre_name,)
        required_obstacle_ids = frozenset({"pre-route-name"})
        yieldable_obstacle_ids = frozenset({"pre-route-name"})

        def adopt_obstacles(self, current):
            self.obstacles = current

        def yield_for_endpoint(self, request, current):
            return None

        def finish(self):
            return SimpleNamespace()

    context = replace(context, pre_route_members=PreRouteNames())
    terminal_batch = SimpleNamespace(text=(terminal_text,), diagnostics=(), visible_label_overflows=())
    member_batch = SimpleNamespace(text=(post_name,), diagnostics=(), visible_overflows=())
    ordinary_batch = SimpleNamespace(text=(), diagnostics=(), visible_label_overflows=())

    def compose_routes(route_context):
        assert route_context.text == (_text("required-label"), pre_name)
        return routes_batch

    def place_relation_labels(route_context, routes, *, terminal):
        if terminal:
            return terminal_batch
        assert route_context.text == (_text("required-label"), pre_name, terminal_text, post_name)
        return ordinary_batch

    monkeypatch.setattr(plan, "compose_surface_routes", compose_routes)
    monkeypatch.setattr(plan, "place_relation_labels", place_relation_labels)
    monkeypatch.setattr(plan, "place_member_labels", lambda *_args: member_batch)

    plan.compose_routes_and_member_labels(context)


def test_required_terminal_label_failure_propagates_after_one_route_attempt(monkeypatch):
    index = SurfaceObstacleIndex()
    calls = []
    context = _context(index, calls)

    def routes(_route_context):
        calls.append("routes")
        return SimpleNamespace(relations=())

    def fail_terminal(_route_context, routes_batch, *, terminal):
        calls.append("terminal" if terminal else "ordinary")
        if terminal:
            raise TerminalLabelPlacementError("relation-label:blocked-terminal", routes_batch)
        raise AssertionError("ordinary labels must not run after required terminal failure")

    monkeypatch.setattr(plan, "compose_surface_routes", routes)
    monkeypatch.setattr(plan, "place_relation_labels", fail_terminal)
    monkeypatch.setattr(plan, "place_member_labels", lambda *_args: pytest.fail("member placement must not run"))

    with pytest.raises(TerminalLabelPlacementError, match="relation-label:blocked-terminal"):
        plan.compose_routes_and_member_labels(context)
    assert [event[0] if isinstance(event, tuple) else event for event in calls] == [
        "context", "routes", "terminal"]
