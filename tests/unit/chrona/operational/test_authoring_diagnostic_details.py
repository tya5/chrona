"""Authoring rejection operands survive owner boundaries without changing codes."""
from __future__ import annotations

import pytest
from pathlib import Path

from chrona.core.identity import content_identity
from chrona.operational import authoring_commands as persistence
from chrona.usecases import authoring_commands, authoring_materialization


@pytest.mark.parametrize("candidates,code,operand", [
    ({"missing.yaml": b"x"}, "E_AUTHORING_AGGREGATE_CANDIDATE", "sentinel-workspace.yaml"),
    ({"sentinel-workspace.yaml": b"x", "../escape.yaml": b"x"}, "E_AUTHORING_AGGREGATE_PATH", "sentinel-workspace.yaml"),
    ({"sentinel-workspace.yaml": b"x", "one/a.yaml": b"x", "two/b.yaml": b"x"},
     "E_AUTHORING_AGGREGATE_PATH", "'two'"),
])
def test_invalid_aggregate_names_workspace_or_directory(tmp_path, candidates, code, operand):
    with pytest.raises(persistence.OperationalResourceError) as raised:
        persistence.cas_write_authoring_aggregate(tmp_path / "sentinel-workspace.yaml", "expected", candidates)
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
    marker = persistence._transaction_marker(path)
    marker.write_text("{", encoding="utf-8")
    with pytest.raises(persistence.OperationalResourceError) as raised:
        persistence._recover_incomplete_aggregate(path)
    assert raised.value.code == "E_AUTHORING_AGGREGATE_RECOVERY"
    assert marker.name in raised.value.detail and marker.is_file()


def test_missing_aggregate_writer_is_reported_with_a_stable_code(tmp_path):
    current = {"id": "sentinel-workspace"}
    command = {"commandId": "sentinel-command", "baseRevision": content_identity(current),
               "target": {"path": "workspace.yaml"}, "type": "materializePresentationPreset"}
    result = authoring_commands.apply_authoring_command(
        tmp_path / "workspace.yaml", command, read_workspace=lambda _: current, cas_write=lambda *_: None)
    assert result["diagnostics"] == [{"code": "E_AUTHORING_AGGREGATE_WRITER",
                                      "detail": "materializePresentationPreset requires an aggregate CAS writer"}]


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
