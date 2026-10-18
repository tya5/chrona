"""Durable Actual inverse operations use verified command history (#902)."""
from hashlib import sha256
import json
from pathlib import Path

import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.operational.command_engine import apply_actual_command, check_command
from chrona.operational.resources import content_identity
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.storage.snapshot_paths import snapshot_directory


def _reference(root: Path, token: str, address: str, value: dict, kind: str, identifier: str):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = snapshot_directory(root, token) / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "test"},
            "address": address, "revision": {"token": token},
            "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def _world(root: Path):
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals",
              "body": {"observations": []}}
    store = LocalActualStore(root, actual)
    revision, value = store.read()
    target = _reference(root, revision, "actuals/actuals.yaml", value, "actual-set", "actuals")
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [],
               "objects": {"one": {"type": "milestone"}, "two": {"type": "milestone"}}, "relations": []}
    project_ref = _reference(root, "project-r1", "project.yaml", project, "project", "p")
    batches = []
    for number, object_id in ((1, "one"), (2, "two")):
        batch = {"version": "chrona/actual-intake-batch/v0.2", "kind": "actual-intake-batch",
                 "id": f"batch-{number}", "body": {"source": {"system": "source",
                 "contentIdentity": "sha256:" + str(number) * 64}, "records": [
                     {"externalKey": str(number), "projectObjectId": object_id,
                      "actual": {"finish": f"2026-01-0{number + 1}"}}]}}
        batches.append(_reference(root, f"batch-r{number}", f"batch-{number}.yaml", batch,
                                  "actual-intake-batch", f"batch-{number}"))
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(root)}]})
    return reader, target, project_ref, batches


def _ordinary(command_id, target, project, batch, *, base=None):
    return {"version": "chrona/command/v0.4", "commandId": command_id, "type": "applyActualIntakeBatch",
            "target": target, "baseRevision": base or target["revision"]["token"],
            "expectedContentIdentity": target["contentIdentity"],
            "payload": {"batch": batch, "project": project}}


def _inverse(command_id, operation, target, linked_id):
    key = "commandId" if operation == "revertActualCommand" else "revertCommandId"
    return {"version": "chrona/command/v0.4", "commandId": command_id, "type": operation,
            "target": target, "baseRevision": target["revision"]["token"],
            "expectedContentIdentity": target["contentIdentity"], "payload": {key: linked_id}}


def _apply(reader, command):
    result = apply_actual_command(reader, command)
    assert result["diagnostics"] == [] or result["status"] == "rejected"
    return result


def _current(root):
    return LocalActualStore(root, {"id": "actuals"}).read()


def test_two_actual_writes_can_be_reverted_and_redone_in_order_across_cycles(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    first = _apply(reader, _ordinary("o1", target, project, batches[0]))
    assert first["status"] == "accepted"
    second = _apply(reader, _ordinary("o2", first["resultTarget"], project, batches[1]))
    assert second["status"] == "accepted"

    undo_second = _apply(reader, _inverse("u2", "revertActualCommand", second["resultTarget"], "o2"))
    undo_first = _apply(reader, _inverse("u1", "revertActualCommand", undo_second["resultTarget"], "o1"))
    assert undo_second["status"] == undo_first["status"] == "accepted"
    assert len(_current(tmp_path)[1]["body"]["observations"]) == 0

    redo_first = _apply(reader, _inverse("r1", "redoActualCommand", undo_first["resultTarget"], "u1"))
    redo_second = _apply(reader, _inverse("r2", "redoActualCommand", redo_first["resultTarget"], "u2"))
    assert redo_first["status"] == redo_second["status"] == "accepted"
    assert [row["id"] for row in _current(tmp_path)[1]["body"]["observations"]] == ["source:1", "source:2"]

    undo_redo_second = _apply(reader, _inverse("ur2", "revertActualCommand", redo_second["resultTarget"], "r2"))
    undo_redo_first = _apply(reader, _inverse("ur1", "revertActualCommand", undo_redo_second["resultTarget"], "r1"))
    redo_redo_first = _apply(reader, _inverse("rr1", "redoActualCommand", undo_redo_first["resultTarget"], "ur1"))
    assert redo_redo_first["status"] == "accepted", redo_redo_first.get("diagnostics")
    redo_redo_second = _apply(reader, _inverse("rr2", "redoActualCommand", redo_redo_first["resultTarget"], "ur2"))
    assert all(result["status"] == "accepted" for result in
               (undo_redo_second, undo_redo_first, redo_redo_first, redo_redo_second))
    assert len(_current(tmp_path)[1]["body"]["observations"]) == 2


def test_inverse_retry_replays_without_a_second_revision_and_stale_base_rejects(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    origin = _apply(reader, _ordinary("origin", target, project, batches[0]))
    undo = _inverse("undo", "revertActualCommand", origin["resultTarget"], "origin")
    accepted = _apply(reader, undo)
    before_retry = _current(tmp_path)[0]
    replay = _apply(reader, undo)
    assert accepted["status"] == "accepted" and replay["replayed"] is True
    assert _current(tmp_path)[0] == before_retry
    stale = undo | {"commandId": "stale", "baseRevision": "old"}
    assert check_command(reader, stale)["diagnostics"][0]["code"] == "E_AUTOMATION_BASE_REVISION"


def test_changed_actual_and_cross_actual_history_reject_without_writing(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    first = _apply(reader, _ordinary("one", target, project, batches[0]))
    second = _apply(reader, _ordinary("two", first["resultTarget"], project, batches[1]))
    before = _current(tmp_path)
    changed = _apply(reader, _inverse("bad", "revertActualCommand", second["resultTarget"], "one"))
    assert changed["status"] == "rejected"
    assert changed["diagnostics"][0]["code"] == "E_COMMAND_NOT_REVERSIBLE"
    assert _current(tmp_path) == before

    other_value = before[1] | {"id": "other"}
    other_store = LocalActualStore(tmp_path, other_value)
    other_revision, other_actual = other_store.read()
    other_target = _reference(tmp_path, other_revision, "other/other.yaml", other_actual, "actual-set", "other")
    request = _inverse("foreign", "revertActualCommand", other_target, "one")
    result = _apply(reader, request)
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"

    alias_reader = ConfiguredStoreReader({"stores": [
        {"provider": "local", "identity": "test", "root": str(tmp_path)},
        {"provider": "local", "identity": "alias", "root": str(tmp_path)},
    ]})
    alias_target = second["resultTarget"] | {"store": {"provider": "local", "identity": "alias"}}
    wrong_store = check_command(alias_reader, _inverse("wrong-store", "revertActualCommand", alias_target, "one"))
    assert wrong_store["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"


def test_legacy_origin_can_revert_but_cannot_redo_without_intent(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    origin = _apply(reader, _ordinary("legacy", target, project, batches[0]))
    ledger_path = tmp_path / "command-replays.json"
    rows = json.loads(ledger_path.read_text())
    rows["legacy"].pop("request")
    ledger_path.write_text(json.dumps(rows))
    undo = _apply(reader, _inverse("legacy-undo", "revertActualCommand", origin["resultTarget"], "legacy"))
    assert undo["status"] == "accepted"
    redo = _apply(reader, _inverse("legacy-redo", "redoActualCommand", undo["resultTarget"], "legacy-undo"))
    assert redo["status"] == "rejected"
    assert redo["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"


def test_history_validates_request_target_without_requiring_optional_content_identity(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    origin = _apply(reader, _ordinary("omitted-identity", target, project, batches[0]))
    ledger_path = tmp_path / "command-replays.json"
    rows = json.loads(ledger_path.read_text())
    request = rows["omitted-identity"]["request"]
    request["target"].pop("contentIdentity")
    rows["omitted-identity"]["requestIdentity"] = content_identity(request)
    rows["omitted-identity"]["result"]["requestContentIdentity"] = content_identity(request)
    ledger_path.write_text(json.dumps(rows))
    undo = _apply(reader, _inverse("undo-omitted", "revertActualCommand", origin["resultTarget"], "omitted-identity"))
    assert undo["status"] == "accepted", undo.get("diagnostics")


def test_snapshot_origin_is_not_reversible(tmp_path):
    reader, target, project_ref, _ = _world(tmp_path)
    capture = {"version": "chrona/command/v0.4", "commandId": "snapshot", "type": "captureSnapshot",
               "target": project_ref, "baseRevision": project_ref["revision"]["token"],
               "payload": {"snapshotId": "base", "registry": {"provider": "local", "identity": "test"}}}
    assert _apply(reader, capture)["status"] == "accepted"
    inverse = _inverse("undo-snapshot", "revertActualCommand", target, "snapshot")
    result = _apply(reader, inverse)
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["code"] == "E_COMMAND_NOT_REVERSIBLE"


def test_corrupt_history_noop_and_snapshot_are_not_reversible(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    origin = _apply(reader, _ordinary("origin", target, project, batches[0]))
    # A second distinct request for the same already-present facts is accepted without a state transition.
    noop = _apply(reader, _ordinary("noop", origin["resultTarget"], project, batches[0]))
    assert noop["status"] == "accepted"
    not_reversible = _apply(reader, _inverse("undo-noop", "revertActualCommand", noop["resultTarget"], "noop"))
    assert not_reversible["diagnostics"][0]["code"] == "E_COMMAND_NOT_REVERSIBLE"

    rows_path = tmp_path / "command-replays.json"
    rows = json.loads(rows_path.read_text())
    rows["origin"]["result"]["resultTarget"]["contentIdentity"] = "sha256:" + "0" * 64
    rows_path.write_text(json.dumps(rows))
    corrupt = check_command(reader, _inverse("corrupt-check", "revertActualCommand", noop["resultTarget"], "origin"))
    assert corrupt["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"


def test_malformed_retained_intent_is_unavailable(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    origin = _apply(reader, _ordinary("malformed", target, project, batches[0]))
    ledger_path = tmp_path / "command-replays.json"
    rows = json.loads(ledger_path.read_text())
    rows["malformed"]["request"]["payload"]["batch"]["contentIdentity"] = "sha256:" + "0" * 64
    ledger_path.write_text(json.dumps(rows))
    result = check_command(reader, _inverse("bad-intent", "revertActualCommand", origin["resultTarget"], "malformed"))
    assert result["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"


def test_malformed_history_shapes_reject_check_and_apply_without_writes(tmp_path):
    for case in ("empty-inputs", "non-mapping-payload", "unknown-payload-property", "wrong-command-id"):
        root = tmp_path / case
        root.mkdir()
        reader, target, project, batches = _world(root)
        origin = _apply(reader, _ordinary("origin", target, project, batches[0]))
        ledger_path = root / "command-replays.json"
        rows = json.loads(ledger_path.read_text())
        if case == "empty-inputs":
            rows["origin"]["result"]["inputs"] = []
        else:
            request = rows["origin"]["request"]
            if case == "non-mapping-payload":
                request["payload"] = []
            elif case == "unknown-payload-property":
                request["payload"]["unexpected"] = "not part of the closed operation"
            else:
                request["commandId"] = "a-different-command"
            rows["origin"]["requestIdentity"] = content_identity(request)
            rows["origin"]["result"]["requestContentIdentity"] = content_identity(request)
        ledger_path.write_text(json.dumps(rows))
        inverse = _inverse(f"undo-{case}", "revertActualCommand", origin["resultTarget"], "origin")
        before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        checked = check_command(reader, inverse)
        applied = apply_actual_command(reader, inverse)
        after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        assert checked["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"
        assert applied["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"
        assert after == before


def test_cyclic_redo_revert_ancestry_rejects_check_and_apply_without_writes(tmp_path):
    reader, target, project, batches = _world(tmp_path)
    origin = _apply(reader, _ordinary("origin", target, project, batches[0]))
    undo = _apply(reader, _inverse("undo", "revertActualCommand", origin["resultTarget"], "origin"))
    assert undo["status"] == "accepted"

    ledger_path = tmp_path / "command-replays.json"
    rows = json.loads(ledger_path.read_text())
    origin_request = rows["origin"]["request"]
    origin_request["type"] = "redoActualCommand"
    origin_request["payload"] = {"revertCommandId": "undo"}
    rows["origin"]["requestIdentity"] = content_identity(origin_request)
    rows["origin"]["result"]["requestContentIdentity"] = content_identity(origin_request)
    ledger_path.write_text(json.dumps(rows))

    redo = _inverse("cycle", "redoActualCommand", undo["resultTarget"], "undo")
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    checked = check_command(reader, redo)
    applied = apply_actual_command(reader, redo)
    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert checked["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"
    assert applied["diagnostics"][0]["code"] == "E_COMMAND_HISTORY_UNAVAILABLE"
    assert after == before
