"""Immutable Render Context closure resolution before any rendering adapter runs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jsonschema
import yaml

from chrona.resources import schema_resource
from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError


class ClosureError(ValueError):
    def __init__(self, diagnostic_id: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id


@dataclass(frozen=True)
class ClosureResource:
    kind: str
    id: str
    revision: str
    content_identity: str
    value: dict[str, Any]


def resolve_render_context(reference: dict[str, Any], reader: LocalSnapshotReader) -> tuple[dict[str, Any], tuple[ClosureResource, ...]]:
    context = _load_presentation(reference, reader, "render-context")
    if context.get("version") == "chrona/presentation/v0.3":
        resolved_context, resources = _resolve_current_context(context, reader)
        if any(item.revision != reference["revision"]["token"] for item in resources):
            raise ClosureError("E_CLOSURE_MIXED_REVISION")
        return resolved_context, resources
    body = context["body"]
    ordered = (("project", "project"), ("view", "view"), ("style", "style"), ("theme", "theme"), ("sceneProfile", "scene-profile"))
    resources = []
    revisions = set()
    for name, kind in ordered:
        item = _load_reference(body[name], reader, kind)
        resources.append(item)
        revisions.add(item.revision)
    for extension in resources[0].value.get("extensions", []):
        reference = extension.get("resource")
        if reference is None:
            continue
        package = _load_reference(reference, reader, "profile-package")
        if package.value.get("packageId") != extension.get("packageId"):
            raise ClosureError("E_CLOSURE_ID")
        resources.append(package)
        revisions.add(package.revision)
    for name, kind in (("snapshot", "snapshot-ref"), ("actual", "actual-set")):
        if name in body.get("inputs", {}):
            item = _load_reference(body["inputs"][name], reader, kind)
            resources.append(item)
            revisions.add(item.revision)
    if len(revisions) != 1:
        raise ClosureError("E_CLOSURE_MIXED_REVISION")
    return context, tuple(resources)


def _resolve_current_context(
    context: dict[str, Any], reader: LocalSnapshotReader
) -> tuple[dict[str, Any], tuple[ClosureResource, ...]]:
    schema = yaml.safe_load(schema_resource("render-context-v0.3.schema.yaml").read_text(encoding="utf-8"))
    if next(jsonschema.Draft202012Validator(schema).iter_errors(context), None) is not None:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA")
    body = context["body"]
    ordered = (
        (body["project"], "project"),
        (body["view"], "view"),
        (body["presentationPreset"], "presentation-preset"),
    )
    resources = [_load_reference(reference, reader, kind) for reference, kind in ordered]
    for extension in resources[0].value.get("extensions", []):
        package_reference = extension.get("resource")
        if package_reference is None:
            continue
        package = _load_reference(package_reference, reader, "profile-package")
        if package.value.get("packageId") != extension.get("packageId"):
            raise ClosureError("E_CLOSURE_ID")
        resources.append(package)
    optional = (
        ("actual", "actual-set"),
        ("summaryProfile", "summary-profile"),
        ("detailProfile", "review-detail-profile"),
    )
    for name, kind in optional:
        if name in body["inputs"]:
            resources.append(_load_reference(body["inputs"][name], reader, kind))
    if len({item.revision for item in resources}) != 1:
        raise ClosureError("E_CLOSURE_MIXED_REVISION")
    capabilities = body["target"]["capabilities"]
    if capabilities != sorted(capabilities):
        raise ClosureError("E_TARGET_CAPABILITY_ORDER")
    return context, tuple(resources)


def _load_reference(reference: dict[str, Any], reader: LocalSnapshotReader, expected_kind: str) -> ClosureResource:
    if reference.get("kind") != expected_kind:
        raise ClosureError("E_CLOSURE_KIND")
    try:
        payload = reader.read(reference)
    except SnapshotReadError as error:
        raise ClosureError(error.diagnostic_id) from error
    value = yaml.safe_load(payload)
    if expected_kind == "project":
        actual_id = value.get("project", {}).get("id") if isinstance(value, dict) else None
    elif expected_kind == "profile-package":
        actual_id = value.get("packageId") if isinstance(value, dict) else None
    elif expected_kind == "presentation-preset":
        if not isinstance(value, dict) or value.get("version") != "chrona/presentation-preset/v0.2":
            raise ClosureError("E_CLOSURE_KIND")
        actual_id = value.get("id")
    elif expected_kind == "review-detail-profile":
        if not isinstance(value, dict) or value.get("version") != "chrona/review-detail-profile/v0.1":
            raise ClosureError("E_CLOSURE_KIND")
        actual_id = value.get("id")
    else:
        actual_id = value.get("id") if isinstance(value, dict) else None
        if not isinstance(value, dict) or value.get("kind") != expected_kind:
            raise ClosureError("E_CLOSURE_KIND")
    if actual_id != reference.get("id"):
        raise ClosureError("E_CLOSURE_ID")
    return ClosureResource(expected_kind, actual_id, reference["revision"]["token"], reference["contentIdentity"], value)


def _load_presentation(reference: dict[str, Any], reader: LocalSnapshotReader, expected_kind: str) -> dict[str, Any]:
    item = _load_reference(reference, reader, expected_kind)
    return item.value
