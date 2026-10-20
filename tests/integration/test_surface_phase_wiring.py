"""Member names are completed before route search and share its obstacle inventory."""
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer, surface_route_label_plan
from tests.support.draft_packages import stage_project_package_store

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_member_names_are_placed_once_before_routes_from_the_actual_inventory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    phases: list[str] = []
    pre_member_ids: list[str] = []
    route_inputs: dict[int, set[str]] = {}
    route_results = []
    plan_facts: dict[str, object] = {}

    place_pre = surface_composer.place_member_labels

    def pre_labels(context, requests, obstacles):
        names = tuple(item.placement_id for item in requests if item.semantic_id == "memberLabel")
        pre_member_ids.extend(names)
        phases.append("member-names")
        result = place_pre(context, requests, obstacles)
        assert {f"label-footprint:{name}" for name in names} <= {
            item.placement_id for item in obstacles.all()}
        return result

    monkeypatch.setattr(surface_composer, "place_member_labels", pre_labels)
    route_owner = surface_route_label_plan.compose_surface_routes
    relation_label_owner = surface_route_label_plan.place_relation_labels
    member_label_owner = surface_route_label_plan.place_member_labels

    def routes(context):
        identity = id(context.obstacles)
        route_inputs[identity] = {item.placement_id for item in context.obstacles.all()}
        phases.append("routes")
        result = route_owner(context)
        route_results.append(result)
        return result

    def relation_labels(context, batch, *, terminal):
        phases.append("terminal-labels" if terminal else "ordinary-relation-labels")
        return relation_label_owner(context, batch, terminal=terminal)

    def post_labels(context, requests, obstacles):
        assert not any(item.semantic_id == "memberLabel" for item in requests)
        phases.append("post-route-labels")
        return member_label_owner(context, requests, obstacles)

    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes", routes)
    monkeypatch.setattr(surface_route_label_plan, "place_relation_labels", relation_labels)
    monkeypatch.setattr(surface_route_label_plan, "place_member_labels", post_labels)
    original_plan = surface_composer.compose_routes_and_member_labels

    def plan_spy(context):
        plan_facts["post_member_names"] = tuple(item.placement_id for item in context.post_route_requests
                                                if item.semantic_id == "memberLabel")
        plan_facts["pre_index_ids"] = {item.placement_id for item in context.clean_obstacles.all()}
        result = original_plan(context)
        plan_facts["selected_index_id"] = id(result.obstacles)
        return result

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", plan_spy)
    example = ROOT / "examples/halcyon-1"
    project_path = example / "project.yaml"
    project = yaml.safe_load(project_path.read_bytes())
    store_config = stage_project_package_store(tmp_path / "project-store", project, example)
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project_path),
                                      "--actual", str(example / "actual.yaml"),
                                      "--store-config", str(store_config),
                                      "--output", str(tmp_path / "out.svg")])
    main()

    assert pre_member_ids and len(pre_member_ids) == len(set(pre_member_ids))
    assert not plan_facts["post_member_names"]
    assert phases[0] == "member-names" and phases[1] == "routes"
    assert phases.count("routes") == 1
    assert phases == ["member-names", "routes", "terminal-labels", "post-route-labels",
                      "ordinary-relation-labels"]
    assert plan_facts["selected_index_id"] in route_inputs
    assert plan_facts["pre_index_ids"] <= route_inputs[plan_facts["selected_index_id"]]
    assert {f"label-footprint:{name}" for name in pre_member_ids} <= route_inputs[
        plan_facts["selected_index_id"]]
    assert len(route_results) == 1
