"""Characterize relation search cost and visibility on the Sunday preset."""
from __future__ import annotations

from time import perf_counter, process_time

import pytest
import yaml

from chrona.core.relation_identity import relation_identities
from chrona.presentation.layout import route_search, routing
from chrona.presentation.layout import surface_composer, surface_routes
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support.sunday_owner_chain import (
    sunday_owner_chain_comparisons, sunday_owner_chain_project,
)


@pytest.mark.parametrize(
    ("chained", "comparisons", "expected_relations"),
    ((False, False, 0), (True, False, 21), (True, True, 21)),
)
def test_sunday_owner_chain_routes_are_visible_with_bounded_search(
    tmp_path, monkeypatch, chained, comparisons, expected_relations,
):
    source = sunday_owner_chain_project(chained=chained)
    objects = source["objects"]
    relations = source["relations"]
    owners = {item["fields"]["owner"] for item in objects.values()}
    assert len(objects) == 22
    assert len(owners) == 9
    assert source["fieldRoles"] == {"responsible": "owner"}
    assert len(relations) == expected_relations
    for index, relation in enumerate(relations, start=1):
        assert relation["id"] == f"r-{index:02}"
        assert relation["from"]["endpoint"] == "end"
        assert relation["to"]["endpoint"] == "start"
        assert relation["lag"] == "0d"
        assert (objects[relation["from"]["object"]]["fields"]["owner"]
                != objects[relation["to"]["object"]]["fields"]["owner"])

    counters = {"expansions": 0, "search_generators": 0,
                "selections": 0, "route_plans": 0}
    search_limits: list[int | None] = []
    original_candidates = route_search.orthogonal_route_candidates
    original_select = surface_routes.select_relation_route
    original_plan = surface_composer.compose_routes_and_member_labels

    def observe_candidates(*args, **kwargs):
        counters["search_generators"] += 1
        search_limits.append(kwargs.get("limit"))
        callback = kwargs.get("on_expansion")

        def count_expansion():
            counters["expansions"] += 1
            if callback is not None:
                callback()

        kwargs["on_expansion"] = count_expansion
        yield from original_candidates(*args, **kwargs)

    def observe_selection(*args, **kwargs):
        counters["selections"] += 1
        return original_select(*args, **kwargs)

    def observe_route_plan(*args, **kwargs):
        counters["route_plans"] += 1
        return original_plan(*args, **kwargs)

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", observe_candidates)
    monkeypatch.setattr(surface_routes, "select_relation_route", observe_selection)
    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", observe_route_plan)

    project_path = tmp_path / "project.yaml"
    project_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    request = DraftRenderRequest(project=project_path, target_kind="svg", preset="sunday")
    if comparisons:
        snapshot, actual_set = sunday_owner_chain_comparisons(source)
        snapshot_path = tmp_path / "snapshot.yaml"
        actual_path = tmp_path / "actual.yaml"
        snapshot_path.write_text(yaml.safe_dump(snapshot, sort_keys=False), encoding="utf-8")
        actual_path.write_text(yaml.safe_dump(actual_set, sort_keys=False), encoding="utf-8")

        design_root = builtin_preset_source_root("presets/bundles/design-default")
        view = safe_load(design_root.joinpath("view.yaml").read_bytes())
        view["body"]["comparison"]["baseline"] = "snapshot"
        view_path = tmp_path / "view.yaml"
        view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
        request = DraftRenderRequest(
            project=project_path, target_kind="svg", preset="sunday", view=view_path,
            actual=actual_path, snapshot=snapshot_path,
        )

    wall_start, cpu_start = perf_counter(), process_time()
    rendered = render_draft(request).rendered
    wall_seconds, cpu_seconds = perf_counter() - wall_start, process_time() - cpu_start

    assert counters["route_plans"] == 1
    assert all(limit is not None for limit in search_limits)
    assert counters["expansions"] <= routing.RELATION_SEARCH_EXPANSIONS * counters["selections"]

    expected_ids = set(relation_identities(relations))
    route_primitives = [primitive for primitive in rendered.surface.primitives
                        if primitive.source_kind == "relation"
                        and primitive.scene_id.startswith("relation:")]
    emitted_ids = {primitive.source_ref for primitive in route_primitives}
    assert emitted_ids == expected_ids
    assert len(route_primitives) == expected_relations
    assert all(primitive.source_ref is not None for primitive in route_primitives)
    assert not [diagnostic for diagnostic in rendered.scene.diagnostics
                if diagnostic.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]
    if comparisons:
        assert {item.source_ref for item in rendered.surface.primitives
                if item.purpose == "snapshot"} == set(objects)
        assert {item.source_ref for item in rendered.surface.primitives
                if item.purpose == "actual"} == {"task-00", "task-01", "task-02"}

    print(
        f"Sunday chained={chained} comparisons={comparisons} "
        f"owners={len(owners)} relations={len(relations)} "
        f"counts={counters} wall={wall_seconds:.2f}s cpu={cpu_seconds:.2f}s"
    )
