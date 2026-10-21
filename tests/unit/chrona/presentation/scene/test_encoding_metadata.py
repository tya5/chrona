from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, ScenePaint, ScenePrimitive,
    SceneProvenance, SceneSlot, SceneSurface,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, scene_document, serialize_scene, validate_scene_document,
)
from chrona.presentation.style import EncodingSource, EncodingWitness, LegendEncodingCoverage


_VIEW = ("view", "mission-light", "draft", "sha256:" + "a" * 64)
_STYLE = ("style", "review-style", "draft", "sha256:" + "b" * 64)


def _witness(*sources: EncodingSource) -> EncodingWitness:
    return EncodingWitness("fill", "owner", "responsible", "Ada", tuple(sources))


def _coverage(*witnesses: EncodingWitness, kind="encoding", paint_channel="fill") -> LegendEncodingCoverage:
    return LegendEncodingCoverage(kind, tuple(witnesses), paint_channel)


def _primitive(**changes):
    values = {
        "scene_id": "actual-mark", "kind": "Rect", "source_ref": "task-1",
        "source_kind": "object", "purpose": "actual", "visual_role": "actual",
        "bounds": (1, 1, 10, 4), "slot_id": "plot",
        "paint": ScenePaint("#224466", None, None, (), 1.0),
    }
    values.update(changes)
    return ScenePrimitive(**values)


def _scene(primitive, *, resources=(_VIEW,)):
    slot = SceneSlot("plot", "plot", None, (0, 0, 20, 12))
    surface = SceneSurface("surface", (slot,), (), (), None, (primitive,), canvas_bounds=(0, 0, 20, 12))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 12), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", resources), (20, 12), (),
                           (surface,), manifest, ())


def test_encoding_witness_round_trips_as_passive_v07_metadata():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    document = json.loads(serialize_scene(_scene(_primitive(encoding=witness))))
    primitive = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert primitive["encoding"] == {
        "channel": "fill", "scaleId": "owner", "field": "responsible", "value": "Ada",
        "sources": [{"kind": "view", "id": "mission-light", "sourceRef": "/encodings/owner"}],
    }
    validate_scene_document(document)


def test_encoding_can_record_view_and_style_sources_without_evaluating_them():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"),
                       EncodingSource("style", "review-style", "/rules/0/encoding", "owner-treatment"))
    scene = _scene(_primitive(encoding=witness), resources=(_VIEW, _STYLE))
    document = scene_document(scene)
    validate_scene_document(document)
    assert document["surfaces"][0]["primitives"][0]["encoding"]["sources"] == [
        {"kind": "view", "id": "mission-light", "sourceRef": "/encodings/owner"},
        {"kind": "style", "id": "review-style", "sourceRef": "/rules/0/encoding", "ruleId": "owner-treatment"},
    ]


@pytest.mark.parametrize("kind", ["Text", "Icon", "Rect"])
def test_encoding_is_restricted_to_filled_mark_classified_primitives(kind):
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    with pytest.raises(ValueError, match="encoding.*filled MARK-classified"):
        _primitive(kind=kind, purpose="title" if kind != "Rect" else "decoration",
                   visual_role="title" if kind != "Rect" else "background",
                   encoding=witness)

    with pytest.raises(ValueError, match="encoding.*filled MARK-classified"):
        _primitive(paint=ScenePaint(None, "#224466", 1, (), 1.0), encoding=witness)


def test_encoding_sources_require_pinned_resource_joins():
    witness = _witness(EncodingSource("view", "missing-view", "/encodings/owner"))
    with pytest.raises(ValueError, match="E_RESOURCE_IDENTITY_MISMATCH.*encoding source"):
        _scene(_primitive(encoding=witness))

    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    with pytest.raises(ValueError, match="E_RESOURCE_IDENTITY_MISMATCH.*encoding source"):
        _scene(_primitive(encoding=witness), resources=(_VIEW, _VIEW))


def test_replayed_encoding_requires_closed_shape_mark_and_resource_join():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    document = scene_document(_scene(_primitive(encoding=witness)))
    validate_scene_document(document)

    malformed = json.loads(json.dumps(document))
    malformed["surfaces"][0]["primitives"][0]["encoding"]["mystery"] = True
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(malformed)

    missing = json.loads(json.dumps(document))
    missing["provenance"]["resources"].clear()
    with pytest.raises(SceneSerializationError, match="E_RESOURCE_IDENTITY_MISMATCH.*encoding source"):
        validate_scene_document(missing)

    unfilled = json.loads(json.dumps(document))
    unfilled["surfaces"][0]["primitives"][0]["paint"].pop("fill")
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(unfilled)


def test_encoding_absence_retains_v06_bytes_and_v06_schema_rejects_witness():
    # Same compact closure fixture used by the existing v0.6 byte-identity test.
    legacy = _primitive(scene_id="planned-mark", purpose="planned", visual_role="planned", paint=None)
    encoded = serialize_scene(_scene(legacy, resources=()))
    document = json.loads(encoded)
    assert document["version"] == "chrona/scene/v0.6"
    assert sha256(encoded).hexdigest() == "ae2c29daaf51c492c63e9889fc1347ff8070db4243ea0f1596591a8a3a3e7e79"

    document["surfaces"][0]["primitives"][0]["encoding"] = _witness(
        EncodingSource("view", "mission-light", "/encodings/owner")).as_mapping()
    with pytest.raises(SceneSerializationError, match="scene-v0.6.schema.yaml rejected"):
        validate_scene_document(document)


def test_style_source_without_authored_rule_id_is_rejected():
    with pytest.raises(ValueError, match="Style encoding source needs an authored rule ID"):
        EncodingSource("style", "review-style", "/rules/0/encoding")

    raw = {"kind": "style", "id": "review-style", "sourceRef": "/rules/0/encoding"}
    with pytest.raises(ValueError, match="missing or unsupported members"):
        EncodingSource.from_mapping(raw)


def test_legend_encoding_coverage_round_trips_without_role_interpretation():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    coverage = _coverage(witness)
    primitive = _primitive(scene_id="legend-key", source_ref="scale:owner", source_kind="legend",
                           purpose="legend-swatch", visual_role="unclassified-key-role",
                           legend_encoding_coverage=coverage)
    document = json.loads(serialize_scene(_scene(primitive)))
    encoded = document["surfaces"][0]["primitives"][0]

    assert document["version"] == "chrona/scene/v0.7"
    assert encoded["legendEncodingCoverage"] == {
        "kind": "encoding", "witnesses": [witness.as_mapping()],
    }
    validate_scene_document(document)


def test_state_legend_coverage_allows_stroke_only_completed_ink():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    primitive = _primitive(
        scene_id="neutral-state-key", source_ref="milestone:planned", source_kind="legend",
        purpose="legend-swatch", visual_role="unclassified-key-role",
        paint=ScenePaint(None, "#224466", 1.25, (), 1.0),
        legend_encoding_coverage=_coverage(witness, kind="state"),
    )

    document = json.loads(serialize_scene(_scene(primitive)))
    encoded = document["surfaces"][0]["primitives"][0]
    assert encoded["paint"]["stroke"] == "#224466"
    assert "fill" not in encoded["paint"]
    assert encoded["legendEncodingCoverage"]["kind"] == "state"
    validate_scene_document(document)

    with pytest.raises(ValueError, match="state legend encoding coverage requires visible fill or stroke"):
        _primitive(source_kind="legend", purpose="legend-swatch",
                   paint=ScenePaint(None, None, None, (), 1.0),
                   legend_encoding_coverage=_coverage(witness, kind="state"))

    transient = _primitive(source_kind="legend", purpose="legend-swatch", paint=None,
                           legend_encoding_coverage=_coverage(witness, kind="state"))
    assert transient.paint is None
    with pytest.raises(ValueError, match="state legend encoding coverage requires visible fill or stroke"):
        _scene(transient)


@pytest.mark.parametrize("changes", [
    {"kind": "Text"},
    {"purpose": "not-a-legend-swatch"},
    {"source_kind": "object"},
    {"paint": ScenePaint(None, "#224466", 1, (), 1.0)},
])
def test_legend_encoding_coverage_requires_filled_legend_swatch_primitive(changes):
    coverage = _coverage(_witness(EncodingSource("view", "mission-light", "/encodings/owner")))
    values = {"source_kind": "legend", "purpose": "legend-swatch",
              "legend_encoding_coverage": coverage}
    values.update(changes)
    with pytest.raises(ValueError, match="legend encoding coverage"):
        _primitive(**values)


def test_legend_encoding_coverage_requires_nonempty_unique_witnesses():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    with pytest.raises(ValueError, match="non-empty unique"):
        _coverage()
    with pytest.raises(ValueError, match="non-empty unique"):
        _coverage(witness, witness)


def test_encoding_legend_coverage_can_name_stroke_while_state_coverage_cannot():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    coverage = _coverage(witness, paint_channel="stroke")
    primitive = _primitive(source_kind="legend", purpose="legend-swatch",
                           paint=ScenePaint(None, "#224466", 1.25, (), 1.0),
                           legend_encoding_coverage=coverage)
    document = json.loads(serialize_scene(_scene(primitive)))
    encoded = document["surfaces"][0]["primitives"][0]["legendEncodingCoverage"]
    assert encoded == {"kind": "encoding", "paintChannel": "stroke",
                       "witnesses": [witness.as_mapping()]}
    validate_scene_document(document)

    with pytest.raises(ValueError, match="state legend encoding coverage cannot declare"):
        _coverage(witness, kind="state", paint_channel="stroke")
    with pytest.raises(ValueError, match="paint channel must be 'fill' or 'stroke'"):
        _coverage(witness, paint_channel="outline")
    with pytest.raises(ValueError, match="cannot declare a paint channel"):
        LegendEncodingCoverage.from_mapping({
            "kind": "state", "paintChannel": "fill", "witnesses": [witness.as_mapping()],
        })
    with pytest.raises(ValueError, match="when present, must be 'stroke'"):
        LegendEncodingCoverage.from_mapping({
            "kind": "encoding", "paintChannel": "fill", "witnesses": [witness.as_mapping()],
        })


def test_legend_encoding_coverage_sources_require_exact_pinned_resource_join():
    witness = _witness(EncodingSource("view", "missing-view", "/encodings/owner"))
    primitive = _primitive(source_kind="legend", purpose="legend-swatch",
                           legend_encoding_coverage=_coverage(witness))
    with pytest.raises(ValueError, match="E_RESOURCE_IDENTITY_MISMATCH.*legend encoding coverage source"):
        _scene(primitive)

    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    primitive = _primitive(source_kind="legend", purpose="legend-swatch",
                           legend_encoding_coverage=_coverage(witness))
    with pytest.raises(ValueError, match="E_RESOURCE_IDENTITY_MISMATCH.*legend encoding coverage source"):
        _scene(primitive, resources=(_VIEW, _VIEW))


def test_replayed_legend_encoding_coverage_is_closed_and_requires_filled_swatch_and_join():
    witness = _witness(EncodingSource("view", "mission-light", "/encodings/owner"))
    primitive = _primitive(source_kind="legend", purpose="legend-swatch",
                           legend_encoding_coverage=_coverage(witness))
    document = scene_document(_scene(primitive))
    validate_scene_document(document)

    malformed = json.loads(json.dumps(document))
    malformed["surfaces"][0]["primitives"][0]["legendEncodingCoverage"]["mystery"] = True
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(malformed)

    missing = json.loads(json.dumps(document))
    missing["provenance"]["resources"].clear()
    with pytest.raises(SceneSerializationError, match="E_RESOURCE_IDENTITY_MISMATCH.*legend encoding coverage source"):
        validate_scene_document(missing)

    unfilled = json.loads(json.dumps(document))
    unfilled["surfaces"][0]["primitives"][0]["paint"].pop("fill")
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(unfilled)

    wrong_kind = json.loads(json.dumps(document))
    wrong_kind["surfaces"][0]["primitives"][0]["kind"] = "Text"
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(wrong_kind)

    wrong_purpose = json.loads(json.dumps(document))
    wrong_purpose["surfaces"][0]["primitives"][0]["purpose"] = "decoration"
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(wrong_purpose)

    wrong_source_kind = json.loads(json.dumps(document))
    wrong_source_kind["surfaces"][0]["primitives"][0]["sourceKind"] = "object"
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(wrong_source_kind)

    state_stroke = json.loads(json.dumps(document))
    state_stroke["surfaces"][0]["primitives"][0]["legendEncodingCoverage"]["kind"] = "state"
    state_stroke["surfaces"][0]["primitives"][0]["paint"].pop("fill")
    state_stroke["surfaces"][0]["primitives"][0]["paint"].update(
        {"stroke": "#224466", "strokeWidth": 1.25})
    validate_scene_document(state_stroke)

    hollow_state = json.loads(json.dumps(state_stroke))
    hollow_state["surfaces"][0]["primitives"][0]["paint"].pop("stroke")
    hollow_state["surfaces"][0]["primitives"][0]["paint"].pop("strokeWidth")
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(hollow_state)

    encoding_stroke = json.loads(json.dumps(state_stroke))
    encoding_stroke["surfaces"][0]["primitives"][0]["legendEncodingCoverage"].update(
        {"kind": "encoding", "paintChannel": "stroke"})
    validate_scene_document(encoding_stroke)

    encoding_fill = json.loads(json.dumps(document))
    encoding_fill["surfaces"][0]["primitives"][0]["legendEncodingCoverage"]["paintChannel"] = "fill"
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(encoding_fill)

    missing_stroke_coverage = json.loads(json.dumps(encoding_stroke))
    missing_stroke_coverage["surfaces"][0]["primitives"][0]["legendEncodingCoverage"].pop("paintChannel")
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(missing_stroke_coverage)

    state_channel = json.loads(json.dumps(state_stroke))
    state_channel["surfaces"][0]["primitives"][0]["legendEncodingCoverage"]["paintChannel"] = "stroke"
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(state_channel)

    zero_width_stroke = json.loads(json.dumps(encoding_stroke))
    zero_width_stroke["surfaces"][0]["primitives"][0]["paint"]["strokeWidth"] = 0
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(zero_width_stroke)

    duplicate = json.loads(json.dumps(document))
    duplicate["surfaces"][0]["primitives"][0]["legendEncodingCoverage"]["witnesses"].append(
        witness.as_mapping())
    with pytest.raises(SceneSerializationError, match="scene-v0.7.schema.yaml rejected"):
        validate_scene_document(duplicate)
