"""Real scheduling facts drive Layout calls, not paint or Scene ordering."""
from xml.etree import ElementTree

import yaml

from chrona.presentation.layout import surface_routes
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
    batches, attempts, expected_attempts = [], [], []
    declared_ids = {}
    order, select = surface_routes.dependency_routing_order, surface_routes.select_relation_route

    def observed_order(facts):
        result = order(facts)
        batches.append(tuple((index, fact.source_object_id, fact.target_object_id,
                              fact.critical, fact.semantic_id)
                             for index, fact in result))
        declared_ids.update((fact.relation_id, index) for index, fact in result)
        expected_attempts.extend(f"relation:{fact.relation_id}:" for _, fact in result)
        return result

    def observed_select(*args, **kwargs):
        attempts.append(kwargs["relation_scene_id"])
        return select(*args, **kwargs)  # Preserve real safety/quality validation.

    monkeypatch.setattr(surface_routes, "dependency_routing_order", observed_order)
    monkeypatch.setattr(surface_routes, "select_relation_route", observed_select)
    rendered = render_draft(DraftRenderRequest(project=path, target_kind="svg")).rendered
    expected = ((1, "start", "long", True, "dependency"), (3, "long", "finish", True, "dependency"),
                (0, "start", "short", False, "dependency"), (2, "short", "finish", False, "dependency"))
    assert batches and all(batch == expected for batch in batches)
    assert attempts
    assert len(attempts) == len(expected_attempts)
    assert all(identity.startswith(prefix) for identity, prefix in zip(attempts, expected_attempts))
    routes = [item for item in rendered.surface.primitives
              if item.source_kind == "relation" and item.scene_id.startswith("relation:")]
    route_names = [item.source_ref for item in routes]
    assert route_names
    assert route_names == sorted(route_names, key=declared_ids.__getitem__)
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_ids = [element.get("data-scene-id", element.get("id")) for element in svg.iter()]
    emitted = [item.scene_id for item in routes]
    assert [identity for identity in svg_ids if identity in emitted] == emitted
