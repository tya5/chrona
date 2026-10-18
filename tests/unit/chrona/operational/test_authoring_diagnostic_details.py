"""Authoring rejection operands survive owner boundaries without changing codes."""
from __future__ import annotations

import pytest
from pathlib import Path

from chrona.core.identity import content_identity
from chrona.operational import authoring_commands as persistence
from chrona.usecases import authoring_commands, authoring_materialization
from chrona.storage.file_transaction import PreparedFileMutation


@pytest.mark.parametrize("candidates,code,operand", [
    ({"missing.yaml": b"x"}, "E_AUTHORING_AGGREGATE_CANDIDATE", "sentinel-workspace.yaml"),
    ({"sentinel-workspace.yaml": b"x", "../escape.yaml": b"x"}, "E_AUTHORING_AGGREGATE_PATH", "../escape.yaml"),
    ({"sentinel-workspace.yaml": b"x", "one/a.yaml": b"x", "two/b.yaml": b"x"},
     "E_AUTHORING_AGGREGATE_PATH", "share one nested directory"),
])
def test_invalid_aggregate_names_workspace_or_directory(tmp_path, candidates, code, operand):
    path = tmp_path / "sentinel-workspace.yaml"
    path.write_text("id: sentinel-workspace\n", encoding="utf-8")
    current = persistence.read_authoring_workspace(path)
    command = {"commandId": "invalid-candidate", "target": {"path": path.name},
               "baseRevision": content_identity(current)}
    with pytest.raises(persistence.OperationalResourceError) as raised:
        persistence.transact_authoring_command(
            path, command,
            prepare=lambda _path, _current: PreparedFileMutation(candidates, "sha256:" + "1" * 64, {"accepted": True}),
            reject=lambda *_args: {}, verify_receipt=lambda *_args: None,
        )
    assert raised.value.code == code and operand in raised.value.detail


def test_workspace_schema_names_file_and_expected_type(tmp_path):
    path = tmp_path / "sentinel-shape.yaml"
    path.write_text("- invalid\n", encoding="utf-8")
    with pytest.raises(persistence.OperationalResourceError) as raised:
        persistence._load_workspace(path)
    assert raised.value.code == "E_AUTHORING_WORKSPACE_SCHEMA"
    assert "sentinel-shape.yaml" in raised.value.detail and "list" in raised.value.detail


def test_recovery_names_the_invalid_marker(tmp_path):
    path = tmp_path / "sentinel-recovery.yaml"
    path.write_text("id: sentinel\n", encoding="utf-8")
    marker = persistence._transaction_marker(path)
    marker.write_text("{", encoding="utf-8")
    with pytest.raises(persistence.OperationalResourceError) as raised:
        workspace, scope = persistence._canonical_workspace(path)
        persistence._recover_transaction(workspace, scope, authoring_commands.verify_authoring_receipt)
    assert raised.value.code == "E_AUTHORING_AGGREGATE_RECOVERY"
    assert marker.name in raised.value.detail and marker.is_file()


def test_canonical_target_rejection_names_the_required_workspace_filename(tmp_path):
    path = tmp_path / "sentinel-workspace.yaml"
    path.write_text("id: sentinel-workspace\n", encoding="utf-8")
    command = {"commandId": "sentinel-command", "baseRevision": content_identity({"id": "sentinel-workspace"}),
               "target": {"path": "workspace.yaml"}, "type": "materializePresentationPreset", "payload": {}}
    result = persistence.transact_authoring_command(
        path, command, prepare=lambda *_args: pytest.fail("target mismatch must reject before preparation"),
        reject=lambda code, _identity, detail: {"code": code, "detail": detail},
        verify_receipt=lambda *_args: None,
    )
    assert result["code"] == "E_AUTHORING_TARGET_MISMATCH"
    assert "sentinel-workspace.yaml" in result["detail"]


def test_unsupported_command_names_the_type():
    with pytest.raises(ValueError) as raised:
        authoring_commands._apply({"body": {}}, {"type": "sentinelUnknown", "payload": {}})
    assert str(raised.value).startswith("E_AUTHORING_COMMAND:") and "sentinelUnknown" in str(raised.value)


@pytest.mark.parametrize("function", [authoring_materialization._relative,
    lambda value: authoring_materialization._child(Path("."), value)])
def test_materialization_path_names_the_rejected_address(function):
    with pytest.raises(ValueError) as raised:
        function("../sentinel-escape")
    assert str(raised.value).startswith("E_AUTHORING_MATERIALIZE_PATH:")
    assert "../sentinel-escape" in str(raised.value)


def test_rejected_inline_detail_is_not_part_of_the_code():
    result = authoring_commands._rejected({}, "E_AUTHORING_COMMAND: sentinel detail", "base")
    assert result["diagnostics"] == [{"code": "E_AUTHORING_COMMAND", "detail": "sentinel detail"}]
