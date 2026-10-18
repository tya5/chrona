"""Fail-closed replay and crash-recovery checks for authoring transactions."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from chrona.operational import authoring_commands as persistence
from chrona.operational.resources import OperationalResourceError, content_identity
from chrona.storage.file_transaction import PreparedFileMutation
from chrona.usecases.authoring_commands import apply_authoring_command


def _workspace() -> dict:
    return {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {
            "project": {"id": "project", "tasks": [
                {"id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}},
            ]},
            "presentation": {"mode": "guided", "binding": {
                "preset": {"id": "starter", "version": "1", "path": "preset.yaml"},
            }},
        },
    }


def _command(workspace: dict, command_id: str = "first", title: str = "Changed") -> dict:
    return {
        "version": "chrona/authoring-command/v0.1", "commandId": command_id,
        "type": "setWorkspaceTask", "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
        "baseRevision": content_identity(workspace),
        "payload": {"task": {"id": "one", "title": title, "planned": {
            "start": "2026-01-03", "finish": "2026-01-04",
        }}},
    }


def _apply(path: Path, command: dict) -> dict:
    return apply_authoring_command(path, command, transact=persistence.transact_authoring_command)


def _accepted_with_receipt(tmp_path: Path) -> tuple[Path, dict, dict, Path]:
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")
    command = _command(workspace)
    result = _apply(path, command)
    assert result["status"] == "accepted"
    _, scope = persistence._canonical_workspace(path)
    receipt = persistence._receipt_path(path.resolve(), scope, command["commandId"])
    return path, command, result, receipt


@pytest.mark.parametrize("corruption", ["malformed", "request-hash", "target", "result"])
def test_corrupt_receipt_is_fail_closed_before_replay(tmp_path, corruption):
    path, command, _result, receipt_path = _accepted_with_receipt(tmp_path)
    if corruption == "malformed":
        receipt_path.write_text("{", encoding="utf-8")
    else:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if corruption == "request-hash":
            receipt["request"]["payload"]["task"]["title"] = "tampered"
        elif corruption == "target":
            receipt["request"]["target"]["path"] = "other.yaml"
            receipt["requestIdentity"] = content_identity(receipt["request"])
        else:
            receipt["result"]["commandId"] = "other"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(OperationalResourceError) as raised:
        _apply(path, command)
    assert raised.value.code == "E_AUTHORING_REPLAY_UNAVAILABLE"


@pytest.mark.parametrize("field", ["requestIdentity", "beforeIdentity", "afterIdentity"])
def test_committed_marker_receipt_identity_mismatch_is_preserved_and_rejected(tmp_path, monkeypatch, field):
    monkeypatch.setattr(persistence, "_remove_stage",
                        lambda *_args: (_ for _ in ()).throw(OSError("leave committed marker")))
    path, command, _result, _receipt = _accepted_with_receipt(tmp_path)
    marker_path = persistence._transaction_marker(path)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if field == "requestIdentity":
        marker[field] = "sha256:" + "0" * 64
    else:
        marker[field] = "sha256:" + "0" * 64
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    with pytest.raises(OperationalResourceError) as raised:
        _apply(path, command)
    assert raised.value.code == "E_AUTHORING_AGGREGATE_RECOVERY"
    assert marker_path.is_file()


def test_failed_precommit_receipt_publication_rolls_back_owned_bundle_not_prior_receipt(tmp_path, monkeypatch):
    path, first_command, _first_result, first_receipt = _accepted_with_receipt(tmp_path)
    old_receipt = first_receipt.read_bytes()
    current = persistence.read_authoring_workspace(path)
    request = _command(current, "second", "No-op bundle")
    workspace_bytes = path.read_bytes()
    result = {"version": "accepted", "commandId": "second"}
    candidates = {path.name: workspace_bytes, "presentation/view.yaml": b"bundle"}
    prepare = lambda _path, _current: PreparedFileMutation(candidates, content_identity(current), result)
    reject = lambda code, _observed, _detail: {"code": code}
    verify = lambda *_args: None
    monkeypatch.setattr(persistence.os, "link",
                        lambda *_args: (_ for _ in ()).throw(OSError("injected receipt publication failure")))

    with pytest.raises(OSError, match="injected receipt publication failure"):
        persistence.transact_authoring_command(path, request, prepare=prepare, reject=reject,
                                               verify_receipt=verify)
    assert not (tmp_path / "presentation").exists()
    assert first_receipt.read_bytes() == old_receipt
    assert not persistence._transaction_marker(path).exists()


def test_replace_that_commits_then_raises_still_returns_and_replays_acceptance(tmp_path, monkeypatch):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")
    command = _command(workspace)
    real_replace = persistence.os.replace
    replaced = False

    def replace_then_raise(source, destination):
        nonlocal replaced
        real_replace(source, destination)
        if Path(destination) == path and not replaced:
            replaced = True
            raise OSError("injected post-replace failure")

    monkeypatch.setattr(persistence.os, "replace", replace_then_raise)
    accepted = _apply(path, command)
    assert accepted["status"] == "accepted"
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["body"]["project"]["tasks"][0]["title"] == "Changed"
    assert _apply(path, command) == accepted
    assert not persistence._transaction_marker(path).exists()
