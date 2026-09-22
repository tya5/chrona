"""Immutable Render Context closure resolution before any rendering adapter runs."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import jsonschema
import yaml

from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
from chrona.resources import schema_resource
from chrona.core.ports import SnapshotReadError, SnapshotReader


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


def resolve_render_context(reference: dict[str, Any], reader: SnapshotReader) -> tuple[dict[str, Any], tuple[ClosureResource, ...]]:
    context = _load_presentation(reference, reader, "render-context")
    if context.get("version") != "chrona/presentation/v0.6":
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA")
    return _resolve_layout_context(context, reader)


def _resolve_layout_context(
    context: dict[str, Any], reader: SnapshotReader
) -> tuple[dict[str, Any], tuple[ClosureResource, ...]]:
    schema = yaml.safe_load(schema_resource("render-context-v0.6.schema.yaml").read_text(encoding="utf-8"))
    if next(jsonschema.Draft202012Validator(schema).iter_errors(context), None) is not None:
        raise ClosureError("E_RENDER_CONTEXT_SCHEMA")
    body = context["body"]
    ordered = (
        (body["project"], "project"),
        (body["view"], "view"),
        (body["theme"], "theme"),
        (body["colorScheme"], "color-scheme"),
        (body["layout"], "layout-profile"),
    )
    resources = [_load_reference(reference, reader, kind) for reference, kind in ordered]
    for extension in resources[0].value.get("extensions", []):
        package_reference = extension.get("resource")
        if package_reference is not None:
            package = _load_reference(package_reference, reader, "profile-package")
            if package.value.get("packageId") != extension.get("packageId"):
                raise ClosureError("E_CLOSURE_ID")
            resources.append(package)
    for name, kind in (("actual", "actual-set"), ("summaryProfile", "summary-profile"), ("detailProfile", "review-detail-profile")):
        if name in body["inputs"]:
            resources.append(_load_reference(body["inputs"][name], reader, kind))
    if "snapshot" in body["inputs"]:
        snapshot = _load_reference(body["inputs"]["snapshot"], reader, "snapshot-ref")
        project_reference = snapshot.value.get("body", {}).get("project")
        if not isinstance(project_reference, dict):
            raise ClosureError("E_CLOSURE_KIND")
        snapshot_project = _load_reference(project_reference, reader, "project")
        if snapshot_project.id != resources[0].id:
            raise ClosureError("E_CLOSURE_ID")
        resources.extend((snapshot, ClosureResource(
            "snapshot-project", snapshot_project.id, snapshot_project.revision,
            snapshot_project.content_identity, snapshot_project.value)))
    if body["target"]["capabilities"] != sorted(body["target"]["capabilities"]):
        raise ClosureError("E_TARGET_CAPABILITY_ORDER")
    theme, scheme = resources[2], resources[3]
    try:
        context = dict(context)
        context["resolvedTheme"] = resolve_theme(theme.value, scheme.value, scheme_content_identity=scheme.content_identity)
    except ColorSchemeError as error:
        raise ClosureError(str(error)) from error
    return context, tuple(resources)


def _load_reference(reference: dict[str, Any], reader: SnapshotReader, expected_kind: str) -> ClosureResource:
    if reference.get("kind") != expected_kind:
        raise ClosureError("E_CLOSURE_KIND")
    try:
        payload = reader.read(reference)
    except SnapshotReadError as error:
        raise ClosureError(error.diagnostic_id) from error
    computed_identity = f"sha256:{sha256(payload).hexdigest()}"
    value = yaml.safe_load(payload)
    if expected_kind == "project":
        actual_id = value.get("project", {}).get("id") if isinstance(value, dict) else None
    elif expected_kind == "profile-package":
        actual_id = value.get("packageId") if isinstance(value, dict) else None
    elif expected_kind == "review-detail-profile":
        if not isinstance(value, dict) or value.get("version") != "chrona/review-detail-profile/v0.1":
            raise ClosureError("E_CLOSURE_KIND")
        actual_id = value.get("id")
    elif expected_kind == "layout-profile":
        if not isinstance(value, dict) or value.get("version") != "chrona/layout-profile/v0.2":
            raise ClosureError("E_CLOSURE_KIND")
        actual_id = value.get("id")
    else:
        actual_id = value.get("id") if isinstance(value, dict) else None
        if not isinstance(value, dict) or value.get("kind") != expected_kind:
            raise ClosureError("E_CLOSURE_KIND")
    if actual_id != reference.get("id"):
        raise ClosureError("E_CLOSURE_ID")
    return ClosureResource(expected_kind, actual_id, reference["revision"]["token"], reference.get("contentIdentity", computed_identity), value)


def _load_presentation(reference: dict[str, Any], reader: SnapshotReader, expected_kind: str) -> dict[str, Any]:
    item = _load_reference(reference, reader, expected_kind)
    return item.value
