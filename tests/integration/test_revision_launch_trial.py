"""Actual issue1300 trial: retain the dependency in Scene and serialized SVG."""
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

from chrona.usecases.draft_render import DraftRenderRequest, render_draft


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
