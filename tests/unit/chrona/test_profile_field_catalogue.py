import pytest

from chrona.extensions.profiles import (
    PACKAGE_ID,
    resolve_profile_field_catalogue,
    resolve_profile_field_definitions,
    validate_profiles,
)


def _manifest(package_id, profile_id, fields, *, package_fields=None):
    return {
        "version": "chrona/profile/v0.3",
        "packageId": package_id,
        "contentIdentity": "sha256:" + "1" * 64,
        "requires": {"projectFormat": "timeline/v0.7"},
        "fields": package_fields or {},
        "profiles": {profile_id: {"extends": "task", "fields": fields}},
    }


def test_catalogue_uses_the_shared_package_merge_and_profile_override():
    manifest = _manifest(
        "acme-fields", "acme-fields.item",
        {"risk": {"type": "enum", "enumValues": ["low", "high"]}},
        package_fields={"risk": {"type": "string"}, "owner": {"type": "string"}},
    )
    project = {"extensions": [{"packageId": "acme-fields"}], "objects": {}}

    catalogue, diagnostics = resolve_profile_field_catalogue(project, {"acme-fields": manifest})

    assert diagnostics == []
    assert catalogue["acme-fields.item"] == resolve_profile_field_definitions(manifest, "acme-fields.item")
    assert catalogue["acme-fields.item"] == {
        "risk": {"type": "enum", "enumValues": ["low", "high"]},
        "owner": {"type": "string"},
    }
    catalogue["acme-fields.item"]["risk"]["enumValues"].append("changed")
    assert manifest["profiles"]["acme-fields.item"]["fields"]["risk"]["enumValues"] == ["low", "high"]


@pytest.mark.parametrize("package_order", [("first", "second"), ("second", "first")])
def test_profile_id_collision_is_pointed_and_removed_independent_of_order(package_order):
    manifests = {
        "first": _manifest("first", "shared.profile", {"value": {"type": "string"}}),
        "second": _manifest("second", "shared.profile", {"value": {"type": "integer"}}),
    }
    project = {"extensions": [{"packageId": package_id} for package_id in package_order], "objects": {}}

    catalogue, diagnostics = resolve_profile_field_catalogue(project, manifests)

    assert "shared.profile" not in catalogue
    assert [(item.id, item.path) for item in diagnostics] == [
        ("E_PROFILE_PACKAGE_INVALID", "/extensions/1"),
    ]
    assert "both" in diagnostics[0].message


def test_primary_and_snapshot_sources_resolve_independent_catalogues():
    primary_manifest = _manifest("acme-fields", "shared.profile", {"risk": {"type": "enum", "enumValues": ["high"]}})
    snapshot_manifest = _manifest("acme-fields", "shared.profile", {"risk": {"type": "string"}})
    project = {"extensions": [{"packageId": "acme-fields"}], "objects": {}}

    primary, primary_diagnostics = resolve_profile_field_catalogue(project, {"acme-fields": primary_manifest})
    snapshot, snapshot_diagnostics = resolve_profile_field_catalogue(project, {"acme-fields": snapshot_manifest})

    assert primary_diagnostics == snapshot_diagnostics == []
    assert primary["shared.profile"]["risk"]["type"] == "enum"
    assert snapshot["shared.profile"]["risk"]["type"] == "string"


def test_delivery_definitions_are_catalogued_but_values_keep_idp_diagnostics():
    delivery = {
        "version": "chrona/profile/v0.3",
        "packageId": PACKAGE_ID,
        "contentIdentity": "sha256:" + "2" * 64,
        "requires": {"projectFormat": "timeline/v0.7"},
        "profiles": {"implementation-delivery.work-item": {
            "extends": "task",
            "fields": {"workflowState": {
                "type": "enum", "cardinality": "one", "required": True,
                "enumValues": ["planned", "active"],
            }},
        }, "implementation-delivery.person": {
            "extends": "entity", "fields": {"externalKey": {"type": "string"}},
        }},
    }
    project = {
        "extensions": [{"packageId": PACKAGE_ID}],
        "objects": {
            "item": {"type": "implementation-delivery.work-item", "fields": {"unknown": "x"}},
            "person": {"type": "implementation-delivery.person", "fields": {"unmodeled": "x"}},
        },
    }

    catalogue, catalogue_diagnostics = resolve_profile_field_catalogue(project, {PACKAGE_ID: delivery})
    diagnostics = validate_profiles(project, {PACKAGE_ID: delivery})

    assert catalogue_diagnostics == []
    assert catalogue["implementation-delivery.work-item"] == delivery["profiles"]["implementation-delivery.work-item"]["fields"]
    assert catalogue["implementation-delivery.person"] == delivery["profiles"]["implementation-delivery.person"]["fields"]
    assert [(item.id, item.path) for item in diagnostics] == [
        ("IDP-PROFILE-006", "/objects/item/fields"),
    ]


def test_invalid_delivery_manifest_does_not_gain_generic_package_diagnostic():
    invalid_delivery = {
        "version": "chrona/profile/v0.3",
        "packageId": PACKAGE_ID,
        "contentIdentity": "sha256:" + "3" * 64,
        "requires": {"projectFormat": "timeline/v0.7"},
        "profiles": {"implementation-delivery.work-item": {
            "extends": "task", "fields": {"workflowState": {"type": "unknown"}},
        }},
    }
    project = {
        "extensions": [{"packageId": PACKAGE_ID}],
        "objects": {"item": {"type": "implementation-delivery.work-item", "fields": {}}},
    }

    catalogue, catalogue_diagnostics = resolve_profile_field_catalogue(project, {PACKAGE_ID: invalid_delivery})
    diagnostics = validate_profiles(project, {PACKAGE_ID: invalid_delivery})

    assert catalogue == {}
    assert catalogue_diagnostics == []
    assert [item.id for item in diagnostics] == ["IDP-PROFILE-006"]
    assert not any(item.id.startswith("E_PROFILE_") for item in diagnostics)


def test_invalid_delivery_profile_shape_does_not_crash_generic_validation():
    invalid_delivery = {
        "version": "chrona/profile/v0.3",
        "packageId": PACKAGE_ID,
        "contentIdentity": "sha256:" + "4" * 64,
        "requires": {"projectFormat": "timeline/v0.7"},
        "profiles": ["malformed"],
    }
    project = {
        "extensions": [{"packageId": PACKAGE_ID}],
        "objects": {"person": {
            "type": "implementation-delivery.person", "fields": {"unmodeled": "x"},
        }},
    }

    diagnostics = validate_profiles(project, {PACKAGE_ID: invalid_delivery})

    assert [item.id for item in diagnostics] == ["IDP-PROFILE-006"]


def test_delivery_profile_name_is_generic_when_delivery_package_is_not_declared():
    generic = _manifest(
        "acme-fields", "implementation-delivery.work-item",
        {"known": {"type": "string"}},
    )
    project = {
        "extensions": [{"packageId": "acme-fields"}],
        "objects": {"item": {
            "type": "implementation-delivery.work-item", "fields": {"unknown": "x"},
        }},
    }

    assert [(item.id, item.path) for item in validate_profiles(project, {"acme-fields": generic})] == [
        ("E_PROFILE_FIELD_UNKNOWN", "/objects/item/fields/unknown"),
    ]
