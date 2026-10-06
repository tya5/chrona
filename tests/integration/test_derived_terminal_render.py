"""Authored omission completes physical marker facts through Layout and public Scene."""
import pytest

from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("shape", ["chevron", "rounded-triangle"])
def test_omitted_attachment_is_completed_at_actual_relation_width_and_schema_valid(tmp_path, shape):
    parts = sr.bundle()
    body = parts["theme"]["body"]
    body["values"]["derived-terminal"] = {
        "type": "marker", "value": {"shape": shape, "headLength": 6, "headWidth": 6},
    }
    body["values"]["physical-stroke"] = {"type": "number", "value": 2.5}
    body["roles"]["relationTargetTerminal"] = {"marker": "derived-terminal"}
    for role in ("dependency", "dependency-critical"):
        if role in body["roles"]:
            body["roles"][role]["strokeWidth"] = "physical-stroke"
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=2), presentation=parts)
    relations = [node for node in rendered.surface.primitives if node.marker_end is not None
                 and node.scene_id.startswith("relation:")]
    assert len(relations) == 1
    marker = relations[0].marker_end
    assert marker.physical_units
    assert marker.stroke_width == (2.5 if shape == "chevron" else None)
    assert (marker.attachment_offset < 0) if shape == "chevron" else (marker.attachment_offset > 0)
    document = scene_document(rendered.scene)
    assert document["version"] == "chrona/scene/v0.7"
    validate_scene_document(document)
