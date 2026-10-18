"""M26 revision-bound command validation and machine result construction."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any
import yaml

from chrona.commands.actual_commands import LocalActualStore, apply_actual_intake_batch, resolve_actual_observation
from chrona.core.store_address import StoreAddressError, check_store_segment, resolve_store_address
from chrona.operational.references import ImmutableReader, verify_reference
from chrona.operational.references import ReplayLedger
from chrona.operational.resources import content_identity, diagnostic_row, parse_command, stamp_automation_result
from chrona.storage.revision_store import ProjectSnapshot
from chrona.storage.snapshots import LocalBaselineRegistry, capture_baseline_v02
from chrona.storage.store_lock import StoreLockError, store_write_lock


SUPPORTED = {"applyActualIntakeBatch", "resolveActualObservation", "captureSnapshot",
             "revertActualCommand", "redoActualCommand"}
_ACTUAL_OPERATIONS = {"applyActualIntakeBatch", "resolveActualObservation"}


def check_command(reader: ImmutableReader, command: dict[str, Any], *, validate_history: bool = True) -> dict[str, Any]:
    """Validate a v0.2 operational command without writing a Store."""
    request_identity = content_identity(command)
    target = command.get("target", {})
    base = command.get("baseRevision")
    expected = command.get("expectedContentIdentity")
    try:
        command_type = command.get("type")
        expected_kind = ("project" if command_type == "captureSnapshot" else "actual-set"
                         if command_type in _ACTUAL_OPERATIONS | {"revertActualCommand", "redoActualCommand"}
                         else None)
        verified = verify_reference(reader, target, kind=expected_kind)
        current = verified.reference.get("revision", {}).get("token")
        if base != current:
            raise ValueError(f"E_AUTOMATION_BASE_REVISION: baseRevision {base!r} is not the target's revision {current!r}")
        if expected is not None and expected != verified.reference.get("contentIdentity"):
            raise ValueError(f"E_AUTOMATION_BASE_REVISION: expectedContentIdentity {expected} is not the target's "
                             f"{verified.reference.get('contentIdentity')}")
        if command.get("type") not in SUPPORTED:
            raise ValueError(_unsupported(command))
        for name in (("batch", "project") if command.get("type") in _ACTUAL_OPERATIONS else ()):
            reference = command.get("payload", {}).get(name)
            if reference is not None:
                verify_reference(reader, reference)
        if validate_history and command.get("type") in {"revertActualCommand", "redoActualCommand"}:
            root = reader.roots.get((verified.reference["store"]["provider"], verified.reference["store"]["identity"]))
            if root is None:
                raise ValueError("E_AUTOMATION_TARGET_CLOSURE: the Store config declares no Store for command history")
            _check_inverse_history(reader, command, root, verified.reference)
    except ValueError as error:
        return stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-check", "status": "rejected", "requestContentIdentity": request_identity, "inputs": [target] if target else [], "diagnostics": [diagnostic_row(str(error))], "artifacts": []})
    return stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-check", "status": "accepted", "requestContentIdentity": request_identity, "inputs": [verified.reference], "diagnostics": [], "artifacts": []})


def apply_actual_command(reader: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Apply one supported Actual command through its declared local CAS Store."""
    checked = check_command(reader, command, validate_history=False)
    if checked["status"] != "accepted":
        checked["operation"] = "command-apply"
        return checked
    target = checked["inputs"][0]
    selector = command["payload"]["registry"] if command["type"] == "captureSnapshot" else target["store"]
    root = reader.roots.get((selector["provider"], selector["identity"]))
    if root is None:
        return _rejected(command, f"E_AUTOMATION_TARGET_CLOSURE: the Store config declares no Store "
                                  f"{selector['provider']}/{selector['identity']} for the command destination")
    try:
        with store_write_lock(root):
            return _apply_checked_command(reader, command, target, root)
    except StoreLockError as error:
        return _rejected(command, f"{error.diagnostic_id}: {error.detail}")


def _apply_checked_command(reader: Any, command: dict[str, Any], target: dict[str, Any], root: Path) -> dict[str, Any]:
    """Keep replay, fresh CAS, publication and recording in one Store transaction."""
    if command["type"] == "captureSnapshot":
        verified = verify_reference(reader, target, kind="project")
        registry_selector = command["payload"]["registry"]
        ledger = ReplayLedger(root / "command-replays.json")
        try:
            replay = ledger.lookup(command["commandId"], command, target)
        except ValueError as error:
            return _rejected(command, str(error))
        if replay:
            return replay.result | {"replayed": True}
        class ProjectStore:
            def read(self_nonlocal):
                return ProjectSnapshot(target["revision"]["token"], target["contentIdentity"], verified.value)
        result = capture_baseline_v02(ProjectStore(), command["baseRevision"], target, command["payload"]["snapshotId"], LocalBaselineRegistry(root, registry_selector["identity"]))
        if result.status != "accepted":
            return _rejected(command, result.diagnostics)
        accepted = stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "accepted", "requestContentIdentity": content_identity(command), "inputs": [target], "resultTarget": result.snapshot_ref, "diagnostics": [], "artifacts": []})
        ledger.record(command["commandId"], command, target, accepted)
        return accepted
    store_info = target["store"]
    tip = None
    if root:
        try:
            # Same adapter-private tip file name as `LocalActualStore`: an identifier, not an address (#731).
            tip = resolve_store_address(root, f"actual-tips/{target['id']}.json", charset="file-name")
            check_store_segment(target["id"], charset="file-name")
        except StoreAddressError:
            tip = None
    if tip is None or not tip.is_file():
        return _rejected(command, f"E_AUTOMATION_TARGET_CLOSURE: Store {store_info['provider']}/{store_info['identity']} "
                                  f"is not configured or holds no tip for Actual {target['id']!r}")
    ledger = ReplayLedger(root / "command-replays.json")
    try:
        replay = ledger.lookup(command["commandId"], command, target)
    except ValueError as error:
        return _rejected(command, str(error))
    if replay:
        return replay.result | {"replayed": True}
    actual = verify_reference(reader, target, kind="actual-set").value
    store = LocalActualStore(root, actual)
    current_revision, current = store.read()
    if current_revision != target["revision"]["token"]:
        return _rejected(command, f"E_AUTOMATION_TARGET_CLOSURE: the reference revision {target['revision']['token']!r} "
                                  f"is not the current tip {current_revision!r} of Actual {target['id']!r}")
    if command["type"] == "revertActualCommand":
        return _apply_revert(reader, command, target, root, store, current)
    if command["type"] == "redoActualCommand":
        return _apply_redo(reader, command, target, root, store, current)
    operation, extra = _execute_actual_operation(reader, command, store)
    if operation.status != "accepted":
        return _rejected(command, operation.diagnostics, extra)
    result_target = _actual_reference(target, operation.result_revision, operation.actual_set)
    result = stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "accepted", "requestContentIdentity": content_identity(command), "inputs": [target], "resultTarget": result_target, "diagnostics": [], "artifacts": [], **extra})
    ledger.record(command["commandId"], command, target, result)
    return result


def _execute_actual_operation(reader: Any, command: dict[str, Any], store: LocalActualStore):
    """Run an ordinary semantic operation; redo reuses this validation and mutation path."""
    payload = command.get("payload", {})
    if command["type"] == "applyActualIntakeBatch":
        batch = verify_reference(reader, payload["batch"], kind="actual-intake-batch").value
        project = verify_reference(reader, payload["project"], kind="project").value
        operation = apply_actual_intake_batch(store, command["baseRevision"], batch["body"], set(project.get("objects", {})))
        extra = {"actualIntake": {"dispositions": list(operation.dispositions)}}
    elif command["type"] == "resolveActualObservation":
        project = verify_reference(reader, payload["project"], kind="project").value
        operation = resolve_actual_observation(store, command["baseRevision"], payload["observationId"], payload["projectObjectId"], set(project.get("objects", {})))
        extra = {}
    else:
        raise ValueError(_unsupported(command))
    return operation, extra


def _history_entry(reader: Any, root: Path, command_id: str, target: dict[str, Any], seen: set[str]):
    """Load one accepted history result and prove every stored identity and immutable state."""
    from chrona.operational.references import ReplayLedger

    if command_id in seen:
        raise ValueError("E_COMMAND_HISTORY_UNAVAILABLE: command history contains a cycle")
    seen.add(command_id)
    record = ReplayLedger(root / "command-replays.json").history(command_id)
    if record is None:
        raise ValueError(f"E_COMMAND_HISTORY_UNAVAILABLE: command {command_id!r} is not in the replay ledger")
    result = record.result
    request = record.request
    try:
        inputs = result.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != 1 or not isinstance(inputs[0], dict):
            raise ValueError("history result must contain exactly one mapping input reference")
        before_ref = inputs[0]
        after_ref = result["resultTarget"]
        if not isinstance(after_ref, dict):
            raise ValueError("history resultTarget must be a mapping reference")
        if result.get("status") != "accepted":
            raise ValueError("history result is not accepted")
        if result.get("requestContentIdentity") != record.request_identity:
            raise ValueError("result request identity disagrees with its ledger row")
        if content_identity(before_ref) != record.target_identity:
            raise ValueError("result input identity disagrees with its ledger row")
        if request is not None:
            if content_identity(request) != record.request_identity:
                raise ValueError("stored request hash disagrees with its ledger row")
            request = parse_command(yaml.safe_dump(request))
            if request["commandId"] != command_id:
                raise ValueError("stored request commandId disagrees with its ledger key")
            if request.get("type") not in _ACTUAL_OPERATIONS | {"revertActualCommand", "redoActualCommand"}:
                raise ValueError("E_COMMAND_NOT_REVERSIBLE: this history operation does not mutate an Actual")
            request_target = verify_reference(reader, request.get("target"), kind="actual-set")
            if content_identity(request_target.reference) != record.target_identity:
                raise ValueError("stored request target disagrees with its ledger row")
            if request_target.reference["contentIdentity"] != before_ref.get("contentIdentity"):
                raise ValueError("stored request target disagrees with the result input")
            if request.get("type") == "applyActualIntakeBatch":
                verify_reference(reader, request["payload"]["batch"], kind="actual-intake-batch")
                verify_reference(reader, request["payload"]["project"], kind="project")
            elif request.get("type") == "resolveActualObservation":
                verify_reference(reader, request["payload"]["project"], kind="project")
        if before_ref.get("kind") != "actual-set" or after_ref.get("kind") != "actual-set":
            raise ValueError("E_COMMAND_NOT_REVERSIBLE: only Actual mutations can be reverted or redone")
        before = verify_reference(reader, before_ref, kind="actual-set")
        after = verify_reference(reader, after_ref, kind="actual-set")
        for reference in (before.reference, after.reference, target):
            if reference.get("id") != target.get("id") or reference.get("store") != target.get("store"):
                raise ValueError("history link names a different Store or Actual ID")
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error).startswith(("E_COMMAND_HISTORY_UNAVAILABLE", "E_COMMAND_NOT_REVERSIBLE")):
            raise
        raise ValueError(f"E_COMMAND_HISTORY_UNAVAILABLE: command {command_id!r} has invalid history: {error}") from error
    return {"command_id": command_id, "request": request, "result": result,
            "before": before, "after": after, "record": record}


def _check_inverse_history(reader: Any, command: dict[str, Any], root: Path, target: dict[str, Any]) -> None:
    """Validate replay ancestry for read-only checks; apply repeats it under the Store lock."""
    payload = command.get("payload", {})
    if command["type"] == "revertActualCommand":
        _resolve_revert_origin(reader, root, payload.get("commandId"), target, set())
        return
    _resolve_redo_origin(reader, root, payload.get("revertCommandId"), target, set())


def _resolve_revert_origin(reader: Any, root: Path, command_id: str, target: dict[str, Any], seen: set[str]):
    entry = _history_entry(reader, root, command_id, target, seen)
    request = entry["request"]
    if request is not None and request.get("type") not in _ACTUAL_OPERATIONS | {"redoActualCommand"}:
        raise ValueError("E_COMMAND_NOT_REVERSIBLE: only ordinary Actual mutations or redos can be reverted")
    if entry["before"].reference["contentIdentity"] == entry["after"].reference["contentIdentity"]:
        raise ValueError("E_COMMAND_NOT_REVERSIBLE: the origin did not change Actual content")
    if request is not None and request.get("type") == "redoActualCommand":
        entry["ordinary_origin"] = _ordinary_origin_entry(reader, root, entry, target, seen)
    return entry


def _resolve_redo_origin(reader: Any, root: Path, revert_id: str, target: dict[str, Any], seen: set[str]):
    revert = _history_entry(reader, root, revert_id, target, seen)
    revert_request = revert["request"]
    if not isinstance(revert_request, dict) or revert_request.get("type") != "revertActualCommand":
        raise ValueError("E_COMMAND_NOT_REVERSIBLE: redo target must be an accepted Actual revert")
    if revert["before"].reference["contentIdentity"] == revert["after"].reference["contentIdentity"]:
        raise ValueError("E_COMMAND_NOT_REVERSIBLE: the revert did not change Actual content")
    origin_id = revert_request.get("payload", {}).get("commandId")
    origin = _resolve_revert_origin(reader, root, origin_id, target, seen)
    if (revert["before"].reference["contentIdentity"] != origin["after"].reference["contentIdentity"]
            or revert["after"].reference["contentIdentity"] != origin["before"].reference["contentIdentity"]):
        raise ValueError("E_COMMAND_HISTORY_UNAVAILABLE: revert result does not match its origin boundary")
    if origin["request"] is None:
        raise ValueError("E_COMMAND_HISTORY_UNAVAILABLE: original semantic request is unavailable")
    ordinary = origin.get("ordinary_origin")
    if ordinary is None:
        ordinary = _ordinary_origin_entry(reader, root, origin, target, seen)
    return revert, ordinary


def _ordinary_origin_entry(reader: Any, root: Path, entry: dict[str, Any], target: dict[str, Any], seen: set[str]):
    """Resolve an already verified history entry without loading it twice into cycle detection."""
    request = entry["request"]
    if request is None:
        return entry
    operation = request.get("type")
    if operation in _ACTUAL_OPERATIONS:
        return entry
    if operation == "redoActualCommand":
        revert_id = request.get("payload", {}).get("revertCommandId")
        _, origin = _resolve_redo_origin(reader, root, revert_id, target, seen)
        if entry["before"].reference["contentIdentity"] != origin["before"].reference["contentIdentity"] or entry["after"].reference["contentIdentity"] != origin["after"].reference["contentIdentity"]:
            raise ValueError("E_COMMAND_HISTORY_UNAVAILABLE: redo result does not match its original operation boundary")
        return origin
    raise ValueError("E_COMMAND_HISTORY_UNAVAILABLE: history does not resolve to an ordinary Actual operation")


def _apply_revert(reader: Any, command: dict[str, Any], target: dict[str, Any], root: Path,
                  store: LocalActualStore, current: dict[str, Any]) -> dict[str, Any]:
    from chrona.operational.references import ReplayLedger

    origin_id = command.get("payload", {}).get("commandId")
    try:
        origin = _resolve_revert_origin(reader, root, origin_id, target, set())
        if _actual_content_identity(current) != origin["after"].reference["contentIdentity"]:
            raise ValueError("E_COMMAND_NOT_REVERSIBLE: current Actual content is not the origin's complete post-state")
    except ValueError as error:
        return _rejected(command, str(error))
    persisted = store.write(command["baseRevision"], origin["before"].value)
    if persisted is None:
        return _rejected(command, f"E_AUTOMATION_BASE_REVISION: Actual changed after base revision {command['baseRevision']!r}; compare-and-swap write was not applied")
    revision, actual = persisted
    result_target = _actual_reference(target, revision, actual)
    result = stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "accepted", "requestContentIdentity": content_identity(command), "inputs": [target], "resultTarget": result_target, "diagnostics": [], "artifacts": []})
    ReplayLedger(root / "command-replays.json").record(command["commandId"], command, target, result)
    return result


def _apply_redo(reader: Any, command: dict[str, Any], target: dict[str, Any], root: Path,
                store: LocalActualStore, current: dict[str, Any]) -> dict[str, Any]:
    from chrona.operational.references import ReplayLedger

    revert_id = command.get("payload", {}).get("revertCommandId")
    try:
        revert, origin = _resolve_redo_origin(reader, root, revert_id, target, set())
        if _actual_content_identity(current) != revert["after"].reference["contentIdentity"]:
            raise ValueError("E_COMMAND_NOT_REVERSIBLE: current Actual content is not the revert's complete result state")
        original_request = origin["request"]
        if not isinstance(original_request, dict) or original_request.get("type") not in _ACTUAL_OPERATIONS:
            raise ValueError("E_COMMAND_HISTORY_UNAVAILABLE: original semantic request is unavailable")
        operation_command = dict(original_request)
        operation_command.update({"commandId": command["commandId"], "target": target,
                                  "baseRevision": command["baseRevision"],
                                  "expectedContentIdentity": target.get("contentIdentity")})
        operation, extra = _execute_actual_operation(reader, operation_command, store)
        if operation.status != "accepted":
            return _rejected(command, operation.diagnostics, extra)
        result_target = _actual_reference(target, operation.result_revision, operation.actual_set)
        result = stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "accepted", "requestContentIdentity": content_identity(command), "inputs": [target], "resultTarget": result_target, "diagnostics": [], "artifacts": [], **extra})
        ReplayLedger(root / "command-replays.json").record(command["commandId"], command, target, result)
        return result
    except ValueError as error:
        return _rejected(command, str(error))


def _actual_content_identity(actual: dict[str, Any]) -> str:
    return f"sha256:{sha256(yaml.safe_dump(actual, sort_keys=True).encode()).hexdigest()}"


def _actual_reference(target: dict[str, Any], revision: str, actual: dict[str, Any]) -> dict[str, Any]:
    digest = sha256(yaml.safe_dump(actual, sort_keys=True).encode()).hexdigest()
    return target | {"revision": {"token": revision}, "contentIdentity": f"sha256:{digest}"}


def _unsupported(command: dict[str, Any]) -> str:
    return f"E_AUTOMATION_OPERATION_UNSUPPORTED: command type {command.get('type')!r} is not supported; supported types: {', '.join(sorted(SUPPORTED))}"


def _rejected(command: dict[str, Any], code: str | tuple[str, ...], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """A rejected command-apply result; each entry of ``code`` is ``"E_X"`` or ``"E_X: detail"``."""
    codes = (code,) if isinstance(code, str) else code
    return stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "rejected", "requestContentIdentity": content_identity(command), "inputs": [command.get("target", {})], "diagnostics": [diagnostic_row(value) for value in codes], "artifacts": [], **(extra or {})})
