"""Annotations place after all source content, share the one obstacle index and register their own geometry (#592 I592-5b)."""
import sys
from pathlib import Path

import pytest

from chrona.app.cli import main
from chrona.presentation.layout import surface_annotations, surface_composer, surface_route_label_plan

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_annotations_follow_selected_route_trial_and_extend_its_obstacle_index(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    trial_events: list[tuple[str, int, int]] = []
    member_requests: dict[int, list[str]] = {}
    trial_initial_ids: dict[int, set[str]] = {}
    trial_final_ids: dict[int, set[str]] = {}
    seen: dict[str, object] = {}
    call: dict[str, object] = {}

    def spy(name: str, original):
        def wrapper(*args, **kwargs):
            events.append(name)
            return original(*args, **kwargs)
        return wrapper

    for attribute, name in (("place_legend", "legend"), ("place_notes", "notes"), ("place_summary", "summary")):
        monkeypatch.setattr(surface_composer, attribute, spy(name, getattr(surface_composer, attribute)))
    for attribute, name in (("compose_surface_routes", "routes"), ("place_relation_labels", "relation-labels")):
        original = getattr(surface_route_label_plan, attribute)

        def owner_spy(*args, _original=original, _name=name, **kwargs):
            obstacles = args[0].obstacles
            identity = id(obstacles)
            ids = {item.placement_id for item in obstacles.all()}
            trial_initial_ids.setdefault(identity, ids)
            trial_events.append((_name, identity, len(ids)))
            result = _original(*args, **kwargs)
            trial_final_ids[identity] = {item.placement_id for item in obstacles.all()}
            return result

        monkeypatch.setattr(surface_route_label_plan, attribute, owner_spy)
    original_labels = surface_route_label_plan.place_member_labels

    def trial_labels(context, requests, obstacles):
        identity = id(obstacles)
        ids = {item.placement_id for item in obstacles.all()}
        trial_initial_ids.setdefault(identity, ids)
        trial_events.append(("member-labels", identity, len(ids)))
        member_requests.setdefault(identity, []).extend(item.placement_id for item in requests)
        result = original_labels(context, requests, obstacles)
        trial_final_ids[identity] = {item.placement_id for item in obstacles.all()}
        return result

    monkeypatch.setattr(surface_route_label_plan, "place_member_labels", trial_labels)
    original_plan = surface_composer.compose_routes_and_member_labels

    def plan_spy(context):
        seen["clean_id"] = id(context.clean_obstacles)
        seen["clean_ids"] = {item.placement_id for item in context.clean_obstacles.all()}
        result = original_plan(context)
        seen["selected_index"] = result.obstacles
        seen["selected_routes"] = {item.relation_id: item.points for item in result.routes.relations}
        return result

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", plan_spy)
    original_complete = surface_composer.complete_surface_layout

    def completion_spy(context):
        selected = seen["selected_routes"]
        completed = {item.relation_id: item.points for item in context.relations
                     if item.relation_id in selected}
        assert completed == selected
        call["completed_routes"] = completed
        return original_complete(context)

    monkeypatch.setattr(surface_composer, "complete_surface_layout", completion_spy)
    original = surface_composer.place_annotations

    def annotations_spy(context):
        events.append("annotations")
        index = context.surface_obstacles
        seen["annotations-before"] = (id(index), len(index.all()))
        batch = original(context)
        seen["annotations-after"] = (id(index), len(index.all()))
        call["batch"] = batch
        return batch

    monkeypatch.setattr(surface_composer, "place_annotations", annotations_spy)
    example = ROOT / "examples/halcyon-1"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(example / "project.yaml"), "--actual", str(example / "actual.yaml"),
        "--view", str(example / "views/02-programme-board.yaml"), "--theme", str(example / "themes/wallboard.yaml"),
        "--scheme", str(example / "schemes/control-room-dark.yaml"), "--layout", str(example / "layouts/wallboard.yaml"),
        "--summary", str(example / "profiles/summary.yaml"), "--detail", str(example / "profiles/detail.yaml"),
        "--output", str(tmp_path / "out.svg"),
    ])
    main()

    assert events == ["legend", "notes", "summary", "annotations"]
    trial_ids = {identity for _, identity, _ in trial_events}
    assert len(trial_ids) in {1, 2}
    for identity in trial_ids:
        phases = [name for name, index_id, _ in trial_events if index_id == identity]
        assert phases in (["routes", "relation-labels"],
                         ["routes", "member-labels", "relation-labels"],
                         ["member-labels", "routes", "relation-labels"],
                         ["member-labels", "routes", "member-labels", "relation-labels"])
        counts = [count for _, index_id, count in trial_events if index_id == identity]
        assert counts == sorted(counts)
        assert len(member_requests.get(identity, ())) == len(set(member_requests.get(identity, ())))
        assert seen["clean_ids"] <= trial_initial_ids[identity]
        assert trial_initial_ids[identity] <= trial_final_ids[identity]
    assert id(seen["selected_index"]) == seen["annotations-before"][0] == seen["annotations-after"][0]
    assert seen["clean_id"] not in trial_ids
    assert id(seen["selected_index"]) in trial_ids
    assert call["completed_routes"] == seen["selected_routes"]
    batch = call["batch"]
    assert batch.text and batch.relations  # this slide has annotation text and leaders
    assert seen["annotations-after"][1] > seen["annotations-before"][1]  # annotations registered their own geometry


def test_annotation_module_owns_its_paint_order_and_anchor_helpers() -> None:
    assert surface_annotations.ANNOTATION_PAINT_ORDER == 400
    assert not hasattr(surface_composer, "ANNOTATION_PAINT_ORDER")
    assert callable(surface_annotations.comparison_marks) and callable(surface_annotations.annotation_anchor_bounds)
