"""Real scheduling facts drive Layout calls, not paint or Scene ordering."""
from xml.etree import ElementTree

import yaml

from chrona.presentation.layout import surface_routes
from chrona.presentation.layout import surface_count_closure
from chrona.presentation.model.render_progress import RenderProgress, RenderProgressEvent, RenderWorkPhaseEvent
from chrona.usecases.draft_render import DraftRenderRequest, render_draft


def test_scheduler_critical_relations_route_first_but_emit_in_declaration_order(tmp_path, monkeypatch):
    names = ("start-short", "start-long", "short-finish", "long-finish")
    edges = (("start", "short"), ("start", "long"), ("short", "finish"), ("long", "finish"))
    project = {
        "version": "timeline/v0.7", "project": {"id": "priority", "title": "Priority"},
        "objects": {
            "start": {"type": "task", "title": "Start", "schedule": {
                "mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-02"}},
            **{name: {"type": "task", "title": name.title(), "schedule": {
                "mode": "scheduled", "amount": amount}}
               for name, amount in (("long", "4d"), ("short", "2d"), ("finish", "1d"))},
        },
        "relations": [{"id": name, "type": "dependency", "from": {
            "object": source, "endpoint": "end"}, "to": {"object": target, "endpoint": "start"}}
            for name, (source, target) in zip(names, edges)],
    }
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    batches, batches_by_trial, attempts_by_trial, prefixes_by_trial, trial_requests = [], {}, {}, {}, {}
    declared_ids = {}
    order, select = surface_routes.dependency_routing_order, surface_routes.select_relation_route
    current_trial = [None]
    original_compose = surface_count_closure.compose_surface_layout

    def observed_compose(request, *, prepared=None):
        trial_id = id(request)
        trial_requests[trial_id] = request
        current_trial[0] = trial_id
        attempts_by_trial.setdefault(trial_id, [])
        return original_compose(request, prepared=prepared)

    def observed_order(facts):
        result = order(facts)
        # The active route-plan request identifies this joint source trial.
        trial_id = current_trial[0]
        assert trial_id is not None
        prefixes_by_trial.setdefault(trial_id, []).append(
            [f"relation:{fact.relation_id}:" for _, fact in result])
        batch = tuple((index, fact.source_object_id, fact.target_object_id,
                       fact.critical, fact.semantic_id) for index, fact in result)
        batches.append(batch)
        batches_by_trial.setdefault(trial_id, []).append(batch)
        declared_ids.update((fact.relation_id, index) for index, fact in result)
        return result

    def observed_select(*args, **kwargs):
        assert current_trial[0] is not None
        attempts_by_trial[current_trial[0]].append(kwargs["relation_scene_id"])
        return select(*args, **kwargs)  # Preserve real safety/quality validation.

    monkeypatch.setattr(surface_routes, "dependency_routing_order", observed_order)
    monkeypatch.setattr(surface_routes, "select_relation_route", observed_select)
    monkeypatch.setattr(surface_count_closure, "compose_surface_layout", observed_compose)
    progress_events = []
    rendered = render_draft(DraftRenderRequest(project=path, target_kind="svg",
                                              progress=RenderProgress(progress_events.append))).rendered
    expected = ((1, "start", "long", True, "dependency"), (3, "long", "finish", True, "dependency"),
                (0, "start", "short", False, "dependency"), (2, "short", "finish", False, "dependency"))
    assert batches and all(batch == expected for batch in batches)
    assert attempts_by_trial
    assert any(isinstance(event, RenderWorkPhaseEvent) and event.phase == "routing"
               for event in progress_events)
    passes = []
    for event in progress_events:
        if not isinstance(event, RenderProgressEvent) or event.phase != "routing" or event.completed is None:
            continue
        assert event.total == len(names)
        if event.completed == 0:
            passes.append([])
        passes[-1].append(event.completed)
    assert passes and all(values == list(range(len(names) + 1)) for values in passes)
    assert len(attempts_by_trial) == len(trial_requests)
    # Re-run expectations per captured joint trial, retaining the declared
    # critical-first order and ensuring no post-route duplicate selection.
    for trial_id, attempts in attempts_by_trial.items():
        # The endpoint-footprint prepass and actual route completion both ask
        # for the same ordering inside a trial; only the actual route phase
        # selects each route, exactly once in its critical-first order.
        expected_prefixes = prefixes_by_trial[trial_id][0]
        assert len(attempts) == len(expected_prefixes)
        assert all(identity.startswith(prefix)
                   for identity, prefix in zip(attempts, expected_prefixes))
    assert len(batches) >= len(trial_requests)
    assert set(batches_by_trial) == set(trial_requests)
    assert all(all(batch == expected for batch in trial_batches)
               for trial_batches in batches_by_trial.values())
    assert all(all(prefixes == prefixes_by_trial[trial_id][0]
                   for prefixes in prefixes_by_trial[trial_id])
               for trial_id in trial_requests)
    routes = [item for item in rendered.surface.primitives
              if item.source_kind == "relation" and item.scene_id.startswith("relation:")]
    route_names = [item.source_ref for item in routes]
    assert route_names
    assert route_names == sorted(route_names, key=declared_ids.__getitem__)
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_ids = [element.get("data-scene-id", element.get("id")) for element in svg.iter()]
    emitted = [item.scene_id for item in routes]
    assert [identity for identity in svg_ids if identity in emitted] == emitted
