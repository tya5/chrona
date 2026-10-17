"""Synthetic member-name reservation trials preserve the unreserved route contract."""
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


def _parts(*, entry: str | None = None, unroutable="suppress"):
    parts = sr.bundle()
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})["search"] = "best"
    parts["layout"]["relationRouting"]["unroutable"] = unroutable
    parts["view"] = sr.lane_view(parts["view"])
    if entry is not None:
        parts["layout"]["relationRouting"]["entry"] = entry
    return parts


def _render_and_compare(tmp_path, source, monkeypatch, *, entry=None, unroutable="suppress"):
    captured = {}
    original = composer.compose_routes_and_member_labels
    def observe(context):
        clean_before = tuple(context.clean_obstacles.all())
        reference = label_plan._trial(context, (), context.post_route_requests)
        selected = original(context)
        assert tuple(context.clean_obstacles.all()) == clean_before
        captured.update(reference=reference, selected=selected)
        return selected
    monkeypatch.setattr(composer, "compose_routes_and_member_labels", observe)
    rendered = sr.render(tmp_path, source, presentation=_parts(entry=entry, unroutable=unroutable))
    reference, selected = captured["reference"], captured["selected"]
    assert label_plan._preserves(reference, selected)
    reference_names = {item.placement_id for item in reference.members.text
                       if item.semantic_id == "memberLabel" and item.overflow != "suppressed"}
    selected_names = {item.placement_id for item in selected.members.text
                      if item.semantic_id == "memberLabel" and item.overflow != "suppressed"}
    assert reference_names <= selected_names
    return rendered, reference, selected


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
def test_reserved_trial_never_worsens_reference_routes_or_suppresses_reference_names(
        tmp_path, monkeypatch, spans, relation, entry):
    rendered, reference, selected = _render_and_compare(
        tmp_path, _project(spans, relation), monkeypatch, entry=entry)

    reference_routes = {item.relation_id for item in reference.routes.relations if not item.suppressed}
    selected_routes = {item.relation_id for item in selected.routes.relations if not item.suppressed}
    assert reference_routes <= selected_routes
    if selected_routes:
        names = _names(rendered)
        assert names
        for route in _routes(rendered):
            for start, end in zip(route.points, route.points[1:]):
                assert all(not _segment_hits_box(start, end, tuple(name.text_layout.bounds)) for name in names)


def test_no_conflict_keeps_completed_primitives_equal_to_unreserved_reference(tmp_path, monkeypatch):
    _, reference, selected = _render_and_compare(tmp_path, sr.chain_project(), monkeypatch)
    reference_text = [(item.placement_id, item.bounds, item.host_placement_id)
                      for item in reference.members.text]
    selected_text = [(item.placement_id, item.bounds, item.host_placement_id)
                     for item in selected.members.text]
    reference_routes = [(item.relation_id, item.points, item.suppressed)
                        for item in reference.routes.relations]
    selected_routes = [(item.relation_id, item.points, item.suppressed)
                       for item in selected.routes.relations]
    assert selected_text == reference_text
    assert selected_routes == reference_routes


def test_project_without_relations_uses_one_reservation_trial_and_no_replay(tmp_path, monkeypatch):
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
    assert passes == ["route-label-reserved"]
