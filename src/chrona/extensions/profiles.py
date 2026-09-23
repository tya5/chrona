"""Declarative standard-profile resolution for the initial delivery package."""
from __future__ import annotations

from typing import Any

import jsonschema
from chrona.core.diagnostics import Diagnostic
from chrona.resources import schema_document
from chrona.schema_diagnostics import explain_errors
from chrona.core.ports import SnapshotReadError, SnapshotReader

from chrona.yaml_codec import safe_load

PACKAGE_ID = "implementation-delivery"
DELIVERY_PROFILES = {"implementation-delivery.work-item", "implementation-delivery.delivery-gate"}
ACTOR_PROFILES = {"implementation-delivery.person", "implementation-delivery.team"}


def resolve_package_manifests(project: dict[str, Any], reader: SnapshotReader) -> tuple[dict[str, dict[str, Any]], list[Diagnostic]]:
    manifests: dict[str, dict[str, Any]] = {}
    diagnostics: list[Diagnostic] = []
    for index, extension in enumerate(project.get("extensions", [])):
        reference = extension.get("resource")
        if not reference:
            continue
        try:
            manifests[extension["packageId"]] = safe_load(reader.read(reference))
        except SnapshotReadError as error:
            diagnostics.append(Diagnostic(error.diagnostic_id, "Package reference did not resolve to an immutable snapshot", f"/extensions/{index}/resource"))
    return manifests, diagnostics


def resolve_profile_diagnostics(
    project: dict[str, Any], reader: SnapshotReader
) -> list[Diagnostic]:
    """Resolve pinned extension resources and return evaluation diagnostics."""
    manifests, diagnostics = resolve_package_manifests(project, reader)
    return [*diagnostics, *validate_profiles(project, manifests)]


def validate_profiles(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]] | None) -> list[Diagnostic]:
    if package_manifests is None:
        return []
    if PACKAGE_ID not in {item.get("packageId") for item in project.get("extensions", [])}:
        return []
    manifest = package_manifests.get(PACKAGE_ID)
    if manifest is None:
        return [Diagnostic("IDP-PROFILE-006", "Implementation-delivery package is unresolved", "/extensions")]
    schema = schema_document("profile-v0.2.schema.yaml")
    errors = tuple(jsonschema.Draft202012Validator(schema).iter_errors(manifest))
    if errors or manifest.get("packageId") != PACKAGE_ID:
        detail = "packageId must be 'implementation-delivery'" if not errors else explain_errors(
            errors, resource_kind="profile", resource_identity=manifest.get("packageId") if isinstance(manifest.get("packageId"), str) else None,
        ).message
        return [Diagnostic("IDP-PROFILE-006", f"Implementation-delivery package is invalid: {detail}", "/extensions")]
    diagnostics: list[Diagnostic] = []
    profiles = manifest.get("profiles", {})
    for object_id, item in project.get("objects", {}).items():
        profile_id = item.get("type")
        if profile_id not in DELIVERY_PROFILES:
            continue
        definition = profiles.get(profile_id)
        fields = definition.get("fields", {}) if isinstance(definition, dict) else {}
        values = item.get("fields", {})
        path = f"/objects/{object_id}/fields"
        if not definition or set(values) - set(fields):
            diagnostics.append(Diagnostic("IDP-PROFILE-006", "Unknown delivery profile field", path))
            continue
        for name, spec in fields.items():
            if spec.get("required") and name not in values:
                diagnostics.append(Diagnostic("IDP-PROFILE-001", f"Missing required field {name}", path))
            elif name in values:
                diagnostics.extend(_validate_value(project, name, values[name], spec, f"{path}/{name}"))
    return diagnostics


def _validate_value(project: dict[str, Any], name: str, value: Any, spec: dict[str, Any], path: str) -> list[Diagnostic]:
    values = value if spec.get("cardinality") == "many" else [value]
    if spec.get("cardinality") == "many" and not isinstance(value, list):
        return [Diagnostic("IDP-PROFILE-003", f"{name} must be an array", path)]
    if spec.get("type") == "enum" and value not in spec.get("enumValues", []):
        return [Diagnostic("IDP-STATE-001", f"Invalid {name}", path)]
    if name == "assignees":
        entities = project.get("entities", {})
        if any(entity_id not in entities or entities[entity_id].get("type") not in ACTOR_PROFILES for entity_id in values):
            return [Diagnostic("IDP-PROFILE-003", "Invalid delivery assignee", path)]
    if spec.get("type") == "resourceReference":
        schema = schema_document("revision-store-resource-ref-v0.1.schema.yaml")
        for reference in values:
            errors = tuple(jsonschema.Draft202012Validator(schema).iter_errors(reference))
            if errors:
                violation = explain_errors(
                    errors, resource_kind="revision-store-resource-ref", resource_identity=reference.get("id") if isinstance(reference.get("id"), str) else None,
                )
                return [Diagnostic("IDP-EVIDENCE-001", f"Invalid immutable evidence reference: {violation.message}", path + violation.pointer)]
            if reference.get("kind") not in spec.get("resourceKinds", []):
                return [Diagnostic("IDP-EVIDENCE-002", "Evidence kind is not allowed for this field", path)]
    return []
