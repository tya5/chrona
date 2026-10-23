"""Names precede routes; annotations extend their one completed inventory (#1841)."""
from collections import Counter
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout import surface_annotations, surface_composer, surface_route_label_plan
from chrona.presentation.layout.surface_member_labels import MemberLabelAllocationSession
from chrona.presentation.layout.obstacles import ObstacleRect, obstacles_intersect
from chrona.presentation.model.render_progress import RenderProgress, RenderProgressEvent, RenderWorkPhaseEvent
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
    trials, active = [], {}
    original_prepare = surface_composer.prepare_member_labels
    original_finish = MemberLabelAllocationSession.finish
    original_routes = surface_route_label_plan.compose_surface_routes
    original_annotations = surface_annotations.place_annotations
    original_complete = surface_composer.complete_surface_layout

    def labels(context, requests, index):
        trial = {"events": ["pre-labels"],
                 "names": [item.placement_id for item in requests if item.semantic_id == "memberLabel"],
                 "seen": {}}
        trials.append(trial)
        active["trial"] = trial
        names, seen = trial["names"], trial["seen"]
        footprints = context.intrinsic_endpoint_footprints
        assert footprints
        seen["intrinsic_ids"] = {item.placement_id for item in footprints}
        session = original_prepare(context, requests, index)
        seen["session"] = session
        seen["prepared_names"] = {
            item.placement_id for item in session.text if item.semantic_id == "memberLabel"}
        assert seen["prepared_names"] == set(names)
        assert {f"label-footprint:{name}" for name in names} <= {
            item.placement_id for item in session.obstacles.all()}
        assert seen["intrinsic_ids"].isdisjoint(
            {item.placement_id for item in session.obstacles.all()})
        for item in session.text:
            if item.semantic_id != "memberLabel" or item.overflow == "suppressed":
                continue
            bounds = item.bounds
            ink = ObstacleRect(float(bounds.inline), float(bounds.block),
                               float(bounds.inline + bounds.inline_size),
                               float(bounds.block + bounds.block_size))
            assert not any(obstacles_intersect(ink, footprint.geometry) for footprint in footprints)
        return session

    def finish_labels(session):
        trial = active["trial"]
        if session is trial["seen"].get("session"):
            trial["events"].append("final-projection")
        return original_finish(session)

    def routes(context):
        trial = active["trial"]
        events = trial["events"]
        names, seen = trial["names"], trial["seen"]
        events.append("routes-start")
        assert names and len(names) == len(set(names))
        assert all(identifier in context.required_label_obstacle_ids for identifier in names)
        assert {item.placement_id for item in context.text if item.semantic_id == "memberLabel"} == set(names)
        assert seen["session"].text
        assert seen["intrinsic_ids"].isdisjoint(
            {item.placement_id for item in context.obstacles.all()})
        seen["index"] = context.obstacles
        seen["before_routes"] = {item.placement_id for item in context.obstacles.all()}
        batch = original_routes(context)
        seen["routes"] = {item.relation_id: item.points for item in batch.relations}
        events.append("routes-closed")
        return batch

    def annotations(context):
        trial = active["trial"]
        events = trial["events"]
        seen = trial["seen"]
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
        trial = active["trial"]
        events = trial["events"]
        seen = trial["seen"]
        events.append("completion")
        assert {item.relation_id: item.points for item in context.relations
                if item.relation_id in seen["routes"]} == seen["routes"]
        batch = seen["annotation_batch"]
        assert batch.text and batch.relations
        assert {item.placement_id for item in batch.text} <= {item.placement_id for item in context.text}
        assert {item.relation_id for item in batch.relations} <= {item.relation_id for item in context.relations}
        return original_complete(context)

    monkeypatch.setattr(surface_composer, "prepare_member_labels", labels)
    monkeypatch.setattr(MemberLabelAllocationSession, "finish", finish_labels)
    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes", routes)
    monkeypatch.setattr(surface_annotations, "place_annotations", annotations)
    monkeypatch.setattr(surface_composer, "complete_surface_layout", complete)
    render_wiring_fixture(tmp_path, policy=policy)
    expected = ["pre-labels", "routes-start", "routes-closed", "final-projection",
                "annotations", "completion"]
    assert len(trials) in {1, 2}
    assert [trial["events"] for trial in trials] == [expected] * len(trials)
    assert all(set(Counter(trial["names"]).values()) == {1} for trial in trials)


def test_annotation_module_owns_its_paint_order_and_anchor_helpers():
    assert surface_annotations.ANNOTATION_PAINT_ORDER == 400
    assert not hasattr(surface_composer, "ANNOTATION_PAINT_ORDER")
    assert callable(surface_annotations.comparison_marks) and callable(surface_annotations.annotation_anchor_bounds)


def test_annotation_leader_progress_counts_declarations_without_changing_artifact(tmp_path, monkeypatch):
    accepted_events = []
    attempt_events = []
    progress = RenderProgress(accepted_events.append)
    original = surface_composer.complete_route_annotations

    def complete(plan, context):
        current = []
        attempt_events.append(current)
        candidate_progress = context.request.progress
        def relay(event):
            current.append(event)
            candidate_progress.emit(event)
        return original(plan, replace(context, request=replace(
            context.request, progress=RenderProgress(relay))))

    monkeypatch.setattr(surface_composer, "complete_route_annotations", complete)
    request_factory = sr.RenderRequest
    monkeypatch.setattr(sr, "RenderRequest",
                        lambda **kwargs: request_factory(**kwargs, progress=progress))
    observed_dir = tmp_path / "observed"
    observed_dir.mkdir()
    rendered = render_wiring_fixture(observed_dir)
    monkeypatch.setattr(surface_composer, "complete_route_annotations", original)
    monkeypatch.setattr(sr, "RenderRequest", request_factory)
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    plain = render_wiring_fixture(plain_dir)
    expected = [event for pass_name in ("annotation-leaders", "annotation-leaders-reflow-1")
                for event in (RenderProgressEvent("routing", 0, 1, pass_name),
                              RenderProgressEvent("routing", 1, 1, pass_name))]
    assert len(attempt_events) in {1, 2}
    expected_attempt = [event for pass_name in ("annotation-leaders", "annotation-leaders-reflow-1")
                        for event in (RenderWorkPhaseEvent("routing", pass_name),
                                      RenderProgressEvent("routing", 0, 1, pass_name),
                                      RenderProgressEvent("routing", 1, 1, pass_name))]
    assert attempt_events == [expected_attempt] * len(attempt_events)
    # Rejected candidate progress is observed above per attempt but is not
    # forwarded as accepted UI progress; the final candidate is published once.
    accepted_annotation_progress = [event for event in accepted_events
                                    if isinstance(event, RenderProgressEvent)
                                    and event.pass_name and event.pass_name.startswith("annotation-leaders")]
    assert accepted_annotation_progress == expected
    assert [event for event in accepted_events if isinstance(event, RenderWorkPhaseEvent)
            and event.pass_name.startswith("annotation-leaders")] == [
        RenderWorkPhaseEvent("routing", pass_name)
        for _ in attempt_events for pass_name in ("annotation-leaders", "annotation-leaders-reflow-1")]
    assert rendered.artifact.content == plain.artifact.content
    assert rendered.surface.primitives == plain.surface.primitives
