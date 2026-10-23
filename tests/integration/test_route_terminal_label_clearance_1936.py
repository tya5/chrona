"""Ordinary relation terminal ink stays clear of retained labels (#1936 row 4)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

import chrona.presentation.layout.surface_route_label_plan as route_plan
from chrona.presentation.layout.member_name_yield import (
    endpoint_candidate_blocker_ids,
    route_candidate_ink,
)
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.relation_terminals import marker_ink_bounds
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.layout import surface_routes as routes
from chrona.presentation.layout.relation_resolution import RelationSearchResolution
from chrona.presentation.model.info_diagnostics import RelationResolutionStage
from chrona.presentation.layout.surface_routes import SurfaceRoutesContext, compose_surface_routes
from tests.support import synthetic_review as sr


def _project():
    first = date(2026, 1, 5)
    return sr.project({
        "source": sr.span("source", first, 8, owner="team-a", title="Source"),
        "target": sr.span("target", date(2026, 2, 2), 8, owner="team-b", title="Target"),
    }, [{"id": "depends", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}])


def _parts(*, unroutable="suppress", style=None):
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})["search"] = "best"
    parts["layout"]["relationRouting"]["unroutable"] = unroutable
    if style is not None:
        parts["layout"]["relationRouting"]["style"] = style
    return parts


def _captured_context(tmp_path, monkeypatch, *, unroutable="suppress", style=None) -> tuple[SurfaceRoutesContext, object]:
    captured = {}
    original = route_plan.compose_surface_routes

    def observe(context):
        # Routing registers accepted route paint into its index, so retain an independent
        # pre-route snapshot for the controlled second composition below.
        captured["context"] = replace(context, obstacles=context.obstacles.copy())
        result = original(context)
        captured["routes"] = result
        return result

    monkeypatch.setattr(route_plan, "compose_surface_routes", observe)
    rendered = sr.render(tmp_path, _project(), presentation=_parts(unroutable=unroutable, style=style))
    assert rendered.surface is not None
    context = captured["context"]
    assert isinstance(context, SurfaceRoutesContext)
    assert captured["routes"].relations
    assert any(item.purpose == "member-label" for item in rendered.surface.primitives)
    return context, rendered


def _stroke_width(context):
    role = semantic_binding("dependency").theme_role
    return float(context.request.theme_tokens.number(role, "strokeWidth"))


def _off_axis_patch(bounds, points, width):
    """Choose a small patch inside terminal bounds, away from every centerline segment."""
    left, top, right, bottom = bounds
    size = min(1.0, (right - left) / 4, (bottom - top) / 4)
    for row in range(1, 4):
        for col in range(1, 4):
            x = left + (right - left) * col / 4
            y = top + (bottom - top) * row / 4
            box = ObstacleRect(x - size / 2, y - size / 2, x + size / 2, y + size / 2)
            obstacle = SurfaceObstacle("candidate-label", "text", "timeline", box)
            inventory = SurfaceObstacleIndex()
            inventory.add(obstacle)
            # Existing centerline clearance must pass while the exact completed terminal
            # envelope still names this obstacle as a blocker.
            from chrona.presentation.layout.surface_routes import route_clears_retained_label_ink
            if route_clears_retained_label_ink(points, inventory, width):
                return obstacle
    raise AssertionError((bounds, points, width))


@pytest.mark.parametrize(("obstacle_class", "placement_id"), [
    ("text", "retained-note-text"),
    ("label-visual", "member-label-icon:station"),
    ("label-visual", "member-label-chip:station"),
])
def test_ordinary_route_rejects_terminal_only_label_contact_and_keeps_label(
        tmp_path, monkeypatch, obstacle_class, placement_id):
    context, rendered = _captured_context(tmp_path, monkeypatch)
    initial = compose_surface_routes(context)
    relation, = initial.relations
    assert not relation.suppressed and relation.from_instance_id and relation.to_instance_id
    assert relation.marker_start is not None or relation.marker_end is not None
    scene_route, = (item for item in rendered.surface.primitives
                    if item.scene_id == relation.relation_id)
    assert scene_route.points == relation.points
    assert scene_route.marker_start == relation.marker_start
    assert scene_route.marker_end == relation.marker_end
    assert rendered.artifact.media_type == "image/svg+xml"

    marker = relation.marker_end or relation.marker_start
    side = "end" if relation.marker_end is not None else "start"
    stroke_width = _stroke_width(context)
    bounds = marker_ink_bounds(marker, side=side, points=relation.points,
                               path_commands=relation.path_commands,
                               stroke_width=stroke_width)
    forbidden = _off_axis_patch(bounds, relation.points, stroke_width)
    assert forbidden.placement_id == "candidate-label"

    obstacle = replace(forbidden, placement_id=placement_id, obstacle_class=obstacle_class)
    index = context.obstacles.copy()
    index.add(obstacle)
    constrained = replace(context, obstacles=index,
        required_label_obstacle_ids=context.required_label_obstacle_ids | {placement_id},
        member_name_yield=None, yieldable_name_ids=frozenset())

    # The preexisting straight/centerline test accepts the original route; completed head ink
    # rejects it. Routing must find another ordinary connected pose, not erase the label.
    assert endpoint_candidate_blocker_ids(
        route_candidate_ink(relation.relation_id, relation.points,
            relation.marker_start, relation.marker_end, stroke_width,
            path_commands=relation.path_commands),
        _index((obstacle,))) == (placement_id,)
    rerouted = compose_surface_routes(constrained)
    replacement, = rerouted.relations
    if replacement.suppressed:
        # This fixture declares suppress as its terminal policy. If no alternative fits,
        # the relation must be visibly diagnosed rather than drawn through the retained label.
        warnings = [item for item in rerouted.diagnostics
                    if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]
        assert len(warnings) == 1 and replacement.relation_id in warnings[0]
    else:
        assert replacement.from_instance_id and replacement.to_instance_id
        assert replacement.points != relation.points or replacement.marker_start != relation.marker_start \
            or replacement.marker_end != relation.marker_end
        final_ink = route_candidate_ink(replacement.relation_id, replacement.points,
            replacement.marker_start, replacement.marker_end, stroke_width,
            path_commands=replacement.path_commands)
        assert placement_id not in endpoint_candidate_blocker_ids(final_ink, index)
    assert any(item.purpose == "member-label" for item in rendered.surface.primitives)
    assert index.has(placement_id)


@pytest.mark.parametrize("style", ["orthogonal", "curved", "metro"])
def test_defensive_raw_fallback_boundary_checks_completed_terminal_ink(
        tmp_path, monkeypatch, style):
    context, rendered = _captured_context(tmp_path, monkeypatch, unroutable="relax", style=style)
    # Keep this low-level branch isolated from unrelated axis/member labels: the synthetic
    # retained obstacle below is the only label-content blocker under test.
    non_label_context = replace(context,
        obstacles=context.obstacles.copy(excluded_ids=tuple(item.placement_id
            for item in context.obstacles.all() if item.obstacle_class in {"text", "label-visual"})),
        required_label_obstacle_ids=frozenset(), member_name_yield=None, yieldable_name_ids=frozenset())
    # Inject a lower-level search result to exercise the defensive raw-fallback boundary.
    # Current RELAX search exhausts into OVERLAP, not this result; this is not evidence
    # that ordinary policy selects a raw fallback. It pins complete-ink validation even
    # when candidate preparation and style rejection are bypassed.
    monkeypatch.setattr(routes, "search_relation_resolution", lambda *args, **kwargs:
        RelationSearchResolution((), None))
    baseline = compose_surface_routes(non_label_context)
    route, = baseline.relations
    assert not route.suppressed and route.from_instance_id and route.to_instance_id, baseline.diagnostics

    marker = route.marker_end or route.marker_start
    assert marker is not None
    bounds = marker_ink_bounds(marker, side="end" if route.marker_end is not None else "start",
        points=route.points, path_commands=route.path_commands, stroke_width=_stroke_width(context))
    obstacle = _off_axis_patch(bounds, route.points, _stroke_width(context))
    retained = replace(obstacle, placement_id=f"retained-{style}-text")
    assert endpoint_candidate_blocker_ids(route_candidate_ink(route.relation_id, route.points,
        route.marker_start, route.marker_end, _stroke_width(context),
        path_commands=route.path_commands), _index((retained,))) == (retained.placement_id,)
    assert routes.route_clears_retained_label_ink(route.points, _index((retained,)), _stroke_width(context))

    index = non_label_context.obstacles.copy()
    index.add(retained)
    constrained = replace(non_label_context, obstacles=index,
        required_label_obstacle_ids=frozenset({retained.placement_id}),
        member_name_yield=None, yieldable_name_ids=frozenset())
    blocked = compose_surface_routes(constrained)
    blocked_route, = blocked.relations
    assert blocked_route.suppressed
    assert blocked_route.diagnostic == "W_LAYOUT_RELATION_SUPPRESSED"
    assert any(item == f"W_LAYOUT_RELATION_SUPPRESSED:{blocked_route.relation_id}"
               for item in blocked.diagnostics)
    assert not blocked.visible_route_fallbacks
    assert index.has(retained.placement_id)
    # `rendered` is the unmodified baseline artifact; this controlled second composition proves
    # Layout rejects the candidate. It deliberately makes no claim that the test-only obstacle
    # was emitted into that baseline SVG.
    assert rendered.artifact.media_type == "image/svg+xml"


def _index(obstacles):
    result = SurfaceObstacleIndex()
    for obstacle in obstacles:
        result.add(obstacle)
    return result
