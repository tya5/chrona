"""Normalize the closed guided-authoring facade into existing resource contracts.

This module is the sole reader of ``authoring-workspace`` syntax.  It intentionally
returns ordinary Project/Actual/View/Theme/Scheme/Layout contracts and has no scheduler,
layout, Scene, or renderer dependency.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

import yaml

from chrona.presentation.contracts import (
    ActualSetContract, AuthoringWorkspaceContract, ClosureIdentity, ColorSchemeContract,
    ContractError, LayoutProfileContract, PresentationPresetContract, ProjectContract,
    ThemeContract, ViewContract, parse_contract,
)


class AuthoringError(ValueError):
    """A guided workspace cannot produce one closed existing-resource bundle."""


@dataclass(frozen=True)
class NormalizedAuthoring:
    """Existing typed resources constructed by the ingress adapter."""

    project: ProjectContract
    actual_set: ActualSetContract | None
    view: ViewContract
    theme: ThemeContract
    color_scheme: ColorSchemeContract
    layout: LayoutProfileContract
    project_source: Mapping[str, Any]
    actual_source: Mapping[str, Any] | None
    view_source: Mapping[str, Any]
    theme_source: Mapping[str, Any]
    color_scheme_source: Mapping[str, Any]
    layout_source: Mapping[str, Any]

    def draft_sources(self) -> tuple[tuple[str, Mapping[str, Any]], ...]:
        """Internal typed-ingress handoff; never exposed to downstream use cases."""
        return (
            ("project", self.project_source),
            *(((("actual-set", self.actual_source),) if self.actual_source is not None else ())),
            ("view", self.view_source), ("theme", self.theme_source),
            ("color-scheme", self.color_scheme_source), ("layout-profile", self.layout_source),
        )


def normalize_authoring_workspace(
    workspace: AuthoringWorkspaceContract,
    preset: PresentationPresetContract,
    resources_by_path: Mapping[str, Mapping[str, Any]],
) -> NormalizedAuthoring:
    """Produce existing typed resources from one matching guided workspace/preset.

    ``resources_by_path`` is an acquisition result owned by the caller.  The normalizer
    only validates that the already-acquired documents match the declarative preset;
    it never searches a directory or selects a fallback.
    """
    if workspace.mode != "guided" or workspace.binding is None:
        raise AuthoringError("E_AUTHORING_EXPLICIT_MODE")
    binding_preset = workspace.binding["preset"]
    if binding_preset["id"] != preset.identity.id or binding_preset["version"] != preset.package_version:
        raise AuthoringError("E_AUTHORING_PRESET_IDENTITY")
    declared = preset.resources
    loaded = {
        name: _declared_resource(name, declared[name], resources_by_path)
        for name in ("view", "theme", "colorScheme", "layout")
    }
    selected_scheme = _select_scheme(workspace, preset, resources_by_path, loaded["colorScheme"])
    view = deepcopy(loaded["view"])
    _apply_view_overrides(view, workspace.binding.get("overrides", {}).get("view", {}))
    sources: dict[str, Mapping[str, Any]] = {
        "project": _project_document(workspace),
        **({"actual-set": _actual_document(workspace)} if workspace.actuals else {}),
        "view": view,
        "theme": loaded["theme"],
        "color-scheme": selected_scheme,
        "layout-profile": loaded["layout"],
    }
    contracts = {
        kind: parse_contract(_identity(kind, source), source)
        for kind, source in sources.items()
    }
    if not isinstance(contracts["project"], ProjectContract) or not isinstance(contracts["view"], ViewContract):
        raise AuthoringError("E_AUTHORING_NORMALIZATION")
    if not isinstance(contracts["theme"], ThemeContract) or not isinstance(contracts["color-scheme"], ColorSchemeContract):
        raise AuthoringError("E_AUTHORING_NORMALIZATION")
    if not isinstance(contracts["layout-profile"], LayoutProfileContract):
        raise AuthoringError("E_AUTHORING_NORMALIZATION")
    actual = contracts.get("actual-set")
    if actual is not None and not isinstance(actual, ActualSetContract):
        raise AuthoringError("E_AUTHORING_NORMALIZATION")
    return NormalizedAuthoring(contracts["project"], actual, contracts["view"], contracts["theme"],
                               contracts["color-scheme"], contracts["layout-profile"], sources["project"],
                               sources.get("actual-set"), sources["view"], sources["theme"],
                               sources["color-scheme"], sources["layout-profile"])


def _declared_resource(name: str, declaration: Mapping[str, Any], resources: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    document = resources.get(str(declaration["path"]))
    expected_kind = {"view": "view", "theme": "theme", "colorScheme": "color-scheme", "layout": "layout-profile"}[name]
    # Layout Profile v0.3 predates the common presentation envelope and therefore
    # has no literal ``kind`` member; its declared preset slot supplies that type.
    actual_kind = document.get("kind", expected_kind) if isinstance(document, Mapping) else None
    if not isinstance(document, Mapping) or actual_kind != expected_kind or document.get("id") != declaration["id"]:
        raise AuthoringError("E_AUTHORING_PRESET_RESOURCE")
    return document


def _select_scheme(
    workspace: AuthoringWorkspaceContract, preset: PresentationPresetContract,
    resources: Mapping[str, Mapping[str, Any]], default: Mapping[str, Any],
) -> Mapping[str, Any]:
    requested = workspace.binding.get("overrides", {}).get("theme", {}).get("colorScheme")
    if requested is None:
        return default
    for declaration in preset.compatible_color_schemes:
        if declaration["id"] == requested:
            return _declared_resource("colorScheme", declaration, resources)
    raise AuthoringError("E_AUTHORING_COLOR_SCHEME")


def _apply_view_overrides(view: dict[str, Any], overrides: Mapping[str, Any]) -> None:
    body = view.get("body")
    if not isinstance(body, dict):
        raise AuthoringError("E_AUTHORING_PRESET_RESOURCE")
    if "window" in overrides:
        window = overrides["window"]
        body["window"] = {"mode": "explicit", "start": window["start"], "end": window["end"]}
    if "grouping" in overrides:
        body["grouping"] = {"by": overrides["grouping"]}
    if "visibility" in overrides:
        body["visibility"] = {**body["visibility"], **overrides["visibility"]}
    if "annotations" in overrides:
        existing = list(body.get("annotations", ()))
        identifiers = {item.get("id") for item in existing if isinstance(item, dict)}
        additions = list(overrides["annotations"])
        if identifiers.intersection(item["id"] for item in additions):
            raise AuthoringError("E_AUTHORING_ANNOTATION_ID")
        body["annotations"] = [*existing, *additions]


def _project_document(workspace: AuthoringWorkspaceContract) -> dict[str, Any]:
    project = workspace.project
    return {
        "version": "timeline/v0.6",
        "project": {"id": project["id"], **({"title": project["title"]} if "title" in project else {})},
        "objects": {
            task["id"]: {"type": "task", "title": task["title"], "schedule": {
                "mode": "fixed-span", "start": task["planned"]["start"], "end": task["planned"]["finish"],
            }} for task in project["tasks"]
        },
    }


def _actual_document(workspace: AuthoringWorkspaceContract) -> dict[str, Any]:
    return {
        "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": f"{workspace.identity.id}-actuals",
        "body": {"observations": [
            {"id": f"{item['taskId']}-actual", "sequence": index, "projectObjectId": item["taskId"],
             "actual": {"start": item["actual"]["start"], "finish": item["actual"]["finish"],
                        **({"progress": item["progress"]} if "progress" in item else {})}}
            for index, item in enumerate(workspace.actuals, start=1)
        ]},
    }


def _identity(kind: str, document: Mapping[str, Any]) -> ClosureIdentity:
    payload = yaml.safe_dump(document, sort_keys=True).encode("utf-8")
    identifier = document.get("id") if kind != "project" else document["project"]["id"]
    return ClosureIdentity(kind, str(identifier), "normalized", "sha256:" + sha256(payload).hexdigest())
