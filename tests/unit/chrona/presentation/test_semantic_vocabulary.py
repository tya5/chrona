"""The host semantic vocabulary is a versioned, immutable resource."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json

import pytest
import yaml

import chrona.presentation.model.semantic_registry as semantic_registry
from chrona.presentation.model.semantic_registry import semantic_binding, semantic_ids
from chrona.resources.semantic_vocabulary import (
    SemanticVocabularyError,
    builtin_semantic_vocabulary,
    load_semantic_vocabulary,
    validate_semantic_vocabulary,
)


_BASELINE_BINDING_DIGEST = "f381624b9bbaa02c006de7c63943e1f21a631ccb8c65f6b3df61116726ff76e5"


def _small_envelope() -> dict[str, object]:
    """An independent valid sample for loader failures and isolation checks."""
    return {
        "version": "chrona/semantic-vocabulary/v0.1",
        "kind": "semantic-vocabulary",
        "id": "chrona-core",
        "body": {
            "bindings": [{
                "semanticId": "sampleMark",
                "primitiveFamily": "mark",
                "purpose": "sample",
                "sceneRole": "sample",
                "themeRole": "sample",
                "contrastClass": "mark",
            }],
        },
    }


def _payload(envelope: dict[str, object]) -> bytes:
    return yaml.safe_dump(envelope, sort_keys=False, allow_unicode=True).encode("utf-8")


def test_runtime_vocabulary_has_the_reviewed_117_bindings_in_order():
    rows = [
        (
            binding.semantic_id,
            binding.primitive_kind,
            binding.purpose,
            binding.scene_role,
            binding.theme_role,
            binding.contrast_class.value if binding.contrast_class else None,
        )
        for binding in map(semantic_binding, semantic_ids())
    ]
    digest = sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

    assert len(rows) == 117
    assert digest == _BASELINE_BINDING_DIGEST


def test_registry_map_is_immutable_and_cannot_change_derived_roles_or_helpers():
    original_roles = semantic_registry._SCENE_ROLES
    original_ids = semantic_ids()
    original_purposes = semantic_registry.purposes()

    with pytest.raises(TypeError):
        semantic_registry._REGISTRY["planned"] = semantic_binding("actual")

    assert semantic_registry._SCENE_ROLES == original_roles
    assert semantic_ids() == original_ids
    assert semantic_registry.purposes() == original_purposes
    assert semantic_binding("planned").scene_role == "planned"


def test_vocabulary_is_cached_immutable_and_to_envelope_is_isolated():
    vocabulary = builtin_semantic_vocabulary()

    assert builtin_semantic_vocabulary() is vocabulary
    assert isinstance(vocabulary.bindings, tuple)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        vocabulary.bindings[0].purpose = "changed"
    with pytest.raises(AttributeError):
        vocabulary.bindings.append(vocabulary.bindings[0])

    first = vocabulary.to_envelope()
    first["body"]["bindings"][0]["purpose"] = "changed"
    assert vocabulary.to_envelope()["body"]["bindings"][0]["purpose"] == vocabulary.bindings[0].purpose


def test_mapping_input_is_copied_into_frozen_runtime_rows():
    envelope = _small_envelope()
    bindings = validate_semantic_vocabulary(envelope)
    envelope["body"]["bindings"][0]["purpose"] = "mutated-after-load"

    assert bindings[0].purpose == "sample"
    assert bindings[0].semantic_id == "sampleMark"


def test_schema_rejects_unknown_envelope_fields():
    envelope = _small_envelope()
    envelope["unrecognized"] = True

    with pytest.raises(SemanticVocabularyError) as caught:
        validate_semantic_vocabulary(envelope)

    assert caught.value.diagnostic_id == "E_RESOURCE_SCHEMA"


def test_content_identity_hashes_exact_raw_bytes_not_decoded_content():
    payload = _payload(_small_envelope())
    equivalent_bytes = payload + b"\n"
    first = load_semantic_vocabulary(payload)
    second = load_semantic_vocabulary(equivalent_bytes)

    assert first.bindings == second.bindings
    assert first.content_identity == "sha256:" + sha256(payload).hexdigest()
    assert second.content_identity == "sha256:" + sha256(equivalent_bytes).hexdigest()
    assert first.content_identity != second.content_identity
    assert load_semantic_vocabulary(payload, expected_content_identity=first.content_identity) == first


@pytest.mark.parametrize(
    ("mutate", "diagnostic_id", "source_ref"),
    [
        (lambda value: value["body"]["bindings"].append(deepcopy(value["body"]["bindings"][0])),
         "E_SEMANTIC_VOCABULARY_DUPLICATE_ID", "/body/bindings/1/semanticId"),
        (lambda value: value["body"]["bindings"][0].pop("themeRole"),
         "E_RESOURCE_SCHEMA", "/body/bindings/0"),
        (lambda value: value["body"]["bindings"][0].__setitem__("primitiveFamily", "beam"),
         "E_RESOURCE_SCHEMA", "/body/bindings/0/primitiveFamily"),
        (lambda value: value["body"]["bindings"][0].__setitem__("purpose", 42),
         "E_RESOURCE_SCHEMA", "/body/bindings/0/purpose"),
        (lambda value: value.__setitem__("version", "chrona/semantic-vocabulary/v9.9"),
         "E_RESOURCE_VERSION_UNSUPPORTED", "/version"),
        (lambda value: value.__setitem__("kind", "style"),
         "E_SEMANTIC_VOCABULARY_RESOURCE", "/kind"),
        (lambda value: value.__setitem__("id", "other-vocabulary"),
         "E_SEMANTIC_VOCABULARY_RESOURCE", "/id"),
    ],
    ids=("duplicate-id", "missing-field", "unknown-enum", "wrong-type", "wrong-version", "wrong-kind", "wrong-id"),
)
def test_invalid_vocabulary_is_rejected_with_a_pointed_diagnostic(mutate, diagnostic_id, source_ref):
    envelope = _small_envelope()
    mutate(envelope)

    with pytest.raises(SemanticVocabularyError) as caught:
        load_semantic_vocabulary(_payload(envelope))

    assert caught.value.diagnostic_id == diagnostic_id
    assert caught.value.source_ref == source_ref


def test_expected_raw_byte_identity_mismatch_is_rejected():
    payload = _payload(_small_envelope())

    with pytest.raises(SemanticVocabularyError) as caught:
        load_semantic_vocabulary(payload, expected_content_identity="sha256:" + "0" * 64)

    assert caught.value.diagnostic_id == "E_RESOURCE_IDENTITY_MISMATCH"
    assert caught.value.source_ref == "/contentIdentity"


def test_expected_identity_is_checked_before_invalid_bytes_are_parsed():
    with pytest.raises(SemanticVocabularyError) as caught:
        load_semantic_vocabulary(b"not: [valid", expected_content_identity="sha256:" + "0" * 64)

    assert caught.value.diagnostic_id == "E_RESOURCE_IDENTITY_MISMATCH"
    assert caught.value.source_ref == "/contentIdentity"


def test_missing_resource_bytes_are_rejected():
    with pytest.raises(SemanticVocabularyError) as caught:
        load_semantic_vocabulary(b"")

    assert caught.value.diagnostic_id == "E_SEMANTIC_VOCABULARY_RESOURCE"
