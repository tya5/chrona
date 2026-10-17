"""One obstacle index and one phase order across label, route and relation-label placement (#592 I592-4)."""
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer, surface_route_label_plan
from tests.support.draft_packages import stage_project_package_store

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_routes_and_labels_use_isolated_trials_from_one_pre_route_inventory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    trials: list[tuple[str, int, int, bool]] = []
    trial_initial_ids: dict[int, set[str]] = {}
    trial_final_ids: dict[int, set[str]] = {}
    trial_indexes: dict[int, object] = {}
    requested: dict[int, list[str]] = {}
    pre_requests: list[str] = []
    probe_added_ids: dict[int, set[str]] = {}
    route_trial_phases: list[list[str]] = []
    seen: dict[str, object] = {}

    def record(name, obstacles, *, reserve_only=False):
        identity = id(obstacles)
        ids = {item.placement_id for item in obstacles.all()}
        trial_initial_ids.setdefault(identity, ids)
        trial_indexes.setdefault(identity, obstacles)  # retain identities across isolated trial lifetimes
        trials.append((name, identity, len(ids), reserve_only))
        return identity

    pre_label_owner = surface_composer.place_member_labels

    def pre_labels(context, requests, obstacles):
        pre_requests.extend(item.placement_id for item in requests)
        return pre_label_owner(context, requests, obstacles)

    monkeypatch.setattr(surface_composer, "place_member_labels", pre_labels)
    route_owner = surface_route_label_plan.compose_surface_routes
    relation_label_owner = surface_route_label_plan.place_relation_labels
    member_label_owner = surface_route_label_plan.place_member_labels

    def routes(context):
        identity = record("routes", context.obstacles)
        route_trial_phases.append(["routes"])
        result = route_owner(context)
        trial_final_ids[identity] = {item.placement_id for item in context.obstacles.all()}
        return result

    def relation_labels(context, batch):
        identity = record("relation-labels", context.obstacles)
        route_trial_phases[-1].append("relation-labels")
        result = relation_label_owner(context, batch)
        trial_final_ids[identity] = {item.placement_id for item in context.obstacles.all()}
        return result

    def post_labels(context, requests, obstacles, *, reserve_only=False):
        identity = record("member-labels", obstacles, reserve_only=reserve_only)
        if not reserve_only:
            route_trial_phases[-1].append("member-labels")
            requested.setdefault(identity, []).extend(item.placement_id for item in requests)
        result = member_label_owner(context, requests, obstacles, reserve_only=reserve_only)
        trial_final_ids[identity] = {item.placement_id for item in obstacles.all()}
        if reserve_only:
            probe_added_ids[identity] = trial_final_ids[identity] - trial_initial_ids[identity]
        return result

    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes", routes)
    monkeypatch.setattr(surface_route_label_plan, "place_relation_labels", relation_labels)
    monkeypatch.setattr(surface_route_label_plan, "place_member_labels", post_labels)
    original_plan = surface_composer.compose_routes_and_member_labels

    def plan_spy(context):
        seen["pre_index_id"] = id(context.clean_obstacles)
        seen["pre_index_ids"] = {item.placement_id for item in context.clean_obstacles.all()}
        seen["post_request_ids"] = {item.placement_id for item in context.post_route_requests}
        result = original_plan(context)
        seen["trial_ids"] = set(trial_initial_ids)
        return result

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", plan_spy)
    original_selection = surface_route_label_plan.select_completed_route_label_plan
    def selection_spy(*args):
        result, annotations = original_selection(*args)
        seen["selected_index_id"] = id(result.obstacles)
        return result, annotations
    monkeypatch.setattr(surface_route_label_plan, "select_completed_route_label_plan", selection_spy)
    example = ROOT / "examples/halcyon-1"
    project_path = example / "project.yaml"
    project = yaml.safe_load(project_path.read_bytes())
    store_config = stage_project_package_store(tmp_path / "project-store", project, example)
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project_path),
                                      "--actual", str(example / "actual.yaml"),
                                      "--store-config", str(store_config),
                                      "--output", str(tmp_path / "out.svg")])
    main()

    probes = {identity for name, identity, _, reserve_only in trials
              if name == "member-labels" and reserve_only}
    route_ids = {identity for name, identity, _, _ in trials if name == "routes"}
    final_label_ids = {identity for name, identity, _, reserve_only in trials
                       if name == "member-labels" and not reserve_only}
    assert not probes, "the coordinator must not run a global route-free label rehearsal"
    assert 1 <= len(route_ids) <= 2
    assert probes.isdisjoint(route_ids | final_label_ids)
    assert seen["pre_index_id"] not in {identity for _, identity, _, _ in trials}
    assert seen["selected_index_id"] in final_label_ids
    assert "as-of-label" in pre_requests
    assert set(pre_requests).isdisjoint(seen["post_request_ids"])
    assert route_trial_phases == [["routes", "member-labels", "relation-labels"]] * len(route_ids)
    for identity in final_label_ids:
        assert len(requested.get(identity, ())) == len(set(requested.get(identity, ())))
        assert seen["pre_index_ids"] <= trial_initial_ids[identity]
    for identity in route_ids:
        assert seen["pre_index_ids"] <= trial_initial_ids[identity]
        assert trial_initial_ids[identity] <= trial_final_ids[identity]
    for identity in final_label_ids:
        assert trial_initial_ids[identity] <= trial_final_ids[identity]
