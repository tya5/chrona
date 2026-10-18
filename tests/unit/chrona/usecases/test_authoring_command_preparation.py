from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.core.identity import content_identity
from chrona.usecases.authoring_commands import (
    apply_authoring_command,
    prepare_authoring_command,
    verify_authoring_receipt,
)


def _workspace():
    return {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {
            "project": {"id": "project", "tasks": [{"id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}}]},
            "presentation": {"mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset.yaml"}}},
        },
    }


def _command(workspace, *, path="workspace.yaml", base=None):
    return {
        "version": "chrona/authoring-command/v0.1", "commandId": "change-1", "type": "setWorkspaceTask",
        "target": {"kind": "authoring-workspace", "path": path},
        "baseRevision": base or content_identity(workspace),
        "payload": {"task": {"id": "one", "title": "Renamed", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}},
    }


def test_prepare_returns_complete_workspace_candidate_and_opaque_accepted_result_without_mutation(tmp_path):
    workspace = _workspace()
    original = deepcopy(workspace)
    prepared = prepare_authoring_command(tmp_path / "workspace.yaml", workspace, _command(workspace))

    assert workspace == original
    assert prepared.result["status"] == "accepted"
    assert prepared.result["commandBaseRevision"] == content_identity(workspace)
    assert prepared.result_revision == prepared.result["resultRevision"]
    assert set(prepared.files) == {"workspace.yaml"}
    candidate = yaml.safe_load(prepared.files["workspace.yaml"])
    assert candidate["body"]["project"]["tasks"][0]["title"] == "Renamed"
    assert content_identity(candidate) == prepared.result_revision


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (lambda workspace: _command(workspace, path="alias.yaml"), "E_AUTHORING_TARGET_MISMATCH"),
        (lambda workspace: _command(workspace, base="sha256:" + "0" * 64), "E_AUTHORING_BASE_REVISION"),
    ],
)
def test_preparation_refusals_have_no_candidate_bytes(tmp_path, command, expected):
    workspace = _workspace()
    prepared = prepare_authoring_command(tmp_path / "workspace.yaml", workspace, command(workspace))

    assert prepared.files == {}
    assert prepared.result_revision is None
    assert prepared.result["status"] == "rejected"
    assert prepared.result["diagnostics"][0]["code"] == expected
    if expected == "E_AUTHORING_TARGET_MISMATCH":
        assert "workspace.yaml" in prepared.result["diagnostics"][0]["detail"]


def test_apply_wires_one_shared_transaction_port_and_does_not_publish_itself(tmp_path):
    workspace = _workspace()
    command = _command(workspace)
    seen = {}

    def transact(path, request, *, prepare, reject, verify_receipt):
        seen.update(path=path, request=request, reject=reject, verify_receipt=verify_receipt)
        return prepare(path.resolve(), workspace).result

    result = apply_authoring_command(tmp_path / "workspace.yaml", command, transact=transact)

    assert result["status"] == "accepted"
    assert seen["path"] == tmp_path / "workspace.yaml"
    assert seen["request"] is command
    assert seen["reject"]
    assert seen["verify_receipt"] is verify_authoring_receipt
    assert not (tmp_path / "workspace.yaml").exists()


def test_receipt_verifier_checks_request_result_and_both_revision_boundaries():
    workspace = _workspace()
    command = _command(workspace)
    prepared = prepare_authoring_command(Path("workspace.yaml"), workspace, command)

    verify_authoring_receipt(command, prepared.result, content_identity(workspace), prepared.result_revision)
    with pytest.raises(ValueError, match="E_AUTHORING_REPLAY_UNAVAILABLE"):
        verify_authoring_receipt(command, prepared.result, content_identity(workspace), "sha256:" + "f" * 64)
    mismatched = prepared.result | {"commandId": "other"}
    with pytest.raises(ValueError, match="E_AUTHORING_REPLAY_UNAVAILABLE"):
        verify_authoring_receipt(command, mismatched, content_identity(workspace), prepared.result_revision)
