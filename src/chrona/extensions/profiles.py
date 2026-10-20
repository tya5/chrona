"""Declarative profile resolution: the delivery package plus every resolved profile package."""
from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from difflib import get_close_matches
import re
from pathlib import Path
from hashlib import sha256
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.object_references import ObjectReferenceCatalog, ObjectReferenceError
from chrona.resources import safe_load, schema_validator
from chrona.schema_diagnostics import explain_errors
from chrona.core.ports import SnapshotReadError, SnapshotReader


PACKAGE_ID = "implementation-delivery"
DELIVERY_PROFILES = {"implementation-delivery.work-item", "implementation-delivery.delivery-gate"}
ACTOR_PROFILES = {"implementation-delivery.person", "implementation-delivery.team"}


@dataclass(frozen=True)
class LocalExtensionSnapshot:
    """One validated local extension input, retained for validation and later staging."""

    package_id: str
    path: str
    content: bytes
    manifest: dict[str, Any]


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


def resolve_local_extension_manifests(project: dict[str, Any], base_dir: Path) -> tuple[dict[str, dict[str, Any]], list[Diagnostic]]:
    """Read every ``path`` extension declaration relative to the Project file's directory.

    A missing, escaping or unreadable file, an undecodable document, or a declared ``contentIdentity`` that does
    not match the bytes is an ``E_EXTENSION_UNRESOLVED`` / ``E_CONTENT_IDENTITY`` error at ``/extensions/<i>/path``.
    ``resource`` declarations need a Store reader and are left to the Context path.
    """
    snapshots, diagnostics = resolve_local_extension_snapshots(project, base_dir)
    return {item.package_id: item.manifest for item in snapshots}, diagnostics


def resolve_local_extension_snapshots(
    project: dict[str, Any], base_dir: Path,
) -> tuple[tuple[LocalExtensionSnapshot, ...], list[Diagnostic]]:
    """Acquire each local extension's validated bytes and manifest once.

    The declared relative ``path`` and exact source bytes are retained so an
    application caller can stage the same validated input elsewhere without
    reopening the source file. Containment, identity, decoding and diagnostic
    behavior are shared with :func:`resolve_local_extension_manifests`.
    """
    snapshots: list[LocalExtensionSnapshot] = []
    diagnostics: list[Diagnostic] = []
    root = base_dir.resolve()
    for index, extension in enumerate(project.get("extensions", [])):
        if not isinstance(extension, dict) or "resource" in extension or not isinstance(extension.get("path"), str):
            continue
        pointer = f"/extensions/{index}/path"
        name = extension.get("packageId", extension["path"])
        target = (root / extension["path"]).resolve()
        if not target.is_relative_to(root):
            diagnostics.append(Diagnostic("E_EXTENSION_UNRESOLVED", f"Extension package {name!r} path {extension['path']!r} leaves the Project directory", pointer))
            continue
        try:
            content = target.read_bytes()
        except OSError:
            diagnostics.append(Diagnostic("E_EXTENSION_UNRESOLVED", f"Extension package {name!r} file {extension['path']!r} was not found", pointer))
            continue
        declared = extension.get("contentIdentity")
        if declared is not None and declared != "sha256:" + sha256(content).hexdigest():
            diagnostics.append(Diagnostic("E_CONTENT_IDENTITY", f"Extension package {name!r} file {extension['path']!r} does not match its declared contentIdentity", pointer))
            continue
        try:
            manifest = safe_load(content)
        except Exception:  # noqa: BLE001 - any decoder failure is the same pointed rejection
            manifest = None
        if not isinstance(manifest, dict):
            diagnostics.append(Diagnostic("E_EXTENSION_UNRESOLVED", f"Extension package {name!r} file {extension['path']!r} is not a YAML mapping", pointer))
            continue
        # A local file's identity is its bytes: a manifest that omits the self-describing field gets the computed one.
        manifest.setdefault("contentIdentity", "sha256:" + sha256(content).hexdigest())
        snapshots.append(LocalExtensionSnapshot(
            package_id=str(extension.get("packageId", manifest.get("packageId"))),
            path=extension["path"], content=content, manifest=manifest,
        ))
    return tuple(snapshots), diagnostics


def check_project_extensions(project: dict[str, Any], *, base_dir: Path | None = None,
                             manifests: dict[str, dict[str, Any]] | None = None) -> list[Diagnostic]:
    """The one extension check shared by validate, schedule, draft render and MCP.

    ``base_dir`` resolves ``path`` declarations beside the Project file; ``manifests`` are packages a caller already
    resolved from a Store. Unresolvable declarations are errors; resolved packages go through ``validate_profiles``.
    """
    resolved = dict(manifests or {})
    diagnostics: list[Diagnostic] = []
    if base_dir is not None:
        local, diagnostics = resolve_local_extension_manifests(project, base_dir)
        resolved.update(local)
    if diagnostics or not resolved:
        return diagnostics
    visible = {**project, "extensions": [item for item in project.get("extensions", [])
                                         if isinstance(item, dict) and item.get("packageId") in resolved]}
    return validate_profiles(visible, resolved)


def resolve_profile_diagnostics(
    project: dict[str, Any], reader: SnapshotReader
) -> list[Diagnostic]:
    """Resolve pinned extension resources and return evaluation diagnostics."""
    manifests, diagnostics = resolve_package_manifests(project, reader)
    return [*diagnostics, *validate_profiles(project, manifests)]


def validate_profiles(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]] | None) -> list[Diagnostic]:
    """Validate objects against the delivery package (IDP-*) and every other resolved package (E_PROFILE_*)."""
    if package_manifests is None:
        return []
    return [*_validate_delivery(project, package_manifests), *validate_generic_profiles(project, package_manifests)]


def _validate_delivery(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]]) -> list[Diagnostic]:
    if PACKAGE_ID not in {item.get("packageId") for item in project.get("extensions", [])}:
        return []
    manifest = package_manifests.get(PACKAGE_ID)
    if manifest is None:
        return [Diagnostic("IDP-PROFILE-006", "Implementation-delivery package is unresolved", "/extensions")]
    errors = tuple(schema_validator("profile-v0.3.schema.yaml").iter_errors(manifest))
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
        validator = schema_validator("revision-store-resource-ref-v0.1.schema.yaml")
        for reference in values:
            errors = tuple(validator.iter_errors(reference))
            if errors:
                violation = explain_errors(
                    errors, resource_kind="revision-store-resource-ref", resource_identity=reference.get("id") if isinstance(reference.get("id"), str) else None,
                )
                return [Diagnostic("IDP-EVIDENCE-001", f"Invalid immutable evidence reference: {violation.message}", path + violation.pointer)]
            if reference.get("kind") not in spec.get("resourceKinds", []):
                return [Diagnostic("IDP-EVIDENCE-002", "Evidence kind is not allowed for this field", path)]
    return []


# --- Generic typed-field validation for every other resolved package (#344) ---

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _pointer(text: str) -> str:
    return text.replace("~", "~0").replace("/", "~1")


def resolve_profile_field_definitions(
    manifest: dict[str, Any], profile_id: str
) -> dict[str, Any] | None:
    """Return the effective field definitions for one profile in a package.

    Package-wide fields are the base definitions and fields declared by the
    selected profile override same-named package-wide fields. This is a
    shallow merge in terms of schema semantics, but the returned value is a
    deep copy so callers cannot mutate the manifest through nested values.
    Unknown profile IDs return ``None``; profile inheritance is intentionally
    not resolved here.
    """
    profile = manifest.get("profiles", {}).get(profile_id)
    if profile is None:
        return None
    return deepcopy({**manifest.get("fields", {}), **profile.get("fields", {})})


def resolve_profile_field_catalogue(
    project: dict[str, Any],
    package_manifests: dict[str, dict[str, Any]] | None,
) -> tuple[dict[str, dict[str, Any]], list[Diagnostic]]:
    """Resolve this Project's effective profile fields and package diagnostics.

    Each source Project gets its own catalogue. Profile field merging remains
    owned by :func:`resolve_profile_field_definitions`; this function only
    selects declarations from that Project's already-resolved manifests and
    rejects ambiguous profile IDs across packages.
    """
    if package_manifests is None:
        return {}, []

    catalogue: dict[str, dict[str, Any]] = {}
    owners: dict[str, str] = {}
    conflicted: set[str] = set()
    diagnostics: list[Diagnostic] = []
    declared = [
        (index, extension.get("packageId"))
        for index, extension in enumerate(project.get("extensions", []))
        if isinstance(extension, dict)
    ]

    # Delivery owns its declared profile names; its definition validation keeps
    # the established IDP diagnostics, independently of generic field parsing.
    for _, package_id in declared:
        manifest = package_manifests.get(package_id) if isinstance(package_id, str) else None
        if package_id == PACKAGE_ID and isinstance(manifest, dict):
            profiles = manifest.get("profiles")
            if isinstance(profiles, dict):
                owners.update({profile_id: package_id for profile_id in profiles})

    for index, package_id in declared:
        if not isinstance(package_id, str):
            continue
        manifest = package_manifests.get(package_id)
        if manifest is None:
            continue

        errors = tuple(schema_validator("profile-v0.3.schema.yaml").iter_errors(manifest))
        if errors or manifest.get("packageId") != package_id:
            # The delivery package retains its established IDP diagnostics.
            if package_id != PACKAGE_ID:
                detail = f"packageId must be {package_id!r}" if not errors else explain_errors(
                    errors, resource_kind="profile", resource_identity=package_id).message
                diagnostics.append(Diagnostic(
                    "E_PROFILE_PACKAGE_INVALID",
                    f"Profile package {package_id} is invalid: {detail}",
                    f"/extensions/{index}",
                ))
            continue

        bad_default = _invalid_default(project, manifest)
        if bad_default is not None and package_id != PACKAGE_ID:
            diagnostics.append(Diagnostic("E_PROFILE_PACKAGE_INVALID", f"Profile package {package_id} is invalid: {bad_default}", f"/extensions/{index}"))
            continue
        for profile_id in manifest["profiles"]:
            profile_fields = resolve_profile_field_definitions(manifest, profile_id)
            if profile_fields is None:
                continue
            previous_owner = owners.get(profile_id)
            if previous_owner is not None and previous_owner != package_id:
                conflicted.add(profile_id)
                catalogue.pop(profile_id, None)
                diagnostics.append(Diagnostic(
                    "E_PROFILE_ID_DUPLICATE",
                    f"Profile ID {profile_id!r} is declared by both {previous_owner!r} and {package_id!r}",
                    f"/extensions/{index}",
                ))
                continue
            owners[profile_id] = package_id
            if profile_id not in conflicted:
                catalogue[profile_id] = profile_fields

    return catalogue, diagnostics


def validate_generic_profiles(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]] | None) -> list[Diagnostic]:
    """Check objects whose ``type`` names a profile of a declared, resolved package.

    One family of pointed diagnostics: ``E_PROFILE_PACKAGE_INVALID``, ``E_PROFILE_ID_DUPLICATE``,
    ``E_PROFILE_FIELD_UNKNOWN``, ``E_PROFILE_FIELD_TYPE``,
    ``E_PROFILE_FIELD_ENUM`` and ``E_PROFILE_FIELD_REQUIRED``. An absent field
    differs from an explicit ``null``: absent is valid unless required; null is
    valid only for an optional field. Objects with an undeclared ``type`` and
    the delivery package (validated with IDP-* codes) are not touched.
    """
    definitions, diagnostics = resolve_profile_field_catalogue(project, package_manifests)
    reference_catalog: ObjectReferenceCatalog | None = None
    delivery_declared = any(
        isinstance(extension, dict) and extension.get("packageId") == PACKAGE_ID
        for extension in project.get("extensions", [])
    )
    delivery_profile_ids: set[str] = set()
    delivery_manifest = (package_manifests or {}).get(PACKAGE_ID) if delivery_declared else None
    delivery_profiles = delivery_manifest.get("profiles") if isinstance(delivery_manifest, dict) else None
    if isinstance(delivery_profiles, dict):
        delivery_profile_ids = {profile_id for profile_id in delivery_profiles if isinstance(profile_id, str)}
    for object_id, item in project.get("objects", {}).items():
        profile_id = item.get("type")
        if profile_id in delivery_profile_ids:
            continue
        profile_fields = definitions.get(profile_id)
        if profile_fields is None:
            continue
        path = f"/objects/{_pointer(object_id)}/fields"
        values = item.get("fields", {})
        for name in values:
            if name not in profile_fields:
                near = get_close_matches(name, profile_fields, n=1)
                hint = f"; did you mean {near[0]!r}" if near else ""
                diagnostics.append(Diagnostic("E_PROFILE_FIELD_UNKNOWN", f"Field {name!r} is not declared by profile {item['type']!r}{hint}", f"{path}/{_pointer(name)}"))
        for name, spec in profile_fields.items():
            if name not in values:
                if spec.get("required") and "default" not in spec:
                    diagnostics.append(Diagnostic("E_PROFILE_FIELD_REQUIRED", f"Required field {name!r} is absent", path))
            elif values[name] is None:
                if spec.get("required"):
                    diagnostics.append(Diagnostic("E_PROFILE_FIELD_REQUIRED", f"Required field {name!r} is null", f"{path}/{_pointer(name)}"))
            else:
                if spec.get("type") == "objectReference":
                    if reference_catalog is None:
                        reference_catalog = ObjectReferenceCatalog.from_project(project)
                diagnostics.extend(_generic_value(
                    project, name, values[name], spec, f"{path}/{_pointer(name)}",
                    reference_catalog=reference_catalog,
                ))
    return diagnostics


def _generic_value(
    project: dict[str, Any], name: str, value: Any, spec: dict[str, Any], path: str,
    *, reference_catalog: ObjectReferenceCatalog | None = None,
) -> list[Diagnostic]:
    if spec.get("cardinality") == "many":
        if not isinstance(value, list):
            return [Diagnostic("E_PROFILE_FIELD_TYPE", f"{name} must be an array", path)]
        found: list[Diagnostic] = []
        for index, element in enumerate(value):
            found.extend(_generic_scalar(project, name, element, spec, f"{path}/{index}", reference_catalog=reference_catalog))
        return found
    return _generic_scalar(project, name, value, spec, path, reference_catalog=reference_catalog)


def _generic_scalar(
    project: dict[str, Any], name: str, value: Any, spec: dict[str, Any], path: str,
    *, reference_catalog: ObjectReferenceCatalog | None = None,
) -> list[Diagnostic]:
    kind = spec.get("type")
    if kind == "enum":
        allowed = spec.get("enumValues", [])
        if not isinstance(value, str):
            return [Diagnostic("E_PROFILE_FIELD_TYPE", f"{name} must be a string enum value", path)]
        if value not in allowed:
            near = get_close_matches(value, allowed, n=1)
            hint = f"; did you mean {near[0]!r}" if near else ""
            return [Diagnostic("E_PROFILE_FIELD_ENUM", f"{name} value {value!r} is outside {list(allowed)}{hint}", path)]
        return []
    if kind == "objectReference":
        try:
            (reference_catalog or ObjectReferenceCatalog.from_project(project)).resolve(
                value, target_profiles=tuple(spec.get("targetProfiles", ())),
            )
        except (ObjectReferenceError, TypeError, ValueError):
            targets = spec.get("targetProfiles")
            constraint = f" of profile {list(targets)}" if targets else ""
            return [Diagnostic("E_PROFILE_FIELD_TYPE", f"{name} must name one object or entity{constraint}", path)]
        return []
    if kind == "resourceReference":
        errors = tuple(schema_validator("revision-store-resource-ref-v0.1.schema.yaml").iter_errors(value))
        if errors:
            return [Diagnostic("E_PROFILE_FIELD_TYPE", f"{name} is not a valid resource reference", path)]
        if value.get("kind") not in spec.get("resourceKinds", []):
            return [Diagnostic("E_PROFILE_FIELD_TYPE", f"{name} resource kind {value.get('kind')!r} is not allowed", path)]
        return []
    ok = {
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        "date": _is_date(value),
    }.get(kind, True)
    return [] if ok else [Diagnostic("E_PROFILE_FIELD_TYPE", f"{name} must be {kind}, found {type(value).__name__}", path)]


def _is_date(value: Any) -> bool:
    if isinstance(value, date) and not hasattr(value, "hour"):
        return True
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _invalid_default(project: dict[str, Any], manifest: dict[str, Any]) -> str | None:
    """The first declared ``default`` that is not a value of its field's declared type (#1682), else None."""
    groups = [("package", manifest.get("fields", {}))] + [(profile_id, profile.get("fields", {})) for profile_id, profile in manifest["profiles"].items()]
    for owner, fields in groups:
        for name, spec in fields.items():
            if "default" not in spec:
                continue
            if spec.get("type") in {"objectReference", "resourceReference"} or spec.get("cardinality") == "many":
                return f"{owner} field {name!r} cannot declare a default for a reference or many-valued field"
            if spec["default"] is None or _generic_value(project, name, spec["default"], spec, ""):
                return f"{owner} field {name!r} default is not a {spec.get('type')} value"
    return None
