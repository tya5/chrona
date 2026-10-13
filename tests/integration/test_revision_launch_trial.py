"""Actual issue1300 trial: retain the dependency in Scene and serialized SVG."""
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml
import pytest

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.presentation.scene.serialization import serialize_scene
from chrona.presentation.model.info_diagnostics import RelationHintReceipt, RelationHintSummary


def test_launch_trial_revision_keeps_spec_build_drawn(tmp_path):
    fixture = Path(__file__).parents[1] / "fixtures/routing_revision/project-v1.yaml"
    project = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    actual = {
        "version": "chrona/actual-set/v0.3", "kind": "actual-set",
        "id": "nimbus-launch-actuals", "body": {
            "asOf": "2027-02-10", "observations": [
                {"id": "spec-done", "sequence": 1, "projectObjectId": "spec",
                 "actual": {"start": "2027-01-04", "finish": "2027-01-20", "progress": 1}},
                {"id": "positioning-done", "sequence": 1, "projectObjectId": "positioning",
                 "actual": {"start": "2027-01-11", "finish": "2027-01-27", "progress": 1}},
                {"id": "build-progress", "sequence": 1, "projectObjectId": "build",
                 "actual": {"start": "2027-01-21", "openUntil": "asOf", "progress": .55}},
                {"id": "website-progress", "sequence": 1, "projectObjectId": "website",
                 "actual": {"start": "2027-02-01", "openUntil": "asOf", "progress": .3}},
                {"id": "pricing-progress", "sequence": 1, "projectObjectId": "pricing",
                 "actual": {"start": "2027-01-25", "openUntil": "asOf", "progress": .7}},
                {"id": "kickoff-held", "sequence": 1, "projectObjectId": "kickoff",
                 "actual": {"at": "2027-01-05"}},
            ],
        },
    }
    actual_path = tmp_path / "actual.yaml"
    actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    previous_scene = tmp_path / "v1.scene.json"
    old_spec_points = None
    old_routes = None
    for revision in (1, 2):
        if revision == 2:
            project["objects"]["spec"]["schedule"]["end"] = "2027-01-20"
            for identity, title, parent, amount in (
                ("qa", "Regression QA pass", "product", "4wd"),
                ("docs", "Help center docs", "marketing", "6wd"),
            ):
                project["objects"][identity] = {
                    "type": "task", "title": title, "parent": parent,
                    "schedule": {"mode": "scheduled", "amount": amount},
                }
            for identity, source, target in (
                ("bugfix-qa", "bugfix", "qa"), ("web-docs", "website", "docs"),
            ):
                project["relations"].append({
                    "id": identity, "type": "dependency", "lag": "0d",
                    "from": {"object": source, "endpoint": "end"},
                    "to": {"object": target, "endpoint": "start"},
                })
        path = tmp_path / f"project-v{revision}.yaml"
        path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
        result = render_draft(DraftRenderRequest(path, "svg", actual=actual_path)).rendered
        routes = [primitive for primitive in result.surface.primitives
                  if primitive.kind == "Path" and primitive.source_kind == "relation"
                  and ":spec-build:" in primitive.scene_id]
        assert len(routes) == 1
        assert len(routes[0].points) >= 2
        svg = ET.fromstring(result.artifact.content)
        assert any(element.get("data-scene-id", element.get("id")) == routes[0].scene_id
                   for element in svg.iter())
        assert not any(diagnostic.startswith("W_LAYOUT_RELATION_SUPPRESSED:")
                       for diagnostic in result.scene.diagnostics)
        if revision == 1:
            previous_scene.write_bytes(serialize_scene(result.scene))
            old_spec_points = routes[0].points
            old_routes = {
                route.scene_id: (route.from_instance_id, route.to_instance_id, route.points)
                for route in result.surface.primitives
                if route.kind == "Path" and route.source_kind == "relation"
                and route.from_instance_id and route.to_instance_id
            }
        else:
            hinted = render_draft(DraftRenderRequest(path, "svg", actual=actual_path,
                                                   previous_scene=previous_scene)).rendered
            hinted_routes = [primitive for primitive in hinted.surface.primitives
                             if primitive.kind == "Path" and primitive.source_kind == "relation"
                             and ":spec-build:" in primitive.scene_id]
            assert len(hinted_routes) == 1
            receipts = [info for info in hinted.info_diagnostics
                        if isinstance(info, RelationHintReceipt)]
            current_routes = {
                route.scene_id: route
                for route in hinted.surface.primitives
                if route.kind == "Path" and route.source_kind == "relation"
                and route.from_instance_id and route.to_instance_id
            }
            accepted = {receipt.relation_id: receipt for receipt in receipts
                        if receipt.disposition == "accepted"}
            assert accepted
            assert all(not receipt.searched for receipt in accepted.values())
            for relation_id, receipt in accepted.items():
                assert relation_id in current_routes, receipt
                route = current_routes[relation_id]
                assert route.scene_id in old_routes, relation_id
                old_source, old_target, old_points = old_routes[route.scene_id]
                assert (route.from_instance_id, route.to_instance_id) == (old_source, old_target)
                # Reanchoring moves endpoints with their marks and adjusts the
                # first/last elbows. Every interior route point stays pinned.
                points = route.points
                assert len(points) == len(old_points), relation_id
                if len(points) > 2:
                    assert points[2:-2] == old_points[2:-2], relation_id
                assert tuple((b[0] == a[0], b[1] == a[1]) for a, b in zip(points, points[1:])) == tuple(
                    (b[0] == a[0], b[1] == a[1]) for a, b in zip(old_points, old_points[1:])), relation_id
                svg = ET.fromstring(hinted.artifact.content)
                elements = {element.get("data-scene-id", element.get("id")): element for element in svg.iter()}
                assert route.scene_id in elements, relation_id
                assert elements[route.scene_id].get("d"), relation_id
            receipt = next(info for info in receipts if ":spec-build:" in info.relation_id)
            assert receipt.disposition == "accepted", receipt
            assert receipt.relation_id in current_routes
            points = hinted_routes[0].points
            assert len(points) == len(old_spec_points)
            translation = (points[0][0] - old_spec_points[0][0], points[0][1] - old_spec_points[0][1])
            for old, new in zip(old_spec_points, points):
                assert new == pytest.approx((old[0] + translation[0], old[1] + translation[1]))
            svg = ET.fromstring(hinted.artifact.content)
            assert any(element.get("data-scene-id", element.get("id")) == hinted_routes[0].scene_id
                       for element in svg.iter())
            summary = next(info for info in hinted.info_diagnostics if isinstance(info, RelationHintSummary))
            payload = summary.payload()
            assert sum(payload[key] for key in ("accepted", "invalidated", "unusable", "absent")) == payload["relationInstances"]
