"""The shared dispatch of the revision-bound Store commands (#813): one function for the command line and the tool core."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.operational.resources import parse_command
from chrona.operational.store_commands import (
    OPERATIONS, REQUIRED_TYPE, StoreRootOutsideWorkspace, open_store_reader, run_store_command,
)
from tests.support.store_workspace import StoreWorkspace


def _cli(monkeypatch, capsys, cwd: Path, *arguments: str) -> tuple[int, str]:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["chrona", *arguments])
    code = 0
    try:
        main()
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else 0
    return code, capsys.readouterr().out


def test_the_operations_are_the_five_command_line_commands():
    assert OPERATIONS == ("command-check", "command-apply", "actual-intake", "actual-resolve", "baseline-capture")
    assert set(REQUIRED_TYPE) <= set(OPERATIONS)


def test_check_then_apply_an_intake_through_the_shared_function(tmp_path):
    work = StoreWorkspace(tmp_path)
    command = parse_command(yaml.safe_dump(work.intake("c1", work.batch("b1"))))
    reader = open_store_reader(work.config)

    checked = run_store_command("command-check", command, reader)
    assert (checked["operation"], checked["status"]) == ("command-check", "accepted")
    applied = run_store_command("command-apply", command, reader)
    assert (applied["operation"], applied["status"]) == ("command-apply", "accepted")
    assert applied["actualIntake"]["dispositions"] == ["inserted"]


def test_an_operation_that_requires_another_type_is_rejected_and_writes_nothing(tmp_path):
    work = StoreWorkspace(tmp_path)
    command = work.intake("c1", work.batch("b1"))
    before = work.snapshot()

    result = run_store_command("baseline-capture", command, open_store_reader(work.config))

    assert result["status"] == "rejected" and result["operation"] == "baseline-capture"
    assert [row["code"] for row in result["diagnostics"]] == ["E_AUTOMATION_OPERATION_UNSUPPORTED"]
    assert result["diagnostics"][0]["message"] == (
        "baseline-capture needs a command of type 'captureSnapshot', got 'applyActualIntakeBatch'")
    assert work.snapshot() == before


def test_allowed_types_narrow_any_operation_and_nothing_is_written(tmp_path):
    work = StoreWorkspace(tmp_path)
    resolve = {**work.intake("c1", work.batch("b1")), "type": "resolveActualObservation"}
    before = work.snapshot()
    reader = open_store_reader(work.config)

    for operation in ("command-check", "command-apply"):
        result = run_store_command(operation, resolve, reader, allowed_types={"applyActualIntakeBatch", "captureSnapshot"})
        assert result["status"] == "rejected"
        assert [row["code"] for row in result["diagnostics"]] == ["E_AUTOMATION_OPERATION_UNSUPPORTED"]
        assert "resolveActualObservation" in result["diagnostics"][0]["message"]
    assert work.snapshot() == before


def test_the_command_line_and_the_shared_function_return_the_same_bytes(tmp_path, monkeypatch, capsys):
    cli_side, function_side = StoreWorkspace(tmp_path / "cli"), StoreWorkspace(tmp_path / "fn")
    for work in (cli_side, function_side):
        work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))

    code, _ = _cli(monkeypatch, capsys, cli_side.root, "command-apply", "--command", "commands/c1.yaml",
                   "--store-config", ".chrona/store.yaml", "--result", "result.json")
    command = parse_command((function_side.root / "commands" / "c1.yaml").read_text(encoding="utf-8"))
    result = run_store_command("command-apply", command, open_store_reader(function_side.config))

    assert code == 0
    assert (cli_side.root / "result.json").read_text(encoding="utf-8") == json.dumps(result, sort_keys=True)


def test_a_store_root_inside_the_workspace_is_opened(tmp_path):
    work = StoreWorkspace(tmp_path)

    reader = open_store_reader(work.config, contained_in=work.root)

    assert set(reader.roots.values()) == {work.store}


def _config(work: StoreWorkspace, root: str) -> Path:
    work.config.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [
        {"provider": "local", "identity": "test", "root": root, "integrity": "required"}]}), encoding="utf-8")
    return work.config


@pytest.mark.parametrize("shape", ["absolute", "dotdot", "workspace-itself", "parent"])
def test_a_store_root_that_leaves_the_workspace_is_refused(tmp_path, shape):
    work = StoreWorkspace(tmp_path / "ws")
    outside = tmp_path / "outside"
    outside.mkdir()
    root = {"absolute": str(outside), "dotdot": "../../outside", "workspace-itself": "../",
            "parent": "../.."}[shape]

    with pytest.raises(StoreRootOutsideWorkspace) as error:
        open_store_reader(_config(work, root), contained_in=work.root)

    assert str(error.value).startswith("E_STORE_ROOT_OUTSIDE_WORKSPACE")
    assert not list(outside.iterdir())


def test_a_store_root_that_is_a_symlink_out_is_refused(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = work.root / "linked-store"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this OS cannot create a symlink")

    with pytest.raises(StoreRootOutsideWorkspace):
        open_store_reader(_config(work, "../linked-store"), contained_in=work.root)


def test_without_contained_in_any_root_is_opened_as_the_command_line_does(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    outside = tmp_path / "outside"
    outside.mkdir()

    reader = open_store_reader(_config(work, str(outside)))

    assert set(reader.roots.values()) == {outside}
