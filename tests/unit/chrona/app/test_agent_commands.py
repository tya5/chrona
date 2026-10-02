"""The two Store-command tools of the agent tool core (#813): one test per row of the design's threat model.

Every scenario goes through ``call_tool`` over a ``WorkspaceScope`` on a scratch workspace that holds a local Store
(``tests/support/store_workspace.py``) and no SDK. The command line is the oracle for the result bytes, and the Store's
own files are the oracle for "nothing was written": the snapshot of every Store file is equal before and after.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from chrona.app.agent_tools import InvalidArgumentsError, call_tool, tool_specs
from chrona.app.agent_workspace import WorkspaceScope
from chrona.commands.actual_commands import LocalActualStore
from chrona.storage.snapshot_paths import snapshot_directory
from tests.support.store_workspace import StoreWorkspace, run_cli

OUTPUT = {spec.name: Draft202012Validator(spec.output_schema) for spec in tool_specs()}
CODES = lambda result: [row["code"] for row in result.structured["diagnostics"]]  # noqa: E731


def call(work: StoreWorkspace, name: str, arguments: dict, *, allow_write: bool = True):
    result = call_tool(WorkspaceScope(work.root), name, arguments, allow_write=allow_write)
    assert not list(OUTPUT[name].iter_errors(result.structured)), result.structured
    return result


def apply(work: StoreWorkspace, command: dict, **arguments):
    return call(work, "apply_command", {"command": work.write_command(f"{command['commandId']}.yaml", command), **arguments})


@pytest.fixture
def work(tmp_path: Path) -> StoreWorkspace:
    return StoreWorkspace(tmp_path / "ws")


# --- the happy path, and equality with the command line ---------------------------------------------------------

def test_check_then_apply_an_intake_returns_the_automation_result(work):
    command = work.intake("c1", work.batch("b1"))
    path = work.write_command("c1.yaml", command)
    before = work.snapshot()

    checked = call(work, "check_command", {"command": path})

    assert checked.structured["status"] == "ok" and checked.structured["automationResult"]["operation"] == "command-check"
    assert work.snapshot() == before and not checked.is_error

    applied = call(work, "apply_command", {"command": path})

    assert applied.structured["status"] == "ok"
    automation = applied.structured["automationResult"]
    assert automation["operation"] == "command-apply" and automation["actualIntake"] == {"dispositions": ["inserted"]}
    assert work.tip()["counter"] == 2 and work.snapshot() != before


def test_a_baseline_is_captured_by_name(work):
    path = work.write_command("capture.yaml", work.capture("capture-1", "q2"))

    result = call(work, "apply_command", {"command": path})

    assert result.structured["status"] == "ok"
    assert (work.store / "snapshots" / "q2.yaml").is_file()
    assert result.structured["automationResult"]["resultTarget"]["kind"] == "snapshot-ref"


@pytest.mark.parametrize(("tool", "operation"), [("check_command", "command-check"), ("apply_command", "command-apply")])
def test_the_result_is_byte_equal_to_the_command_line_result_file(tmp_path, monkeypatch, capsys, tool, operation):
    cli_side, tool_side = StoreWorkspace(tmp_path / "cli"), StoreWorkspace(tmp_path / "tool")
    for side in (cli_side, tool_side):
        side.write_command("c1.yaml", side.intake("c1", side.batch("b1")))

    code, _ = run_cli(monkeypatch, capsys, cli_side.root, operation, "--command", "commands/c1.yaml",
                      "--store-config", ".chrona/store.yaml", "--result", "result.json")
    result = call(tool_side, tool, {"command": "commands/c1.yaml"})

    assert code == 0
    assert json.dumps(result.structured["automationResult"], sort_keys=True) == (cli_side.root / "result.json").read_text(encoding="utf-8")
    assert tool_side.snapshot() == cli_side.snapshot()


def test_an_explicit_store_config_is_used(work):
    config = work.root / "elsewhere" / "store.yaml"
    config.parent.mkdir()
    config.write_text(work.config.read_text(encoding="utf-8").replace("root: store", "root: ../.chrona/store"), encoding="utf-8")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))

    assert call(work, "check_command", {"command": path, "storeConfig": "elsewhere/store.yaml"}).structured["status"] == "ok"


# --- the write gate ---------------------------------------------------------------------------------------------

def test_with_the_write_flag_off_apply_is_refused_and_nothing_is_opened_or_written(work):
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    before = work.snapshot()

    for arguments in ({"command": path}, {"command": "does/not/exist.yaml"}, {"command": "../escape.yaml"}):
        result = call(work, "apply_command", arguments, allow_write=False)
        assert (result.structured["status"], CODES(result), result.is_error) == ("failed", ["E_MCP_WRITE_DISABLED"], True)
        assert "--allow-write" in result.structured["diagnostics"][0]["message"]
    assert work.snapshot() == before


def test_the_preview_works_with_the_write_flag_off(work):
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))

    assert call(work, "check_command", {"command": path}, allow_write=False).structured["status"] == "ok"


def test_malformed_arguments_are_a_protocol_error_even_with_the_flag_off(work):
    for allow in (False, True):
        with pytest.raises(InvalidArgumentsError):
            call_tool(WorkspaceScope(work.root), "apply_command", {}, allow_write=allow)


@pytest.mark.parametrize("extra", ["allowMissingContentIdentity", "storeRoot", "output", "allowWrite", "confirm"])
def test_no_argument_lowers_integrity_names_a_root_or_an_output_or_enables_writes(work, extra):
    for tool in ("check_command", "apply_command"):
        with pytest.raises(InvalidArgumentsError):
            call_tool(WorkspaceScope(work.root), tool, {"command": "c.yaml", extra: True}, allow_write=True)


# --- replay -----------------------------------------------------------------------------------------------------

def test_a_replayed_command_is_a_no_op_that_returns_the_first_result(work):
    command = work.intake("c1", work.batch("b1"))
    first = apply(work, command)
    after_first = work.snapshot()

    second = apply(work, command)

    assert second.structured["status"] == "ok"
    assert second.structured["automationResult"]["replayed"] is True
    assert second.structured["automationResult"]["resultTarget"] == first.structured["automationResult"]["resultTarget"]
    assert work.snapshot() == after_first and work.tip()["counter"] == 2


def test_the_same_command_id_with_another_request_is_rejected(work):
    apply(work, work.intake("c1", work.batch("b1")))
    other_command = work.intake("c1", work.batch("b2", finish="2026-02-02", key="43"))
    after_first = work.snapshot()

    other = apply(work, other_command)

    assert (other.structured["status"], CODES(other)) == ("rejected", ["E_COMMAND_ID_REUSE"])
    row = other.structured["diagnostics"][0]
    assert row["message"] == other.structured["automationResult"]["diagnostics"][0]["message"] != "E_COMMAND_ID_REUSE"
    assert work.snapshot() == after_first


# --- stale revision ---------------------------------------------------------------------------------------------

def test_a_base_revision_that_differs_from_the_target_reference_is_rejected(work):
    command = work.intake("c1", work.batch("b1"), base="actual:0:stale")
    before = work.snapshot()

    result = apply(work, command)

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_AUTOMATION_BASE_REVISION"])
    assert result.structured["diagnostics"][0]["sourceRef"] == "/baseRevision"
    assert work.snapshot() == before


def test_a_command_built_on_a_revision_the_store_has_moved_past_is_rejected(work):
    apply(work, work.intake("c1", work.batch("b1")))
    stale = work.intake("c2", work.batch("b2", finish="2026-03-03", key="44"))  # still the initial revision
    after_first = work.snapshot()

    result = apply(work, stale)

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_AUTOMATION_TARGET_CLOSURE"])
    row = result.structured["diagnostics"][0]
    assert "is not the current tip" in row["message"]  # the engine's own message, which names both revisions
    assert row["message"] == result.structured["automationResult"]["diagnostics"][0]["message"]
    assert work.snapshot() == after_first


# --- nothing is overwritten -------------------------------------------------------------------------------------

def test_an_existing_baseline_name_is_never_overwritten(work):
    apply(work, work.capture("capture-1", "q2"))
    original = (work.store / "snapshots" / "q2.yaml").read_bytes()
    after_first = work.snapshot()

    result = apply(work, work.capture("capture-2", "q2"))

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_BASELINE_EXISTS"])
    assert (work.store / "snapshots" / "q2.yaml").read_bytes() == original
    assert work.snapshot() == after_first


def test_different_facts_for_an_existing_external_key_are_never_overwritten(work):
    first = apply(work, work.intake("c1", work.batch("b1", finish="2026-01-02")))
    current = work.actual_reference(first.structured["automationResult"]["resultTarget"]["revision"]["token"])
    conflicting = work.intake("c2", work.batch("b2", finish="2026-09-09"), target=current)
    after_first = work.snapshot()

    result = apply(work, conflicting)

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_ACTUAL_EXTERNAL_CONFLICT"])
    assert work.snapshot() == after_first


def test_no_tool_call_creates_an_actual_set_that_has_no_tip(work):
    other = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "other", "body": {"observations": []}}
    reference = work.write_resource("other-r1", "actuals/other.yaml", other, "actual-set", "other")
    command = work.intake("c1", work.batch("b1"), target=reference)
    before = work.snapshot()

    result = apply(work, command)

    assert (result.structured["status"], CODES(result)) == ("rejected", ["E_AUTOMATION_TARGET_CLOSURE"])
    assert not (work.store / "actual-tips" / "other.json").exists() and work.snapshot() == before


# --- a write, then a revert through the Store -------------------------------------------------------------------

def test_a_write_can_be_reverted_through_the_store_and_the_history_stays(work):
    initial = work.snapshot()
    initial_content = (snapshot_directory(work.store, work.initial_revision) / "actuals" / "actuals.yaml").read_bytes()
    applied = apply(work, work.intake("c1", work.batch("b1")))
    written = applied.structured["automationResult"]["resultTarget"]["revision"]["token"]
    assert written != work.initial_revision and work.tip()["token"] == written

    # The earlier revision is still there, byte for byte, and readable by its token.
    previous = yaml.safe_load(initial_content)
    store = LocalActualStore(work.store, previous)
    assert store.read()[0] == written and len(store.read()[1]["body"]["observations"]) == 1
    reverted_revision, reverted = store.write(written, previous)

    assert reverted == previous and work.tip()["token"] == reverted_revision
    assert reverted_revision not in (work.initial_revision, written)
    for name, content in initial.items():
        if name.startswith("revision-actual"):
            assert work.snapshot()[name] == content
    assert (snapshot_directory(work.store, written) / "actuals" / "actuals.yaml").is_file()


# --- path escapes, symlinks and the write surface ---------------------------------------------------------------

BAD_PATHS = ["../outside.yaml", "/etc/passwd", "commands\\c.yaml", "C:/x.yaml", "con.yaml", "a/../../x.yaml", ".", "a//b.yaml"]


@pytest.mark.parametrize("argument", ["command", "storeConfig"])
@pytest.mark.parametrize("bad", BAD_PATHS)
def test_a_path_escape_in_either_input_is_refused_before_anything_is_read(work, argument, bad):
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    arguments = {"command": path, argument: bad}
    before = work.snapshot()

    for tool in ("check_command", "apply_command"):
        result = call(work, tool, arguments)
        assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_SYNTAX"], bad
        assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"
    assert work.snapshot() == before


def _link(target: Path, destination: Path) -> None:
    try:
        destination.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("this OS cannot create a symlink")


@pytest.mark.parametrize("argument", ["command", "storeConfig"])
def test_a_symlink_that_leaves_the_workspace_is_refused(work, tmp_path, argument):
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    outside = tmp_path / "outside.yaml"  # a valid copy of the real input, so only its location is wrong
    outside.write_bytes((work.config if argument == "storeConfig" else work.root / path).read_bytes())
    _link(outside, work.root / "linked.yaml")
    arguments = {"command": path, "storeConfig": ".chrona/store.yaml", argument: "linked.yaml"}
    before = work.snapshot()

    result = call(work, "apply_command", arguments)

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"
    assert work.snapshot() == before


def _store_config(work: StoreWorkspace, root: str, name: str = "outside-store.yaml") -> str:
    path = work.root / name
    path.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [
        {"provider": "local", "identity": "test", "root": root, "integrity": "required"}]}), encoding="utf-8")
    return name


@pytest.mark.parametrize("shape", ["absolute", "dotdot", "symlink"])
@pytest.mark.parametrize("tool", ["check_command", "apply_command"])
def test_a_store_root_outside_the_workspace_is_refused_and_nothing_is_written_there(work, tmp_path, shape, tool):
    outside = tmp_path / "outside-store"
    outside.mkdir()
    if shape == "symlink":
        _link(outside, work.root / "linked-store")
    root = {"absolute": str(outside), "dotdot": "../outside-store", "symlink": "linked-store"}[shape]
    config = _store_config(work, root)
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))

    result = call(work, tool, {"command": path, "storeConfig": config})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == "/storeConfig"
    assert not list(outside.iterdir())


def test_a_missing_default_store_configuration_is_a_typed_failure(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    work.config.unlink()
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))

    result = call(work, "check_command", {"command": path})

    assert result.structured["status"] == "failed" and CODES(result) == ["E_INPUT_IO"]
    assert result.structured["diagnostics"][0]["sourceRef"] == "/storeConfig"


# --- the first release's command types, and malformed commands --------------------------------------------------

def test_a_command_type_outside_the_first_release_is_rejected_and_the_store_untouched(work):
    resolve = {**work.intake("c1", work.batch("b1")), "type": "resolveActualObservation",
               "payload": {"observationId": "x", "projectObjectId": "firmware", "project": work.project_ref}}
    before = work.snapshot()

    for tool in ("check_command", "apply_command"):
        result = call(work, tool, {"command": work.write_command("resolve.yaml", resolve)})
        assert (result.structured["status"], CODES(result)) == ("rejected", ["E_AUTOMATION_OPERATION_UNSUPPORTED"])
        assert result.structured["diagnostics"][0]["sourceRef"] == "/type"
        assert result.structured["automationResult"]["status"] == "rejected"
    assert work.snapshot() == before


def test_a_command_that_does_not_satisfy_its_schema_is_a_typed_result_not_a_traceback(work):
    path = work.write_command("bad.yaml", {"version": "chrona/command/v0.3", "commandId": "c1"})

    result = call(work, "apply_command", {"command": path})

    assert result.structured["status"] == "rejected" and CODES(result) == ["E_OPERATIONAL_SCHEMA"]


def test_a_file_that_is_not_yaml_is_a_typed_failure(work):
    (work.root / "commands").mkdir(exist_ok=True)
    (work.root / "commands" / "broken.yaml").write_text("a: [\n", encoding="utf-8")

    result = call(work, "check_command", {"command": "commands/broken.yaml"})

    assert result.structured["status"] in {"failed", "rejected"} and result.structured["diagnostics"]
    assert "Traceback" not in result.text()


# --- the result carries no host path ---------------------------------------------------------------------------

def test_no_result_carries_a_host_path(work):
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    for result in (call(work, "check_command", {"command": path}), call(work, "apply_command", {"command": path}),
                   call(work, "apply_command", {"command": path, "storeConfig": "missing.yaml"})):
        assert str(work.root) not in result.text() and str(work.root.resolve()) not in result.text()
