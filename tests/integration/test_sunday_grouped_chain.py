"""Exercise protected Sunday routing on a grouped, scheduled chain."""
from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter, process_time

import pytest
import yaml

from chrona.core.relation_identity import relation_identities
from chrona.presentation.layout import route_search, routing
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _project(*, chained: bool) -> dict:
    first = date(2026, 11, 2)
    objects = {
        f"group-{group}": {
            "type": "group", "title": f"Workstream {group}",
            "schedule": {"mode": "rollup"},
        }
        for group in range(3)
    }
    for index in range(22):
        schedule = {"mode": "scheduled", "amount": "5wd"}
        if not chained or index == 0:
            schedule["anchor"] = {"start": (first + timedelta(days=7 * index)).isoformat()}
        objects[f"task-{index:02}"] = {
            "type": "task", "title": f"Synthetic task {index:02}",
            "parent": f"group-{index % 3}",
            # Mixed owner buckets exercise role-bound grouping without
            # assigning a responsible owner to hierarchy summaries.
            "fields": {"owner": (f"Actor-{index % 9:02}" if index % 9 < 4
                                  else f"Worker-{index % 9:02}")},
            "schedule": schedule,
        }
    relations = ([
        {"id": f"r-{index:02}", "type": "dependency", "lag": "0wd",
         "from": {"object": f"task-{index - 1:02}", "endpoint": "end"},
         "to": {"object": f"task-{index:02}", "endpoint": "start"}}
        for index in range(1, 22)
    ] if chained else [])
    project = sr.project(objects, relations)
    project["project"].update(id="sunday-grouped-chain", title="Sunday grouped chain", calendar="workweek")
    project["calendars"] = {"workweek": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    return project


@pytest.mark.parametrize("mode", ("relax", "suppress"))
@pytest.mark.parametrize("chained", (False, True), ids=("unchained", "chained"))
@pytest.mark.parametrize("role_grouping", (True, False), ids=("role", "direct-field"))
def test_sunday_grouped_scheduled_chain_routes(tmp_path, monkeypatch, mode, chained, role_grouping):
    source = _project(chained=chained)
    assert len(source["objects"]) == 25
    assert len({item.get("fields", {}).get("owner") for item in source["objects"].values()
                if "owner" in item.get("fields", {})}) == 9
    assert sum(item["type"] == "group" and item["schedule"]["mode"] == "rollup"
               for item in source["objects"].values()) == 3
    relations = source["relations"]
    assert len(relations) == (21 if chained else 0)

    # The only Layout override is the unroutable policy; all other Sunday
    # profile values remain the packaged values.
    layout_root = builtin_preset_source_root("designs/sunday")
    layout = safe_load(layout_root.joinpath("layout.yaml").read_bytes())
    layout["relationRouting"]["unroutable"] = mode
    layout_path = tmp_path / f"layout-{mode}.yaml"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    project_path = tmp_path / "project.yaml"
    project_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    view_path = None
    if not role_grouping:
        # Keep the original required-rollup-bar barrier witness under an
        # explicit field contract; bound-role grouping now omits those bars.
        view_root = builtin_preset_source_root("presets/bundles/design-default")
        view = safe_load(view_root.joinpath("view.yaml").read_bytes())
        view["body"]["grouping"]["by"] = "field"
        view["body"]["grouping"]["field"] = "owner"
        view["body"]["grouping"].pop("fallback", None)
        view_path = tmp_path / "direct-field-view.yaml"
        view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    counters = {"expansions": 0, "unbounded_generators": 0, "barrier_bounds": 0}
    original_candidates = route_search.orthogonal_route_candidates
    original_bound = routing.rectangular_detour_lower_bound

    class UnexpectedProtectedWork(RuntimeError):
        pass

    def observe_candidates(*args, **kwargs):
        if kwargs.get("limit", 4096) is None:
            counters["unbounded_generators"] += 1
        callback = kwargs.get("on_expansion")

        def count_expansion():
            counters["expansions"] += 1
            structural_ceiling = routing.RELATION_SEARCH_EXPANSIONS * max(1, len(relations))
            if counters["expansions"] > structural_ceiling:
                raise UnexpectedProtectedWork("protected route search exceeded test safety ceiling")
            if callback is not None:
                callback()

        kwargs["on_expansion"] = count_expansion
        yield from original_candidates(*args, **kwargs)

    def observe_bound(*args, **kwargs):
        counters["barrier_bounds"] += 1
        return original_bound(*args, **kwargs)

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", observe_candidates)
    monkeypatch.setattr(routing, "rectangular_detour_lower_bound", observe_bound)

    start_wall, start_cpu = perf_counter(), process_time()
    rendered = render_draft(DraftRenderRequest(
        project=project_path, target_kind="svg", preset="sunday", layout=layout_path, view=view_path,
    )).rendered
    wall_seconds, cpu_seconds = perf_counter() - start_wall, process_time() - start_cpu

    expected_ids = set(relation_identities(relations))
    route_primitives = [item for item in rendered.surface.primitives
                        if item.source_kind == "relation" and item.scene_id.startswith("relation:")]
    emitted_ids = {item.source_ref for item in route_primitives}
    assert emitted_ids == expected_ids
    assert len(route_primitives) == len(relations)
    diagnostics = tuple(rendered.scene.diagnostics)
    summary_ids = {identity for identity, obj in source["objects"].items() if obj["type"] == "group"}
    emitted_summaries = {item.source_ref for item in rendered.surface.primitives
                         if item.source_kind == "object" and item.source_ref in summary_ids}
    if role_grouping:
        assert 'I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED:{"count":3}' in diagnostics
        assert not emitted_summaries
    else:
        assert not any(item.startswith("I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED:") for item in diagnostics)
        assert emitted_summaries == summary_ids
    assert not any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)
    assert not any(item.startswith("W_LAYOUT_CRITICAL_RELATION_SEARCH_DOMAIN_EXHAUSTED:")
                   for item in diagnostics)
    if mode == "suppress":
        assert not any(item.startswith("W_SCENE_RELATION_THROUGH_MARK:") for item in diagnostics)
        assert counters["expansions"] <= routing.RELATION_SEARCH_EXPANSIONS * max(1, len(relations))
        if chained and not role_grouping:
            assert counters["barrier_bounds"] > 0
            assert any(item.startswith("I_LAYOUT_CRITICAL_RELATION_QUALITY_FALLBACK:")
                       for item in diagnostics)

    print(f"Sunday grouped mode={mode} chained={chained} role={role_grouping} relations={len(relations)} "
          f"routing={counters} wall={wall_seconds:.2f}s cpu={cpu_seconds:.2f}s")
