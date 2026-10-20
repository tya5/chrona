"""Names precede routes; annotations extend their one completed inventory (#1841)."""
from collections import Counter
from datetime import date

import pytest

from chrona.presentation.layout import surface_annotations, surface_composer, surface_route_label_plan
from chrona.presentation.layout.obstacles import ObstacleRect, obstacles_intersect
from tests.support import synthetic_review as sr


def render_wiring_fixture(tmp_path, *, policy="first-fit"):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-02-01", "end": "2026-03-01"}
    parts["view"]["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress"}
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})["search"] = policy
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 4, title="Design"),
                         "b": sr.span("b", date(2026, 2, 16), 4, title="Build")}, [
        {"id": "a-b", "type": "dependency", "lag": "0d",
         "from": {"object": "a", "endpoint": "end"},
         "to": {"object": "b", "endpoint": "start"}}])
    sr.add_notes(source, parts["view"], ("a",),
                 (sr.candidate("plot", connector="leader", max_positions=256),), words=0)
    return sr.render(tmp_path, source, presentation=parts)


@pytest.mark.parametrize("policy", ("first-fit", "best"))
def test_annotations_follow_single_content_first_route_plan(tmp_path, monkeypatch, policy):
    events, names, seen = [], [], {}
    original_names = surface_composer.place_member_labels
    original_routes = surface_route_label_plan.compose_surface_routes
    original_annotations = surface_annotations.place_annotations
    original_complete = surface_composer.complete_surface_layout

    def labels(context, requests, index):
        names.extend(item.placement_id for item in requests if item.semantic_id == "memberLabel")
        events.append("pre-labels")
        footprints = context.intrinsic_endpoint_footprints
        assert footprints
        seen["intrinsic_ids"] = {item.placement_id for item in footprints}
        batch = original_names(context, requests, index)
        for item in batch.text:
            if item.semantic_id != "memberLabel" or item.overflow == "suppressed":
                continue
            bounds = item.bounds
            ink = ObstacleRect(float(bounds.inline), float(bounds.block),
                               float(bounds.inline + bounds.inline_size),
                               float(bounds.block + bounds.block_size))
            assert not any(obstacles_intersect(ink, footprint.geometry) for footprint in footprints)
        return batch

    def routes(context):
        events.append("routes")
        assert names and len(names) == len(set(names))
        assert all(identifier in context.required_label_obstacle_ids for identifier in names)
        assert {item.placement_id for item in context.text if item.semantic_id == "memberLabel"} == set(names)
        seen["index"] = context.obstacles
        seen["before_routes"] = {item.placement_id for item in context.obstacles.all()}
        assert seen["intrinsic_ids"].isdisjoint(seen["before_routes"])
        batch = original_routes(context)
        seen["routes"] = {item.relation_id: item.points for item in batch.relations}
        return batch

    def annotations(context):
        events.append("annotations")
        assert context.surface_obstacles is seen["index"]
        before = {item.placement_id for item in context.surface_obstacles.all()}
        assert seen["before_routes"] <= before
        batch = original_annotations(context)
        after = {item.placement_id for item in context.surface_obstacles.all()}
        assert before < after
        seen["annotation_batch"] = batch
        return batch

    def complete(context):
        events.append("completion")
        assert {item.relation_id: item.points for item in context.relations
                if item.relation_id in seen["routes"]} == seen["routes"]
        batch = seen["annotation_batch"]
        assert batch.text and batch.relations
        assert {item.placement_id for item in batch.text} <= {item.placement_id for item in context.text}
        assert {item.relation_id for item in batch.relations} <= {item.relation_id for item in context.relations}
        return original_complete(context)

    monkeypatch.setattr(surface_composer, "place_member_labels", labels)
    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes", routes)
    monkeypatch.setattr(surface_annotations, "place_annotations", annotations)
    monkeypatch.setattr(surface_composer, "complete_surface_layout", complete)
    render_wiring_fixture(tmp_path, policy=policy)
    assert events == ["pre-labels", "routes", "annotations", "completion"]
    assert set(Counter(names).values()) == {1}


def test_annotation_module_owns_its_paint_order_and_anchor_helpers():
    assert surface_annotations.ANNOTATION_PAINT_ORDER == 400
    assert not hasattr(surface_composer, "ANNOTATION_PAINT_ORDER")
    assert callable(surface_annotations.comparison_marks) and callable(surface_annotations.annotation_anchor_bounds)
