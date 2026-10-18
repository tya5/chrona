"""Preparation and validation for newly initialized guided workspaces."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

import yaml

from chrona.core.identity import content_identity
from chrona.presentation.model.closure import resolve_guided_draft_render
from chrona.resources import safe_load
from chrona.usecases.preset_library import DEFAULT_PRESET_ID, copy_builtin_preset, is_builtin_preset_id


@dataclass(frozen=True)
class WorkspaceCreated:
    workspace: Path
    workspace_revision: str


def create_workspace(
    directory: Path,
    project: Mapping[str, Any],
    preset: str = DEFAULT_PRESET_ID,
    *,
    publish: Callable[[Path, Mapping[str, bytes]], None],
) -> WorkspaceCreated:
    """Prepare and validate a guided workspace, then delegate publication."""
    destination = Path(directory)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"E_AUTHORING_WORKSPACE_EXISTS: destination {destination} already exists")
    parent = destination.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError(f"E_WORKSPACE_PARENT: destination parent {parent} must be an existing real directory")
    if not isinstance(preset, str) or not is_builtin_preset_id(preset):
        raise ValueError(f"E_BUILTIN_PRESET_UNKNOWN: {preset!r} is not a builtin preset")
    if not isinstance(project, Mapping):
        raise ValueError("E_AUTHORING_PROJECT_SCHEMA: project must be an object")
    project_value = deepcopy(dict(project))
    project_id = project_value.get("id")
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("E_AUTHORING_PROJECT_SCHEMA: project.id must be a non-empty string")

    # Stage outside the destination so invalid input or preset closure cannot
    # leave a partially visible workspace.
    with tempfile.TemporaryDirectory(prefix="chrona-workspace-", dir=parent) as temporary:
        staged = Path(temporary)
        preset_path = copy_builtin_preset(preset, staged / "preset")
        preset_document = safe_load(preset_path.read_bytes())
        if not isinstance(preset_document, dict):
            raise ValueError("E_AUTHORING_PRESET_SCHEMA: copied preset must be an object")
        package = preset_document.get("body", {}).get("package", {})
        version = package.get("version") if isinstance(package, dict) else None
        if not isinstance(version, str) or not version:
            raise ValueError("E_AUTHORING_PRESET_SCHEMA: copied preset has no package version")

        workspace = {
            "version": "chrona/authoring-workspace/v0.1",
            "kind": "authoring-workspace",
            "id": f"{project_id}-workspace",
            "body": {
                "project": project_value,
                "presentation": {"mode": "guided", "binding": {"preset": {
                    "id": str(preset_document["id"]), "version": version, "path": "preset/preset.yaml",
                }}},
            },
        }
        workspace_path = staged / "workspace.yaml"
        workspace_path.write_text(
            yaml.safe_dump(workspace, allow_unicode=True, sort_keys=False), encoding="utf-8",
        )
        # Resolving the full immutable guided closure validates the compact
        # project, copied preset, and all declared preset resources together.
        resolve_guided_draft_render(workspace_path=workspace_path)
        revision = content_identity(workspace)
        files = {
            path.relative_to(staged).as_posix(): path.read_bytes()
            for path in sorted(staged.rglob("*")) if path.is_file()
        }
        publish(destination, files)
    return WorkspaceCreated(destination / "workspace.yaml", revision)


def validate_workspace(path: Path, *, read_workspace: Callable[[Path], dict[str, Any]]) -> str:
    """Validate the complete guided resource closure and return its CAS identity."""
    workspace_path = Path(path)
    workspace = read_workspace(workspace_path)
    resolve_guided_draft_render(workspace_path=workspace_path)
    return content_identity(workspace)
