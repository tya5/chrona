"""Member names are completed before route search and share its obstacle inventory."""
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer, surface_route_label_plan
from chrona.presentation.layout.surface_member_labels import MemberLabelAllocationSession
from tests.support.draft_packages import stage_project_package_store

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_member_names_are_placed_once_before_routes_from_the_actual_inventory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    phases_by_trial: dict[int, list[str]] = {}
    trial_requests = {}
    pre_member_ids: dict[int, list[str]] = {}
    session_trials = {}
    placed_member_ids: dict[int, set[str]] = {}
    route_inputs: dict[int, set[str]] = {}
    route_results = []
    plan_facts: dict[int, dict[str, object]] = {}

    def trial_id(context):
        request = getattr(context, "request", None)
        if request is None:
            request = context.member_labels.request
        identity = id(request)
        trial_requests[identity] = request
        phases_by_trial.setdefault(identity, [])
        return identity

    prepare_pre = surface_composer.prepare_member_labels
    finish_pre = MemberLabelAllocationSession.finish
    prepared_sessions = []
    intrinsic_ids: set[str] = set()

    def pre_labels(context, requests, obstacles):
        names = tuple(item.placement_id for item in requests if item.semantic_id == "memberLabel")
        identity = trial_id(context)
        pre_member_ids.setdefault(identity, []).extend(names)
        intrinsic_ids.update(item.placement_id for item in context.intrinsic_endpoint_footprints)
        phases_by_trial[identity].append("member-names")
        result = prepare_pre(context, requests, obstacles)
        prepared_sessions.append(result)
        session_trials[id(result)] = identity
        # every placed name owns a footprint; a name the declared label gap leaves no pose for
        # (suppressed) owns none
        placed = {item.placement_id for item in result.text
                  if item.semantic_id == "memberLabel" and item.overflow != "suppressed"}
        placed_member_ids.setdefault(identity, set()).update(placed)
        assert {f"label-footprint:{name}" for name in names if name in placed} <= {
            item.placement_id for item in result.obstacles.all()}
        assert intrinsic_ids.isdisjoint({item.placement_id for item in result.obstacles.all()})
        return result

    monkeypatch.setattr(surface_composer, "prepare_member_labels", pre_labels)

    def finish_labels(session):
        if id(session) in session_trials:
            phases_by_trial[session_trials[id(session)]].append("final-projection")
        return finish_pre(session)

    monkeypatch.setattr(MemberLabelAllocationSession, "finish", finish_labels)
    route_owner = surface_route_label_plan.compose_surface_routes
    relation_label_owner = surface_route_label_plan.place_relation_labels
    member_label_owner = surface_route_label_plan.place_member_labels

    def routes(context):
        identity = id(context.obstacles)
        route_inputs[identity] = {item.placement_id for item in context.obstacles.all()}
        assert prepared_sessions
        trial = trial_id(context)
        prepared = next(item for item in reversed(prepared_sessions)
                        if session_trials[id(item)] == trial)
        names = set(pre_member_ids[trial])
        assert {item.placement_id for item in prepared.text
                if item.semantic_id == "memberLabel"} == names
        assert {item.placement_id for item in context.text
                if item.semantic_id == "memberLabel"} == names
        assert intrinsic_ids.isdisjoint(route_inputs[identity])
        phases_by_trial[trial].append("routes-start")
        result = route_owner(context)
        route_results.append(result)
        phases_by_trial[trial].append("routes-closed")
        return result

    def relation_labels(context, batch, *, terminal):
        phases_by_trial[trial_id(context)].append(
            "terminal-labels" if terminal else "ordinary-relation-labels")
        return relation_label_owner(context, batch, terminal=terminal)

    def post_labels(context, requests, obstacles):
        assert not any(item.semantic_id == "memberLabel" for item in requests)
        phases_by_trial[trial_id(context)].append("post-route-labels")
        return member_label_owner(context, requests, obstacles)

    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes", routes)
    monkeypatch.setattr(surface_route_label_plan, "place_relation_labels", relation_labels)
    monkeypatch.setattr(surface_route_label_plan, "place_member_labels", post_labels)
    original_plan = surface_composer.compose_routes_and_member_labels

    def plan_spy(context):
        trial = trial_id(context)
        facts = plan_facts.setdefault(trial, {})
        facts["post_member_names"] = tuple(item.placement_id for item in context.post_route_requests
                                            if item.semantic_id == "memberLabel")
        facts["pre_index_ids"] = {item.placement_id for item in context.clean_obstacles.all()}
        result = original_plan(context)
        facts["selected_index_id"] = id(result.obstacles)
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

    assert phases_by_trial and len(phases_by_trial) == len(trial_requests)
    expected_phases = ["member-names", "routes-start", "routes-closed", "final-projection",
                       "terminal-labels", "post-route-labels", "ordinary-relation-labels"]
    for trial, phases in phases_by_trial.items():
        names = pre_member_ids[trial]
        assert names and len(names) == len(set(names))
        assert phases == expected_phases
        facts = plan_facts[trial]
        assert not facts["post_member_names"]
        assert facts["selected_index_id"] in route_inputs
        assert facts["pre_index_ids"] <= route_inputs[facts["selected_index_id"]]
        assert placed_member_ids[trial] and {
            f"label-footprint:{name}" for name in placed_member_ids[trial]} <= route_inputs[
            facts["selected_index_id"]]
    assert len(route_results) == len(phases_by_trial)
