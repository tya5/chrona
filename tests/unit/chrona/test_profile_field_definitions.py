from copy import deepcopy

from chrona.extensions.profiles import (
    resolve_profile_field_definitions,
    validate_generic_profiles,
)


MANIFEST = {
    "version": "chrona/profile/v0.3",
    "packageId": "acme-fields",
    "contentIdentity": "sha256:" + "1" * 64,
    "requires": {"projectFormat": "timeline/v0.7"},
    "fields": {
        "shared-count": {"type": "integer", "required": True},
        "state": {"type": "string"},
        "tags": {"type": "string", "cardinality": "many"},
    },
    "profiles": {
        "acme-fields.item": {
            "extends": "task",
            "fields": {
                "state": {"type": "enum", "enumValues": ["ready", "blocked"]},
                "tags": {"type": "enum", "cardinality": "many", "enumValues": ["red", "blue"]},
            },
        }
    },
}


def test_resolver_merges_shared_fields_then_profile_overrides():
    definitions = resolve_profile_field_definitions(MANIFEST, "acme-fields.item")

    assert definitions == {
        "shared-count": {"type": "integer", "required": True},
        "state": {"type": "enum", "enumValues": ["ready", "blocked"]},
        "tags": {"type": "enum", "cardinality": "many", "enumValues": ["red", "blue"]},
    }


def test_validator_uses_same_effective_shared_and_profile_definitions():
    project = {
        "extensions": [{"packageId": "acme-fields"}],
        "objects": {
            "item": {
                "type": "acme-fields.item",
                "fields": {"shared-count": 3, "state": "ready", "tags": ["red"]},
            }
        },
    }
    assert validate_generic_profiles(project, {"acme-fields": MANIFEST}) == []

    # The profile's enum overrides the shared string definition, and its many
    # cardinality requires an array whose individual values satisfy that enum.
    project["objects"]["item"]["fields"]["state"] = "unknown"
    project["objects"]["item"]["fields"]["tags"] = "red"
    diagnostics = validate_generic_profiles(project, {"acme-fields": MANIFEST})
    assert [(item.id, item.path) for item in diagnostics] == [
        ("E_PROFILE_FIELD_ENUM", "/objects/item/fields/state"),
        ("E_PROFILE_FIELD_TYPE", "/objects/item/fields/tags"),
    ]


def test_resolver_unknown_profile_is_none_and_return_is_detached():
    assert resolve_profile_field_definitions(MANIFEST, "acme-fields.unknown") is None

    original = deepcopy(MANIFEST)
    definitions = resolve_profile_field_definitions(original, "acme-fields.item")
    definitions["state"]["enumValues"].append("mutated")
    definitions["extra"] = {"type": "boolean"}

    assert original == MANIFEST

