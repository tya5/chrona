from copy import deepcopy
from pathlib import Path

import yaml

from chrona.operational.authoring_commands import apply_authoring_command
from chrona.operational.resources import content_identity


def _workspace() -> dict:
    return {"version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
            "body": {"project": {"id": "project", "tasks": [{"id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}}]},
                     "presentation": {"mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset.yaml"}}}}}


def _command(workspace: dict, command_type: str, payload: dict) -> dict:
    return {"version": "chrona/authoring-command/v0.1", "commandId": "change-1", "type": command_type,
            "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
            "baseRevision": content_identity(workspace), "payload": payload}


def _write(path: Path, workspace: dict) -> None:
    path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")


def test_authoring_command_updates_one_task_with_a_new_content_revision(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    command = _command(workspace, "setWorkspaceTask", {"task": {"id": "one", "title": "Renamed", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})

    result = apply_authoring_command(path, command)

    assert result["status"] == "accepted"
    assert result["resultRevision"] != result["baseRevision"]
    assert yaml.safe_load(path.read_text())["body"]["project"]["tasks"][0]["title"] == "Renamed"


def test_stale_or_illegal_command_leaves_workspace_bytes_unchanged(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    stale = _command(workspace, "setWorkspaceTask", {"task": {"id": "two", "title": "Two", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})
    stale["baseRevision"] = "sha256:" + "0" * 64
    assert apply_authoring_command(path, stale)["diagnostics"] == [{"code": "E_AUTHORING_BASE_REVISION"}]
    assert path.read_bytes() == original

    illegal = _command(workspace, "setPresentationOverride", {"overrides": {"view": {"offset": {"x": 1}}}})
    assert apply_authoring_command(path, illegal)["status"] == "rejected"
    assert path.read_bytes() == original


def test_actual_command_rejects_unknown_task_without_writing(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    command = _command(workspace, "setWorkspaceActual", {"actual": {"taskId": "missing", "actual": {"start": "2026-01-01", "finish": "2026-01-02"}}})
    result = apply_authoring_command(path, command)
    assert result["status"] == "rejected"
    assert path.read_bytes() == original
