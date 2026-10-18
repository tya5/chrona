from __future__ import annotations

import json

import pytest

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.scene.model import (
    ContentFamilyCounts,
    InspectionScene,
    LinearGradient,
    SceneManifest,
    ScenePaint,
    ScenePrimitive,
    SceneProvenance,
    SceneSlot,
    SceneSurface,
    SymbolGeometry,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError,
    scene_document,
    serialize_scene,
    validate_scene_document,
)


def _cone(*, mark_ground: bool | None = None, gradient: bool = True,
          fading: bool = True, purpose: str = "as-of-cone", visual_role: str = "as-of-cone",
          kind: str = "Symbol") -> ScenePrimitive:
    paint = ScenePaint(
        "#FFC857", None, None, (), 1.0,
        LinearGradient((0, 0), (0, 10), ((0, "#FFC857"), (1, "#FFC857")), "required",
                       (1.0, 0.0) if fading else None) if gradient else None,
    )
    return ScenePrimitive(
        "as-of-cone", kind, "actual-set", "decoration", purpose, visual_role,
        (0, 0, 10, 10), "plot", symbol=SymbolGeometry((
            PathCommand("move", ((0, 0),)), PathCommand("line", ((10, 0),)),
            PathCommand("line", ((5, 10),)), PathCommand("line", ((0, 0),)),
        )), paint=paint, mark_ground=mark_ground,
    )


def _scene(primitive: ScenePrimitive) -> InspectionScene:
    slot = SceneSlot("plot", "plot", None, (0, 0, 10, 10))
    surface = SceneSurface("surface", (slot,), (), (), None, (primitive,),
                           canvas_bounds=(0, 0, 10, 10))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (10, 10), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (10, 10), (),
                           (surface,), manifest, ())


@pytest.mark.parametrize("value", [False, True])
def test_mark_ground_serializes_as_passive_v07_cone_metadata(value: bool) -> None:
    document = json.loads(serialize_scene(_scene(_cone(mark_ground=value))))
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert primitive["markGround"] is value
    validate_scene_document(document)


def test_absent_mark_ground_is_omitted_and_defaults_to_false_in_v07() -> None:
    document = scene_document(_scene(_cone(mark_ground=None)))
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert "markGround" not in primitive
    validate_scene_document(document)


@pytest.mark.parametrize(
    "changes",
    [
        {"purpose": "planned", "visual_role": "planned"},
        {"mark_ground": 1},
        {"gradient": False},
        {"kind": "Rect"},
    ],
)
def test_typed_scene_rejects_invalid_mark_ground_metadata(changes) -> None:
    values = {"mark_ground": True}
    values.update(changes)
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID.*mark_ground"):
        _cone(**values)


@pytest.mark.parametrize(
    "changes",
    [
        {"purpose": "planned", "visualRole": "planned"},
        {"markGround": 1},
        {"removeGradient": True},
        {"kind": "Rect"},
    ],
)
def test_v07_schema_rejects_noncone_nonboolean_or_unpainted_mark_ground(changes) -> None:
    document = scene_document(_scene(_cone(mark_ground=True)))
    primitive = document["surfaces"][0]["primitives"][0]
    if changes.get("removeGradient"):
        primitive["paint"].pop("gradient")
    primitive.update({key: value for key, value in changes.items() if key != "removeGradient"})

    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(document)


def test_v06_scene_rejects_mark_ground_and_keeps_legacy_cone_without_it() -> None:
    document = scene_document(_scene(_cone(mark_ground=None, fading=False)))
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.6"
    assert "markGround" not in primitive
    validate_scene_document(document)

    primitive["markGround"] = False
    with pytest.raises(SceneSerializationError, match="scene-v0.6.schema.yaml rejected"):
        validate_scene_document(document)
