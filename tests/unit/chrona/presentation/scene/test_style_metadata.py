from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from chrona.presentation.scene.model import (
    ContentFamilyCounts,
    InspectionScene,
    SceneManifest,
    ScenePrimitive,
    ScenePaint,
    SceneProvenance,
    SceneSlot,
    SceneSurface,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError,
    scene_document,
    serialize_scene,
    validate_scene_document,
)
from chrona.resources.semantic_vocabulary import builtin_semantic_vocabulary
from chrona.usecases.previous_scene import decode_previous_scene
from chrona.presentation.scene.contrast_policy import STRICT_SEVERITIES, evaluate_scene_contrast


def _primitive(**changes):
    values = {
        "scene_id": "planned-mark",
        "kind": "Rect",
        "source_ref": "task-1",
        "source_kind": "object",
        "purpose": "planned",
        "visual_role": "planned",
        "bounds": (1, 1, 10, 4),
        "slot_id": "plot",
    }
    values.update(changes)
    return ScenePrimitive(**values)


def _scene(primitive):
    slot = SceneSlot("plot", "plot", None, (0, 0, 20, 12))
    surface = SceneSurface("surface", (slot,), (), (), None, (primitive,), canvas_bounds=(0, 0, 20, 12))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 12), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    vocabulary = builtin_semantic_vocabulary()
    resources = (("semantic-vocabulary", vocabulary.id, "v0.1", vocabulary.content_identity),) if primitive.semantic_id else ()
    return InspectionScene(SceneProvenance("draft", "test", resources), (20, 12), (), (surface,), manifest, ())


def test_style_metadata_round_trips_without_replacing_canonical_host_fields():
    encoded = serialize_scene(_scene(_primitive(semantic_id="planned", theme_role="custom-planned")))
    document = json.loads(encoded)
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert primitive["semanticId"] == "planned"
    assert primitive["themeRole"] == "custom-planned"
    assert primitive["purpose"] == "planned"
    assert primitive["visualRole"] == "planned"
    validate_scene_document(document)


def test_no_style_metadata_retains_the_scene_v06_document_bytes():
    encoded = serialize_scene(_scene(_primitive()))
    document = json.loads(encoded)
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.6"
    assert "semanticId" not in primitive and "themeRole" not in primitive
    assert sha256(encoded).hexdigest() == "ae2c29daaf51c492c63e9889fc1347ff8070db4243ea0f1596591a8a3a3e7e79"


@pytest.mark.parametrize("kwargs", [
    {"semantic_id": "planned"},
    {"theme_role": "custom-planned"},
])
def test_style_metadata_requires_both_fields(kwargs):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID.*semantic_id/theme_role"):
        _primitive(**kwargs)


def test_style_metadata_requires_a_registered_semantic_binding():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID.*registered semantic vocabulary"):
        _primitive(semantic_id="not-registered", theme_role="custom-planned")


def test_style_metadata_requires_canonical_purpose_and_visual_role():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID.*semantic_id/purpose/visual_role"):
        _primitive(semantic_id="planned", theme_role="custom-planned", purpose="actual")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID.*semantic_id/purpose/visual_role"):
        _primitive(semantic_id="planned", theme_role="custom-planned", visual_role="custom-planned")


def test_raw_scene_rejects_wrong_binding_and_half_metadata_pair():
    document = scene_document(_scene(_primitive(semantic_id="planned", theme_role="custom-planned")))
    document["surfaces"][0]["primitives"][0]["purpose"] = "actual"
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION.*semantic_id/purpose/visual_role"):
        validate_scene_document(document)

    document = scene_document(_scene(_primitive(semantic_id="planned", theme_role="custom-planned")))
    document["surfaces"][0]["primitives"][0]["semanticId"] = "not-registered"
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION.*registered semantic vocabulary"):
        validate_scene_document(document)

    document = scene_document(_scene(_primitive(semantic_id="planned", theme_role="custom-planned")))
    del document["surfaces"][0]["primitives"][0]["themeRole"]
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(document)


@pytest.mark.parametrize("change", ["missing", "duplicate", "identity", "revision", "id"])
def test_style_metadata_requires_pinned_vocabulary_before_semantic_lookup(monkeypatch, change):
    document = scene_document(_scene(_primitive(semantic_id="planned", theme_role="custom-planned")))
    resources = document["provenance"]["resources"]
    if change == "missing":
        resources.clear()
    elif change == "duplicate":
        resources.append(dict(resources[0]))
    elif change == "identity":
        resources[0]["contentIdentity"] = "sha256:" + "0" * 64
    elif change == "revision":
        resources[0]["revision"] = "other"
    else:
        resources[0]["id"] = "other"

    def no_unverified_lookup(*args):
        raise AssertionError("unverified vocabulary must not reach semantic lookup")

    monkeypatch.setattr("chrona.presentation.scene.serialization._validate_style_semantic_metadata", no_unverified_lookup)
    with pytest.raises(SceneSerializationError, match="E_RESOURCE_IDENTITY_MISMATCH"):
        validate_scene_document(document)


def test_previous_scene_replay_validates_style_vocabulary_identity():
    document = scene_document(_scene(_primitive(semantic_id="planned", theme_role="custom-planned")))
    document["provenance"]["resources"].append({
        "kind": "project", "id": "p", "revision": "r1", "contentIdentity": "sha256:" + "1" * 64,
    })
    decoded = decode_previous_scene(json.dumps(document).encode(), "p")
    assert decoded.value["surfaces"][0]["primitives"][0]["themeRole"] == "custom-planned"
    document["provenance"]["resources"][0]["contentIdentity"] = "sha256:" + "0" * 64
    with pytest.raises(SceneSerializationError, match="E_RESOURCE_IDENTITY_MISMATCH"):
        decode_previous_scene(json.dumps(document).encode(), "p")


def test_selected_theme_role_cannot_reclassify_a_data_mark_as_decoration():
    paint = ScenePaint("#FFFFFF", None, None, (), 1.0)
    primitive = _primitive(paint=paint)

    def document_for(value):
        scene = _scene(value)
        scene = replace(scene, surfaces=(replace(scene.surfaces[0], canvas_paint=paint),))
        document = scene_document(scene)
        validate_scene_document(document)
        return document

    ordinary = evaluate_scene_contrast(document_for(primitive), policy=STRICT_SEVERITIES)
    styled = evaluate_scene_contrast(document_for(replace(
        primitive, semantic_id="planned", theme_role="canvas-texture")), policy=STRICT_SEVERITIES)
    assert ordinary == styled
    assert any(item.code == "E_SCENE_MARK_CONTRAST" and item.floor == 3.0 for item in styled)
