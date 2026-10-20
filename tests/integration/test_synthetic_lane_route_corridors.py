"""Synthetic content-first member names stay clear of completed route paint."""
from __future__ import annotations

from datetime import date

import pytest

import chrona.presentation.layout.surface_composer as composer
from chrona.presentation.layout import surface_route_label_plan as label_plan
from tests.support import synthetic_review as sr


WALL = {"l0-t0": ("2026-01-20", "2026-02-09", "team-0"), "l1-t0": ("2026-01-23", "2026-02-07", "team-1"),
        "l2-t0": ("2026-01-20", "2026-02-02", "team-2"), "l3-t0": ("2026-01-06", "2026-01-20", "team-3"),
        "l3-t1": ("2026-02-12", "2026-03-07", "team-3"), "l3-t2": ("2026-04-02", "2026-04-21", "team-3")}
WALL_RELATION = ("l1-t0", "l3-t1")
COSTLY = {"l0-t0": ("2026-01-12", "2026-02-05", "team-0"), "l1-t0": ("2026-01-09", "2026-02-02", "team-1"),
          "l1-t1": ("2026-02-15", "2026-03-03", "team-1"), "l2-t0": ("2026-01-09", "2026-01-18", "team-2"),
          "l2-t1": ("2026-02-02", "2026-02-12", "team-2"), "l2-t3": ("2026-04-11", "2026-04-21", "team-2"),
          "l3-t0": ("2026-01-20", "2026-02-10", "team-3")}
COSTLY_RELATION = ("l3-t0", "l1-t1")


def _project(spans, relation):
    objects = {}
    for key, (start, end, owner) in spans.items():
        first = date.fromisoformat(start)
        objects[key] = sr.span(key, first, (date.fromisoformat(end) - first).days, owner=owner,
                               title=f"Task title {key[1]}.{key[-1]}")
    source, target = relation
    return sr.project(objects, [{"id": "r0", "type": "dependency", "lag": "0d",
                                 "from": {"object": source, "endpoint": "end"},
                                 "to": {"object": target, "endpoint": "start"}}])


def _parts(*, entry: str | None = None, unroutable="relax"):
    parts = sr.bundle()
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})["search"] = "best"
    parts["layout"]["relationRouting"]["unroutable"] = unroutable
    parts["view"] = sr.lane_view(parts["view"])
    if entry is not None:
        parts["layout"]["relationRouting"]["entry"] = entry
    return parts


def _render_and_compare(tmp_path, source, monkeypatch, *, entry=None, unroutable="relax", label_sides=None):
    captured = {}
    original = composer.compose_routes_and_member_labels
    def observe(context):
        clean_before = tuple(context.clean_obstacles.all())
        captured["context"] = context
        completed = original(context)
        assert tuple(context.clean_obstacles.all()) == clean_before
        captured["completed"] = completed
        return completed
    monkeypatch.setattr(composer, "compose_routes_and_member_labels", observe)
    route_calls = []
    compose_routes = label_plan.compose_surface_routes
    def observe_routes(context):
        route_calls.append(context)
        return compose_routes(context)
    monkeypatch.setattr(label_plan, "compose_surface_routes", observe_routes)
    parts = _parts(entry=entry, unroutable=unroutable)
    if label_sides:
        parts["view"]["body"]["visibility"]["fallback"]["labels"] = label_sides
        parts["layout"]["reviewSurface"]["rowDistribution"] = "fill"
    rendered = sr.render(tmp_path, source, presentation=parts)
    completed = captured["completed"]
    assert len(route_calls) == 1
    assert route_calls[0].progress_pass == "route-content-baseline"
    assert route_calls[0].obstacles is completed.obstacles
    names = tuple(item for item in captured["context"].base_text if item.semantic_id == "memberLabel")
    assert names
    name_ids = frozenset(identifier for item in names
        for identifier in (item.placement_id, f"label-footprint:{item.placement_id}"))
    assert name_ids <= route_calls[0].required_label_obstacle_ids
    assert all(completed.obstacles.has(identifier) for identifier in name_ids)
    assert not captured["context"].clean_obstacles.select(classes=("dependency-route",))
    return rendered, captured["context"], completed


def _routes(rendered):
    return [item for item in rendered.surface.primitives if item.scene_id.startswith("relation:")]


def _names(rendered):
    return [item for item in rendered.surface.primitives if item.purpose == "member-label"]


def _segment_hits_box(start, end, box) -> bool:
    left, top, width, height = box
    right, bottom = left + width, top + height
    if start[0] == end[0]:
        return left < start[0] < right and min(start[1], end[1]) < bottom and max(start[1], end[1]) > top
    return top < start[1] < bottom and min(start[0], end[0]) < right and max(start[0], end[0]) > left


@pytest.mark.parametrize(("spans", "relation", "entry"), [
    (WALL, WALL_RELATION, None), (COSTLY, COSTLY_RELATION, "any"),
])
def test_member_names_remain_hard_under_declared_suppress_policy(
        tmp_path, monkeypatch, spans, relation, entry):
    rendered, context, completed = _render_and_compare(
        tmp_path, _project(spans, relation), monkeypatch, entry=entry, unroutable="suppress")

    assert len(completed.routes.relations) == 1
    relation_result = completed.routes.relations[0]
    if relation_result.suppressed:
        warnings = [item for item in completed.routes.diagnostics
                    if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]
        assert len(warnings) == 1 and relation_result.relation_id in warnings[0]
    names = _names(rendered)
    assert names
    for route in _routes(rendered):
        for start, end in zip(route.points, route.points[1:]):
            assert all(not _segment_hits_box(start, end, tuple(name.text_layout.bounds)) for name in names), (
                route.scene_id, start, end,
                tuple((name.scene_id, tuple(name.text_layout.bounds)) for name in names))
    assert len(names) >= sum(item.semantic_id == "memberLabel" for item in context.base_text)


def test_clear_member_names_and_dependency_routes_complete_together(tmp_path, monkeypatch):
    source = sr.chain_project(groups=1, per_group=3)
    for index, item in enumerate(source["objects"].values()):
        item["title"] = str(index)
    # Short above-bar names are genuinely clear of the outward dependency stroke;
    # the former long end-side names were not an unobstructed control.
    rendered, context, completed = _render_and_compare(
        tmp_path, source, monkeypatch, label_sides=["above", "suppress"])
    names = tuple(item for item in context.base_text if item.semantic_id == "memberLabel")
    assert names and all(item.overflow == "fit" for item in names), [
        (item.placement_id, item.content, item.overflow) for item in names]
    assert completed.routes.relations and all(not route.suppressed for route in completed.routes.relations)
    assert _names(rendered)
    for route in _routes(rendered):
        for start, end in zip(route.points, route.points[1:]):
            assert all(not _segment_hits_box(start, end, tuple(name.text_layout.bounds))
                       for name in _names(rendered))


def test_project_without_relations_uses_one_route_completion(tmp_path, monkeypatch):
    source = sr.chain_project()
    source["relations"] = []
    passes = []
    routes = label_plan.compose_surface_routes
    def observed(context):
        passes.append(context.progress_pass)
        return routes(context)
    monkeypatch.setattr(label_plan, "compose_surface_routes", observed)
    rendered = sr.render(tmp_path, source, presentation=_parts())

    assert _names(rendered)
    assert passes == ["route-content-baseline"]
