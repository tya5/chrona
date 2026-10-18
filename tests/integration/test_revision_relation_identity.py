"""Revision identity is closed before Layout recovers previous geometry."""
from datetime import date, timedelta
import json

import yaml

from chrona.presentation.model.info_diagnostics import RelationHintReceipt
from chrona.presentation.scene.serialization import serialize_scene
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _routes(rendered):
    return {primitive.source_ref: primitive.scene_id
            for primitive in rendered.surface.primitives
            if primitive.kind == "Path" and primitive.source_kind == "relation"
            and primitive.from_instance_id and primitive.to_instance_id}


def test_removed_and_appended_relation_keeps_other_primitive_ids_and_hints(tmp_path):
    start = date(2026, 2, 2)
    objects = {f"{pair}-{side}": sr.span(f"{pair}-{side}", start + timedelta(days=offset), 2)
               for pair in range(4) for side, offset in (("a", 0), ("b", 7))}
    relations = [{"id": f"link-{pair}", "type": "dependency",
                  "from": {"object": f"{pair}-a", "endpoint": "end"},
                  "to": {"object": f"{pair}-b", "endpoint": "start"}}
                 for pair in range(4)]
    project = sr.project(objects, relations[:3])
    path, previous = tmp_path / "project.yaml", tmp_path / "previous.scene.json"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    before = render_draft(DraftRenderRequest(path, "svg")).rendered
    before_routes = _routes(before)
    assert len(before_routes) == 3
    previous.write_bytes(serialize_scene(before.scene))

    project["relations"] = [*relations[1:3], relations[3]]
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    after = render_draft(DraftRenderRequest(path, "svg", previous_scene=previous)).rendered
    after_routes = _routes(after)
    retained = {"relation:id:link-1", "relation:id:link-2"}
    assert {key: before_routes[key] for key in retained} == {key: after_routes[key] for key in retained}
    receipts = [item for item in after.info_diagnostics if isinstance(item, RelationHintReceipt)]
    assert len(receipts) == 3
    assert len([item for item in receipts if item.disposition == "accepted"]) == 2
    assert len([item for item in receipts if item.disposition == "absent"]) == 1

    # A previous index-prefixed source is not positionally assigned to a new
    # relation, even if its primitive and endpoint geometry would be usable.
    old_scene = json.loads(serialize_scene(before.scene))
    for surface in old_scene["surfaces"]:
        for primitive in surface["primitives"]:
            if primitive.get("sourceRef", "").startswith("relation:id:"):
                primitive["sourceRef"] = primitive["sourceRef"].replace("relation:id:", "relation:0:", 1)
    previous.write_text(json.dumps(old_scene), encoding="utf-8")
    legacy = render_draft(DraftRenderRequest(path, "svg", previous_scene=previous)).rendered
    legacy_receipts = [item for item in legacy.info_diagnostics if isinstance(item, RelationHintReceipt)]
    assert len(legacy_receipts) == 3
    assert all(item.disposition == "absent" for item in legacy_receipts)
