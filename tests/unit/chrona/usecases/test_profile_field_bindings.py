from copy import deepcopy

from chrona.usecases.profile_field_bindings import resolve_source_field_bindings


def _manifest(package_id, *, enum_values):
    return {
        "version": "chrona/profile/v0.3",
        "packageId": package_id,
        "contentIdentity": "sha256:" + "a" * 64,
        "requires": {"projectFormat": "timeline/v0.7"},
        "fields": {"risk": {"type": "string", "cardinality": "one"}},
        "profiles": {"acme.item": {
            "extends": "task",
            "fields": {"risk": {
                "type": "enum", "cardinality": "one", "enumValues": enum_values,
            }},
        }},
    }


def _project(*, extensions=None, fields=None):
    return {
        "extensions": extensions or [{"packageId": "acme"}],
        "fieldRoles": {"risk": "risk"},
        "objects": {"same-id": {"type": "acme.item", "fields": fields or {}}},
    }


def test_primary_and_snapshot_bindings_retain_exact_source_package_descriptors():
    primary_project = _project(fields={"risk": "high"})
    snapshot_project = _project(fields={"risk": "low"})
    primary_manifest = _manifest("acme", enum_values=["high", "medium"])
    snapshot_manifest = _manifest("acme", enum_values=["low", "medium"])

    primary, primary_diagnostics = resolve_source_field_bindings(primary_project, {"acme": primary_manifest})
    snapshot, snapshot_diagnostics = resolve_source_field_bindings(snapshot_project, {"acme": snapshot_manifest})

    assert primary_diagnostics == snapshot_diagnostics == ()
    primary_direct = primary.read_result(
        primary_project["objects"]["same-id"]["fields"], {"field": "risk"}, object_id="same-id"
    )
    primary_alias = primary.read_result(
        primary_project["objects"]["same-id"]["fields"], {"fieldRole": "risk"}, object_id="same-id"
    )
    snapshot_alias = snapshot.read_result(
        snapshot_project["objects"]["same-id"]["fields"], {"fieldRole": "risk"}, object_id="same-id"
    )
    assert primary_direct == primary_alias
    assert primary_direct.descriptor.kind == snapshot_alias.descriptor.kind == "enum"
    assert primary_direct.descriptor.enum_values == ("high", "medium")
    assert snapshot_alias.descriptor.enum_values == ("low", "medium")


def test_absent_optional_field_keeps_its_profile_descriptor():
    project = _project(fields={})
    manifest = _manifest("acme", enum_values=["low", "high"])

    bindings, diagnostics = resolve_source_field_bindings(project, {"acme": manifest})
    read = bindings.read_result(project["objects"]["same-id"]["fields"], {"fieldRole": "risk"}, object_id="same-id")

    assert diagnostics == ()
    assert (read.field_name, read.present, read.value) == ("risk", False, None)
    assert read.descriptor.kind == "enum"
    assert read.descriptor.enum_values == ("low", "high")


def test_project_without_extensions_keeps_legacy_opaque_field_reads():
    project = _project(extensions=[], fields={"risk": "uncatalogued"})

    bindings, diagnostics = resolve_source_field_bindings(project, {})
    read = bindings.read_result(project["objects"]["same-id"]["fields"], {"fieldRole": "risk"}, object_id="same-id")

    assert diagnostics == ()
    assert read.present and read.value == "uncatalogued"
    assert read.descriptor is None


def test_catalogue_collision_diagnostics_are_preserved():
    project = _project(extensions=[{"packageId": "acme"}, {"packageId": "other"}])
    manifests = {
        "acme": _manifest("acme", enum_values=["high"]),
        "other": _manifest("other", enum_values=["low"]),
    }

    _bindings, diagnostics = resolve_source_field_bindings(project, manifests)

    assert [(item.id, item.path) for item in diagnostics] == [
        ("E_PROFILE_ID_DUPLICATE", "/extensions/1"),
    ]


def test_resolver_does_not_mutate_project_or_package_manifests():
    project = _project(fields={"risk": "high"})
    manifests = {"acme": _manifest("acme", enum_values=["high", "low"])}
    before_project = deepcopy(project)
    before_manifests = deepcopy(manifests)

    resolve_source_field_bindings(project, manifests)

    assert project == before_project
    assert manifests == before_manifests


def test_delivery_assignee_descriptor_uses_owner_normalized_entity_namespace():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[4]
    delivery = yaml.safe_load(
        (root / "conformance/implementation-delivery-profile-v0.2.yaml").read_text(encoding="utf-8")
    )
    project = {
        "project": {"id": "source"},
        "extensions": [{"packageId": "implementation-delivery"}],
        "objects": {
            "work": {"type": "implementation-delivery.work-item", "fields": {"assignees": ["same"]}},
            "same": {"type": "implementation-delivery.person", "fields": {}},
        },
        "entities": {"same": {"type": "implementation-delivery.person", "title": "Entity title"}},
    }

    bindings, diagnostics = resolve_source_field_bindings(
        project, {"implementation-delivery": delivery}
    )
    assignees = bindings.read_result(
        project["objects"]["work"]["fields"], {"field": "assignees"}, object_id="work"
    )

    assert diagnostics == ()
    assert assignees.descriptor.target_profiles == (
        "implementation-delivery.person", "implementation-delivery.team",
    )
    assert assignees.descriptor.target_namespaces == ("entities",)
    assert assignees.value == ["same"]
    assert assignees.display_value == "Entity title"
