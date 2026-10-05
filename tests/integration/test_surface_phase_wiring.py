"""One obstacle index and one phase order across label, route and relation-label placement (#592 I592-4)."""
import sys
from pathlib import Path

import pytest

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer, surface_route_label_plan

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_routes_and_labels_use_isolated_trials_from_one_pre_route_inventory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    trials: list[tuple[str, int, int]] = []
    trial_initial_ids: dict[int, set[str]] = {}
    trial_final_ids: dict[int, set[str]] = {}
    requested: dict[int, list[str]] = {}
    pre_requests: list[str] = []
    seen: dict[str, object] = {}

    def record(name, obstacles):
        identity = id(obstacles)
        ids = {item.placement_id for item in obstacles.all()}
        trial_initial_ids.setdefault(identity, ids)
        trials.append((name, identity, len(ids)))
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
        result = route_owner(context)
        trial_final_ids[identity] = {item.placement_id for item in context.obstacles.all()}
        return result

    def relation_labels(context, batch):
        identity = record("relation-labels", context.obstacles)
        result = relation_label_owner(context, batch)
        trial_final_ids[identity] = {item.placement_id for item in context.obstacles.all()}
        return result

    def post_labels(context, requests, obstacles):
        identity = record("member-labels", obstacles)
        requested.setdefault(identity, []).extend(item.placement_id for item in requests)
        result = member_label_owner(context, requests, obstacles)
        trial_final_ids[identity] = {item.placement_id for item in obstacles.all()}
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
        seen["selected_index_id"] = id(result.obstacles)
        seen["trial_ids"] = set(trial_initial_ids)
        return result

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", plan_spy)
    example = ROOT / "examples/halcyon-1"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(example / "project.yaml"),
                                      "--actual", str(example / "actual.yaml"),
                                      "--output", str(tmp_path / "out.svg")])
    main()

    trial_ids = {identity for _, identity, _ in trials}
    assert len(trial_ids) in {1, 2}
    assert seen["pre_index_id"] not in trial_ids
    assert seen["selected_index_id"] in trial_ids
    assert "as-of-label" in pre_requests
    assert set(pre_requests).isdisjoint(seen["post_request_ids"])
    for identity in trial_ids:
        phases = [name for name, index_id, _ in trials if index_id == identity]
        assert phases in (["routes", "relation-labels"],
                         ["routes", "member-labels", "relation-labels"],
                         ["member-labels", "routes", "relation-labels"],
                         ["member-labels", "routes", "member-labels", "relation-labels"])
        counts = [count for _, index_id, count in trials if index_id == identity]
        assert counts == sorted(counts)
        assert len(requested.get(identity, ())) == len(set(requested.get(identity, ())))
        assert seen["pre_index_ids"] <= trial_initial_ids[identity]
        assert trial_initial_ids[identity] <= trial_final_ids[identity]
