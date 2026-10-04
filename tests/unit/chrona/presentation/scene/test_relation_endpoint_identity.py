"""Scene preserves Layout's resolved relation endpoint instance identities."""

import json

import pytest

from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, ScenePaint, ScenePrimitive,
    SceneProvenance, SceneSlot, SceneSurface,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, serialize_scene, scene_document, validate_scene_document,
)
from chrona.presentation.renderers.v05_svg import render_v05_svg


def _scene(primitive: ScenePrimitive) -> InspectionScene:
    slot = SceneSlot("timeline", "timeline", None, (0, 0, 100, 100))
    surface = SceneSurface("timeline", (slot,), (), (), None, (primitive,),
                           canvas_paint=ScenePaint("#ffffff", None, None, (), 1),
                           canvas_bounds=(0, 0, 100, 100))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (100, 100), (), (),
                             ContentFamilyCounts(1, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (100, 100), (), (surface,),
                           manifest, ())


def test_relation_endpoint_identity_is_optional_and_selects_scene_v07() -> None:
    base = ScenePrimitive("relation:r:a:b", "Path", "r", "relation", "dependency-connector",
                          "dependency-connector", (0, 0, 10, 10), slot_id="timeline",
                          points=((0, 5), (10, 5)), paint=ScenePaint(None, "#000000", 1, (), 1))
    legacy = scene_document(_scene(base))
    assert legacy["version"] == "chrona/scene/v0.6"
    assert "fromInstanceId" not in legacy["surfaces"][0]["primitives"][0]
    assert "toInstanceId" not in legacy["surfaces"][0]["primitives"][0]

    identified = ScenePrimitive(**{
        **base.__dict__, "from_instance_id": "source-instance", "to_instance_id": "target-instance",
    })
    document = scene_document(_scene(identified))
    assert document["version"] == "chrona/scene/v0.7"
    primitive = document["surfaces"][0]["primitives"][0]
    assert primitive["fromInstanceId"] == "source-instance"
    assert primitive["toInstanceId"] == "target-instance"
    validate_scene_document(document)
    assert json.loads(serialize_scene(_scene(identified))) == document

    base_surface = _scene(base).surfaces[0]
    identified_surface = _scene(identified).surfaces[0]
    assert render_v05_svg(base_surface) == render_v05_svg(identified_surface)


def test_relation_endpoint_identity_requires_both_nonempty_path_endpoints() -> None:
    base = ScenePrimitive("relation:r:a:b", "Path", "r", "relation", "dependency-connector",
                          "dependency-connector", (0, 0, 10, 10), slot_id="timeline")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(**{**base.__dict__, "from_instance_id": "source-instance"})
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(**{**base.__dict__, "from_instance_id": "source-instance",
                          "to_instance_id": "target-instance", "kind": "Rect"})

    valid = scene_document(_scene(ScenePrimitive(**{
        **base.__dict__, "from_instance_id": "source-instance", "to_instance_id": "target-instance",
    })))
    missing_target = json.loads(json.dumps(valid))
    del missing_target["surfaces"][0]["primitives"][0]["toInstanceId"]
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(missing_target)
    wrong_kind = json.loads(json.dumps(valid))
    wrong_kind["surfaces"][0]["primitives"][0]["kind"] = "Rect"
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(wrong_kind)
