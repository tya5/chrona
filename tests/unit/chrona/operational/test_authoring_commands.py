from copy import deepcopy
import errno
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
import yaml

from chrona.usecases.authoring_commands import apply_authoring_command, workspace_revision
import chrona.operational.authoring_commands as authoring_commands
from chrona.operational.authoring_commands import _bytes_identity, _transaction_marker, _write_transaction_marker, read_authoring_workspace, transact_authoring_command
from chrona.operational.resources import content_identity
from chrona.operational.resources import OperationalResourceError
from chrona.storage.file_transaction import PreparedFileMutation


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


def _apply(path: Path, command: dict) -> dict:
    return apply_authoring_command(path, command, transact=transact_authoring_command)


def test_authoring_command_updates_one_task_with_a_new_content_revision(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    command = _command(workspace, "setWorkspaceTask", {"task": {"id": "one", "title": "Renamed", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})

    result = _apply(path, command)

    assert result["status"] == "accepted"
    assert result["resultRevision"] != result["workspaceRevision"]
    assert result["commandBaseRevision"] == result["workspaceRevision"] == content_identity(workspace)
    assert "baseRevision" not in result
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["body"]["project"]["tasks"][0]["title"] == "Renamed"


def test_authoring_command_updates_a_japanese_workspace_at_its_current_revision(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    workspace["body"]["project"]["tasks"][0]["title"] = "設計レビュー"
    _write(path, workspace)
    command = _command(workspace, "setWorkspaceTask", {
        "task": {"id": "one", "title": "実装レビュー", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}},
    })

    result = _apply(path, command)

    assert result["status"] == "accepted"
    assert result["workspaceRevision"] == content_identity(workspace)
    serialized = path.read_bytes()
    assert "実装レビュー".encode("utf-8") in serialized
    assert b"\\u5b9f\\u88c5" not in serialized
    updated = yaml.safe_load(serialized)
    assert list(updated) == ["version", "kind", "id", "body"]
    assert list(updated["body"]["project"]["tasks"][0]) == ["id", "title", "planned"]


def test_workspace_revision_is_the_first_command_precondition_without_writing(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    revision = workspace_revision(path, read_workspace=read_authoring_workspace)
    command = _command(workspace, "setWorkspaceTask", {
        "task": {"id": "one", "title": "First edit", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}},
    }) | {"baseRevision": revision}

    result = _apply(path, command)

    assert original != path.read_bytes()
    assert result["status"] == "accepted"


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


def test_aggregate_lock_turns_windows_contention_into_an_actionable_diagnostic(tmp_path, monkeypatch):
    fake = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2,
                           locking=lambda *_args: (_ for _ in ()).throw(OSError(13, "locked")))
    monkeypatch.setattr(authoring_commands.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    workspace = tmp_path / "workspace.yaml"
    lock = tmp_path / ".workspace.yaml.authoring.lock"

    with lock.open("a+b") as handle:
        with pytest.raises(OperationalResourceError, match="E_AUTHORING_LOCK_TIMEOUT") as raised:
            authoring_commands._lock_file(handle, workspace_path=workspace, lock_path=lock)

    assert raised.value.code == "E_AUTHORING_LOCK_TIMEOUT"
    assert str(workspace) in raised.value.detail
    assert str(lock) in raised.value.detail


def test_aggregate_lock_does_not_misclassify_unrelated_windows_io_failure(tmp_path, monkeypatch):
    fake = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2,
                           locking=lambda *_args: (_ for _ in ()).throw(OSError(errno.EIO, "disk failure")))
    monkeypatch.setattr(authoring_commands.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "msvcrt", fake)

    with (tmp_path / "workspace.yaml").open("a+b") as handle:
        with pytest.raises(OSError, match="disk failure"):
            authoring_commands._lock_file(handle)


def test_stale_or_illegal_command_leaves_workspace_bytes_unchanged(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    stale = _command(workspace, "setWorkspaceTask", {"task": {"id": "two", "title": "Two", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})
    stale["baseRevision"] = "sha256:" + "0" * 64
    result = _apply(path, stale)
    diagnostic = result["diagnostics"][0]
    assert diagnostic["code"] == "E_AUTHORING_BASE_REVISION"
    assert diagnostic["expectedRevision"] == result["workspaceRevision"] == content_identity(workspace)
    assert diagnostic["receivedRevision"] == result["commandBaseRevision"] == stale["baseRevision"]
    assert "workspace_revision" in diagnostic["detail"]
    assert "chrona " not in diagnostic["detail"]
    assert path.read_bytes() == original

    illegal = _command(workspace, "setPresentationOverride", {"overrides": {"view": {"offset": {"x": 1}}}})
    assert _apply(path, illegal)["status"] == "rejected"
    assert path.read_bytes() == original


def test_actual_command_rejects_unknown_task_without_writing(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = path.read_bytes()
    command = _command(workspace, "setWorkspaceActual", {"actual": {"taskId": "missing", "actual": {"start": "2026-01-01", "finish": "2026-01-02"}}})
    result = _apply(path, command)
    assert result["status"] == "rejected"
    assert path.read_bytes() == original


def test_exact_command_retry_replays_original_result_after_later_write(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    first = _command(workspace, "setWorkspaceTask", {
        "task": {"id": "one", "title": "First", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}},
    })
    accepted = _apply(path, first)
    current = read_authoring_workspace(path)
    later = _command(current, "setWorkspaceTask", {
        "task": {"id": "one", "title": "Later", "planned": {"start": "2026-01-05", "finish": "2026-01-06"}},
    }) | {"commandId": "change-2"}
    assert _apply(path, later)["status"] == "accepted"

    before_retry = path.read_bytes()
    retried = _apply(path, first)
    assert retried == accepted | {"replayed": True, "revisionIsCurrent": False}
    assert "replayed" not in accepted
    assert path.read_bytes() == before_retry

    # The first command's latest-revision resend is not byte-equal (new base), so it is an id reuse that says the
    # first command was applied and whether its revision is current (#1892 row 3).
    resend = deepcopy(first) | {"baseRevision": content_identity(read_authoring_workspace(path))}
    reuse = _apply(path, resend)
    row = reuse["diagnostics"][0]
    assert reuse["status"] == "rejected" and row["code"] == "E_AUTHORING_COMMAND_ID_REUSE"
    assert row["firstApplied"] is True and row["appliedRevision"] == accepted["resultRevision"]
    assert row["revisionIsCurrent"] is False and "was applied" in row["detail"]
    assert path.read_bytes() == before_retry

    current_resend = deepcopy(later) | {"baseRevision": content_identity(read_authoring_workspace(path))}
    current_resend["payload"]["task"]["title"] = "Later again"
    latest = _apply(path, current_resend)["diagnostics"][0]
    assert latest["firstApplied"] is True and latest["revisionIsCurrent"] is True


def test_reused_command_id_with_changed_target_is_id_reuse_before_target_rejection(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    original = _command(workspace, "setWorkspaceTask", {
        "task": {"id": "one", "title": "First", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}},
    })
    assert _apply(path, original)["status"] == "accepted"

    changed = deepcopy(original)
    changed["target"]["path"] = "other.yaml"
    replay = _apply(path, changed)
    assert replay["status"] == "rejected"
    assert replay["diagnostics"][0]["code"] == "E_AUTHORING_COMMAND_ID_REUSE"


def test_noop_command_commits_and_replays_receipt_without_rewriting_workspace(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    command = _command(workspace, "selectPresentationPreset", {
        "preset": deepcopy(workspace["body"]["presentation"]["binding"]["preset"]),
    })
    result = _apply(path, command)
    assert result["status"] == "accepted"
    assert result["resultRevision"] == result["workspaceRevision"]
    after_first = path.read_bytes()
    assert _transaction_marker(path).exists() is False
    assert _apply(path, command) == result | {"replayed": True, "revisionIsCurrent": True}
    assert path.read_bytes() == after_first


def test_noop_bundle_recovery_verifies_resource_outputs_before_replay(tmp_path, monkeypatch):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    workspace_bytes = path.read_bytes()
    request = {"commandId": "noop-bundle", "target": {"path": path.name},
               "baseRevision": content_identity(workspace)}
    result = {"status": "accepted", "commandId": "noop-bundle"}
    candidates = {path.name: workspace_bytes, "presentation/view.yaml": b"view"}
    prepare = lambda _path, _current: PreparedFileMutation(candidates, content_identity(workspace), result)
    reject = lambda code, _observed, _detail: {"code": code}
    verify = lambda request, actual, before, after: (
        None if request["commandId"] == actual["commandId"] and before == after
        else (_ for _ in ()).throw(ValueError("receipt mismatch"))
    )
    monkeypatch.setattr(authoring_commands, "_cleanup_committed_marker", lambda *_args: None)

    assert transact_authoring_command(path, request, prepare=prepare, reject=reject,
                                      verify_receipt=verify) == result
    marker = _transaction_marker(path)
    assert marker.is_file() and (tmp_path / "presentation/view.yaml").read_bytes() == b"view"
    assert transact_authoring_command(path, request, prepare=prepare, reject=reject,
                                      verify_receipt=verify) == result | {"replayed": True, "revisionIsCurrent": True}
    assert not marker.exists()
    assert path.read_bytes() == workspace_bytes


def test_verified_commit_replays_when_cleanup_waits_but_blocks_new_commands(tmp_path, monkeypatch):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    command = _command(workspace, "selectPresentationPreset", {
        "preset": deepcopy(workspace["body"]["presentation"]["binding"]["preset"]),
    })
    monkeypatch.setattr(authoring_commands, "_remove_stage",
                        lambda *_args: (_ for _ in ()).throw(OSError("cleanup unavailable")))
    accepted = _apply(path, command)
    assert accepted["status"] == "accepted"
    assert _transaction_marker(path).is_file()
    assert _apply(path, command) == accepted | {"replayed": True, "revisionIsCurrent": True}

    new_command = deepcopy(command) | {"commandId": "new-command"}
    blocked = _apply(path, new_command)
    assert blocked["status"] == "rejected"
    assert blocked["diagnostics"][0]["code"] == "E_AUTHORING_AGGREGATE_RECOVERY"


def test_identity_case_normalization_does_not_change_canonical_target_filename(tmp_path, monkeypatch):
    path = tmp_path / "MiXeD.yaml"
    _write(path, _workspace())
    monkeypatch.setattr(authoring_commands.os.path, "normcase", lambda value: value.lower())
    canonical, scope = authoring_commands._canonical_workspace(path)
    assert canonical.name == "MiXeD.yaml"
    assert scope.startswith("sha256:")


def test_staging_identity_is_scoped_to_the_canonical_workspace(tmp_path):
    paths = [tmp_path / name for name in ("first.yaml", "second.yaml")]
    for path in paths:
        _write(path, _workspace())
    scopes = [authoring_commands._canonical_workspace(path)[1] for path in paths]
    stages = [authoring_commands._stage_name("shared-command-id", scope) for scope in scopes]
    assert stages[0] != stages[1]
    assert stages[0] == authoring_commands._stage_name("shared-command-id", scopes[0])


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"], ids=["lf", "crlf"])
def test_recovery_preserves_unowned_staging_entries(tmp_path, monkeypatch, line_ending):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    original_bytes = yaml.safe_dump(workspace, sort_keys=False).encode("utf-8").replace(b"\n", line_ending)
    path.write_bytes(original_bytes)
    command = _command(workspace, "setWorkspaceTask", {
        "task": {"id": "one", "title": "Candidate", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}},
    })
    original_write = authoring_commands._write_new_bytes
    injected = False

    def write_then_inject(destination, payload):
        nonlocal injected
        original_write(destination, payload)
        if not injected and destination.name == path.name:
            (destination.parent / "unowned.txt").write_text("preserve", encoding="utf-8")
            injected = True

    monkeypatch.setattr(authoring_commands, "_write_new_bytes", write_then_inject)
    monkeypatch.setattr(authoring_commands.os, "link", lambda *_args: (_ for _ in ()).throw(OSError("publish failed")))

    with pytest.raises(OperationalResourceError) as raised:
        _apply(path, command)
    assert raised.value.code == "E_AUTHORING_AGGREGATE_RECOVERY"
    _, scope_identity = authoring_commands._canonical_workspace(path)
    stage = tmp_path / authoring_commands._stage_name(command["commandId"], scope_identity)
    assert (stage / "unowned.txt").read_text(encoding="utf-8") == "preserve"
    assert path.read_bytes() == original_bytes


def test_transaction_switches_workspace_last_and_rejects_stale_or_colliding_destinations(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    explicit = deepcopy(workspace)
    explicit["body"]["presentation"] = {"mode": "explicit", "resources": {
        name: {"id": name, "kind": name, "path": f"presentation/{name}.yaml", "contentIdentity": "sha256:" + "a" * 64}
        for name in ("view", "theme", "colorScheme", "layout", "renderContext")
    }, "receipt": {"id": "receipt", "kind": "receipt", "path": "presentation/receipt.yaml", "contentIdentity": "sha256:" + "a" * 64}}
    candidates = {"workspace.yaml": yaml.safe_dump(explicit).encode(), "presentation/view.yaml": b"view"}
    request = {"commandId": "bundle", "target": {"path": path.name}, "baseRevision": content_identity(workspace)}
    prepare = lambda _path, _current: PreparedFileMutation(candidates, content_identity(explicit), {"ok": True})
    verify = lambda *_args: None
    reject = lambda code, _observed, _detail: {"code": code}

    assert transact_authoring_command(path, request | {"baseRevision": "sha256:" + "0" * 64},
                                      prepare=prepare, reject=reject, verify_receipt=verify)["code"] == "E_AUTHORING_BASE_REVISION"
    assert not (tmp_path / "presentation").exists()
    result = transact_authoring_command(path, request, prepare=prepare, reject=reject, verify_receipt=verify)
    assert result == {"ok": True}
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["body"]["presentation"]["mode"] == "explicit"
    assert (tmp_path / "presentation/view.yaml").read_bytes() == b"view"


def test_transaction_rolls_back_proven_legacy_bundle_before_retry(tmp_path):
    workspace, path = _workspace(), tmp_path / "workspace.yaml"
    _write(path, workspace)
    orphan = tmp_path / "presentation"
    orphan.mkdir()
    payload = b"orphan"
    (orphan / "view.yaml").write_bytes(payload)
    _write_transaction_marker(_transaction_marker(path), {
        "workspaceIdentity": content_identity(workspace), "directory": "presentation",
        "resources": {"presentation/view.yaml": _bytes_identity(payload)},
    })
    command = _command(workspace, "setWorkspaceTask", {"task": {"id": "one", "title": "retry", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})

    result = _apply(path, command)
    assert result["status"] == "accepted"
    assert not (tmp_path / "presentation").exists()
    assert not _transaction_marker(path).exists()


# --------------------------------------------------------------------------------------------
# S1d: the path guard (T1) on `target.path` and `payload.preset.path`
#
# Each row is one string, whether `parse_authoring_command` accepts it now, and today's verdict of the
# stage after the parser.  Before the guard every non-empty row parsed (the fields were "any non-empty
# string"), so the only check on `target.path` was name equality in `apply_authoring_command` and the
# only check on the preset path was the authoring-workspace contract that apply builds.  The
# `downstream` column is the verdict of `apply_authoring_command` on a command that skips the parser:
# the stage the guard now precedes, unchanged by it.
# --------------------------------------------------------------------------------------------

_BASE = "E_AUTHORING_BASE_REVISION"
_STORED = "sha256:" + "2" * 64

# (value, parse accepts it now, verdict of apply for a workspace stored as `workspace.yaml`)
TARGET_PATH_MATRIX = [
    ("workspace.yaml", True, "accepted"),
    ("my plan.yaml", True, _BASE),
    ("計画.yaml", True, _BASE),
    ("../workspace.yaml", False, _BASE),
    ("/abs/workspace.yaml", False, _BASE),
    ("sub/workspace.yaml", False, _BASE),
    ("a\\b.yaml", False, _BASE),
    ("work\x00space.yaml", False, _BASE),
    ("workspace.yaml\n", False, _BASE),
    ("a\tb.yaml", False, _BASE),
    (".", False, _BASE),
    ("..", False, _BASE),
    ("", False, _BASE),
]
# Names that apply accepts when the workspace file really carries that name (name equality is its only
# check) and that the guard now refuses: the one deliberate narrowing of T1 (design register T1).
NARROWED_BY_THE_GUARD = ["a\\b.yaml", "work\x00space.yaml", "workspace.yaml\n", "a\tb.yaml", ".."]

PRESET_PATH_MATRIX = [
    ("preset.yaml", True, "accepted"),
    ("presets/starter.yaml", True, "accepted"),
    ("../preset.yaml", False, "E_RESOURCE_SCHEMA"),
    ("/etc/preset.yaml", False, "E_RESOURCE_SCHEMA"),
    ("a/./b.yaml", False, "E_RESOURCE_SCHEMA"),
    ("a/../b.yaml", False, "E_RESOURCE_SCHEMA"),
    ("a\\b.yaml", False, "E_RESOURCE_SCHEMA"),
    ("my preset.yaml", False, "E_RESOURCE_SCHEMA"),
    ("計画.yaml", False, "E_RESOURCE_SCHEMA"),
    ("preset\x00.yaml", False, "E_RESOURCE_SCHEMA"),
    (".hidden.yaml", False, "E_RESOURCE_SCHEMA"),
    ("", False, "E_RESOURCE_SCHEMA"),
    # `$` accepts one trailing newline in the strict path (T3 is not adopted): the parser and the
    # workspace contract agree, so the value is accepted by both and stays accepted.
    ("preset.yaml\n", True, "accepted"),
]


def _parse(tmp_path: Path, document: dict) -> str:
    """`parsed`, or the error code and pointer of `parse_authoring_command`."""
    from chrona.usecases.authoring_commands import parse_authoring_command

    path = tmp_path / "command.json"
    path.write_text(json.dumps(document, ensure_ascii=True), encoding="utf-8")
    try:
        parse_authoring_command(path)
    except ValueError as error:
        code, _, rest = str(error).partition(": ")
        return f"{code} {rest.partition(': ')[0]}"
    return "parsed"


def _downstream(document: dict, workspace: dict, workspace_name: str = "workspace.yaml") -> str:
    """The verdict of `apply_authoring_command` alone, on an in-memory workspace (no parser)."""
    def transact(_path, _command, *, prepare, reject, verify_receipt):
        current = deepcopy(workspace)
        if document["baseRevision"] != content_identity(current):
            return reject("E_AUTHORING_BASE_REVISION", content_identity(current), "")
        prepared = prepare(Path(workspace_name), current)
        return prepared.result if prepared.result_revision is not None else prepared.result
    result = apply_authoring_command(Path(workspace_name), document, transact=transact)
    return "accepted" if result["status"] == "accepted" else result["diagnostics"][0]["code"].partition(":")[0]


def _task_command(workspace: dict, path: str) -> dict:
    command = _command(workspace, "setWorkspaceTask", {"task": {"id": "one", "title": "T", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})
    command["target"] = {"kind": "authoring-workspace", "path": path}
    return command


@pytest.mark.parametrize(("value", "parses", "downstream"), TARGET_PATH_MATRIX)
def test_authoring_command_target_path_guard_matrix(tmp_path, value, parses, downstream):
    workspace = _workspace()
    command = _task_command(workspace, value)

    verdict = _parse(tmp_path, command)
    assert (verdict == "parsed") is parses, verdict
    if not parses:
        assert verdict.startswith("E_AUTHORING_COMMAND_SCHEMA /target/path"), verdict
    actual_downstream = _downstream(command, workspace)
    if value != "workspace.yaml":
        # The transaction port canonicalizes the target before preparation; this is
        # now the explicit target-mismatch result rather than a later CAS mismatch.
        assert actual_downstream == "E_AUTHORING_TARGET_MISMATCH"
    else:
        assert actual_downstream == downstream
    if value in NARROWED_BY_THE_GUARD and Path(value).name == value:
        # apply alone would have accepted a workspace stored under exactly this name
        assert _downstream(command, workspace, value) == "accepted"


@pytest.mark.parametrize("name", ["workspace.yaml", "my plan.yaml", "計画.yaml"])
def test_authoring_command_still_works_for_a_workspace_named_with_spaces_or_non_ascii(tmp_path, name):
    workspace, path = _workspace(), tmp_path / name
    _write(path, workspace)
    command = _command(workspace, "setWorkspaceTask", {"task": {"id": "one", "title": "Renamed", "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}})
    command["target"]["path"] = name
    command_file = tmp_path / "command.yaml"
    command_file.write_text(yaml.safe_dump(command, allow_unicode=True), encoding="utf-8")

    from chrona.usecases.authoring_commands import parse_authoring_command
    result = _apply(path, parse_authoring_command(command_file))

    assert result["status"] == "accepted"
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["body"]["project"]["tasks"][0]["title"] == "Renamed"


@pytest.mark.parametrize(("value", "parses", "downstream"), PRESET_PATH_MATRIX)
def test_authoring_command_preset_path_guard_matrix(tmp_path, value, parses, downstream):
    workspace = _workspace()
    command = _command(workspace, "selectPresentationPreset", {"preset": {"id": "starter", "version": "1", "path": value}})

    verdict = _parse(tmp_path, command)
    assert (verdict == "parsed") is parses, verdict
    if not parses:
        assert verdict.startswith("E_AUTHORING_COMMAND_SCHEMA /payload/preset/path"), verdict
    assert _downstream(command, workspace) == downstream
    # The guard only moves a rejection earlier: it never refuses a value that apply accepts.
    assert parses or downstream != "accepted"
