from __future__ import annotations

import json
from dataclasses import replace

import pytest

from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, ScenePrimitive,
    SceneProvenance, SceneSlot, SceneSurface,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, scene_document, serialize_scene, validate_scene_document,
)
from chrona.presentation.style import StyleLegendScope, StyleMatch


_STYLE_RESOURCE = ("style", "review-treatment", "draft", "sha256:" + "a" * 64)


def _primitive(**changes):
    values = {
        "scene_id": "planned-mark", "kind": "Rect", "source_ref": "task-1",
        "source_kind": "object", "purpose": "planned", "visual_role": "planned",
        "bounds": (1, 1, 10, 4), "slot_id": "plot",
    }
    values.update(changes)
    return ScenePrimitive(**values)


def _scene(primitive, *, style=True):
    slot = SceneSlot("plot", "plot", None, (0, 0, 20, 12))
    surface = SceneSurface("surface", (slot,), (), (), None, (primitive,), canvas_bounds=(0, 0, 20, 12))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 12), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    resources = (_STYLE_RESOURCE,) if style else ()
    return InspectionScene(SceneProvenance("draft", "test", resources), (20, 12), (),
                           (surface,), manifest, ())


def test_style_match_round_trips_as_passive_scene_v07_metadata():
    scene = _scene(_primitive(style_match=StyleMatch("review-treatment", ("planned-rule",))))
    document = json.loads(serialize_scene(scene))
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert primitive["styleMatch"] == {"styleId": "review-treatment", "ruleIds": ["planned-rule"]}
    validate_scene_document(document)


def test_legend_scope_round_trips_only_on_a_style_swatch():
    scope = StyleLegendScope("review-treatment", "risk-rule", "risk", '{"purpose":"planned"}',
                             "Risk", True)
    primitive = _primitive(scene_id="arbitrary-scene-id", source_ref="scale:style:abc",
                           source_kind="legend", purpose="legend-swatch",
                           style_match=None, legend_scope=scope)
    document = json.loads(serialize_scene(_scene(primitive)))
    serialized = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert serialized["legendScope"] == {
        "styleId": "review-treatment", "ruleId": "risk-rule", "scaleId": "risk",
        "selector": '{"purpose":"planned"}', "title": "Risk", "showScope": True,
    }
    validate_scene_document(document)


@pytest.mark.parametrize("metadata", [
    {"style_match": StyleMatch("other-style", ("rule",))},
    {"legend_scope": StyleLegendScope("other-style", "rule", "scale", "{}", None, False)},
])
def test_typed_scene_requires_metadata_to_join_its_exact_pinned_style(metadata):
    primitive_values = {"scene_id": "planned-mark", "kind": "Rect", "source_ref": "task-1",
                        "source_kind": "object", "purpose": "planned", "visual_role": "planned",
                        "bounds": (1, 1, 10, 4), "slot_id": "plot"}
    if "legend_scope" in metadata:
        primitive_values.update(source_ref="scale:style:abc", source_kind="legend",
                                purpose="legend-swatch")
    primitive_values.update(metadata)
    with pytest.raises(ValueError, match="E_RESOURCE_IDENTITY_MISMATCH.*exactly one pinned Style"):
        _scene(ScenePrimitive(**primitive_values))


def test_typed_and_replayed_scenes_reject_noncanonical_selector_text():
    with pytest.raises(ValueError, match="legend_scope.selector.*canonical JSON object"):
        _primitive(source_kind="legend", purpose="legend-swatch",
                   legend_scope=StyleLegendScope("review-treatment", "risk-rule", "risk",
                                                 '{ "purpose": "planned" }', None, False))

    scope = StyleLegendScope("review-treatment", "risk-rule", "risk", '{"purpose":"planned"}', None, False)
    document = scene_document(_scene(_primitive(
        source_kind="legend", purpose="legend-swatch",
        legend_scope=scope)))
    document["surfaces"][0]["primitives"][0]["legendScope"]["selector"] = '{ "purpose": "planned" }'
    with pytest.raises(SceneSerializationError, match="legendScope requires canonical selector JSON"):
        validate_scene_document(document)


@pytest.mark.parametrize(("source_kind", "purpose"), [
    ("object", "planned"), ("legend", "planned"),
])
def test_legend_scope_rejects_non_legend_source_or_purpose(source_kind, purpose):
    scope = StyleLegendScope("review-treatment", "risk-rule", "risk", '{"purpose":"planned"}', None, False)
    with pytest.raises(ValueError, match="legend_scope.*completed non-text legend swatch"):
        _primitive(source_kind=source_kind, purpose=purpose, legend_scope=scope)

    document = scene_document(_scene(_primitive(source_kind="legend", purpose="legend-swatch",
                                                legend_scope=scope)))
    primitive = document["surfaces"][0]["primitives"][0]
    primitive["sourceKind"] = source_kind
    primitive["purpose"] = purpose
    with pytest.raises(SceneSerializationError, match="legendScope requires canonical selector JSON on a Style legend swatch"):
        validate_scene_document(document)


def test_raw_scene_replay_requires_one_matching_style_resource():
    primitive = _primitive(style_match=StyleMatch("review-treatment", ("planned-rule",)))
    document = scene_document(_scene(primitive))
    document["provenance"]["resources"] = []
    with pytest.raises(SceneSerializationError, match="E_RESOURCE_IDENTITY_MISMATCH.*exactly one pinned Style"):
        validate_scene_document(document)

    scene = _scene(primitive)
    with pytest.raises(ValueError, match="E_RESOURCE_IDENTITY_MISMATCH.*exactly one pinned Style"):
        replace(scene, provenance=replace(scene.provenance, resources=()))


def test_style_match_requires_unique_nonempty_authored_rule_ids():
    with pytest.raises(ValueError, match="style_match.*unique authored rule IDs"):
        _primitive(style_match=StyleMatch("review-treatment", ("same", "same")))
