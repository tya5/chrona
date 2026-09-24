from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys

import yaml

from chrona.usecases.authoring_commands import apply_authoring_command
import chrona.operational.authoring_commands as authoring_commands
from chrona.operational.authoring_commands import _bytes_identity, _transaction_marker, _write_marker, cas_write_authoring_aggregate, cas_write_authoring_workspace, read_authoring_workspace
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

    result = apply_authoring_command(path, command, read_workspace=read_authoring_workspace, cas_write=cas_write_authoring_workspace)

    assert result["status"] == "accepted"
    assert result["resultRevision"] != result["baseRevision"]
    assert yaml.safe_load(path.read_text())["body"]["project"]["tasks"][0]["title"] == "Renamed"


def test_aggregate_lock_uses_lazy_windows_adapter_without_fcntl(tmp_path, monkeypatch):
    calls = []
    fake = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2,
                           locking=lambda descriptor, mode, length: calls.append((descriptor, mode, length)))
    monkeypatch.setattr(authoring_commands.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    with (tmp_path / "workspace.yaml").open("a+b") as handle:
        authoring_commands._lock_file(handle)
        authoring_commands._unlock_file(handle)
    assert [mode for _, mode, _ in calls] == [fake.LK_LOCK, fake.LK_UNLCK]


def test_stale_or_illegal_command_leaves_workspace_bytes_unchanged(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    stale = _command(workspace, "setWorkspaceTask", {"task": {"id": "two", "title": "Two", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})
    stale["baseRevision"] = "sha256:" + "0" * 64
    assert apply_authoring_command(path, stale, read_workspace=read_authoring_workspace, cas_write=cas_write_authoring_workspace)["diagnostics"] == [{"code": "E_AUTHORING_BASE_REVISION"}]
    assert path.read_bytes() == original

    illegal = _command(workspace, "setPresentationOverride", {"overrides": {"view": {"offset": {"x": 1}}}})
    assert apply_authoring_command(path, illegal, read_workspace=read_authoring_workspace, cas_write=cas_write_authoring_workspace)["status"] == "rejected"
    assert path.read_bytes() == original


def test_actual_command_rejects_unknown_task_without_writing(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    command = _command(workspace, "setWorkspaceActual", {"actual": {"taskId": "missing", "actual": {"start": "2026-01-01", "finish": "2026-01-02"}}})
    result = apply_authoring_command(path, command, read_workspace=read_authoring_workspace, cas_write=cas_write_authoring_workspace)
    assert result["status"] == "rejected"
    assert path.read_bytes() == original


def test_aggregate_writer_switches_workspace_last_and_rejects_stale_or_colliding_destinations(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    explicit = deepcopy(workspace)
    explicit["body"]["presentation"] = {"mode": "explicit", "resources": {
        name: {"id": name, "kind": name, "path": f"presentation/{name}.yaml", "contentIdentity": "sha256:" + "a" * 64}
        for name in ("view", "theme", "colorScheme", "layout", "renderContext")
    }, "receipt": {"id": "receipt", "kind": "receipt", "path": "presentation/receipt.yaml", "contentIdentity": "sha256:" + "a" * 64}}
    candidates = {"workspace.yaml": yaml.safe_dump(explicit).encode(), "presentation/view.yaml": b"view"}

    assert cas_write_authoring_aggregate(path, "sha256:" + "0" * 64, candidates) is None
    assert not (tmp_path / "presentation").exists()
    result = cas_write_authoring_aggregate(path, content_identity(workspace), candidates)
    assert result == content_identity(explicit)
    assert yaml.safe_load(path.read_text())["body"]["presentation"]["mode"] == "explicit"
    assert (tmp_path / "presentation/view.yaml").read_bytes() == b"view"


def test_aggregate_writer_recovers_an_unreferenced_complete_bundle_before_retry(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    orphan = tmp_path / "presentation"
    orphan.mkdir()
    payload = b"orphan"
    (orphan / "view.yaml").write_bytes(payload)
    _write_marker(_transaction_marker(path), content_identity(workspace), "presentation", {"presentation/view.yaml": _bytes_identity(payload)})
    candidates = {"workspace.yaml": yaml.safe_dump(workspace).encode(), "presentation/view.yaml": b"replacement"}

    assert cas_write_authoring_aggregate(path, content_identity(workspace), candidates) == content_identity(workspace)
    assert (tmp_path / "presentation/view.yaml").read_bytes() == b"replacement"
    assert not _transaction_marker(path).exists()
