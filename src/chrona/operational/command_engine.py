"""M26 revision-bound command validation and machine result construction."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any
import yaml

from chrona.commands.actual_commands import LocalActualStore, apply_actual_intake_batch, resolve_actual_observation
from chrona.operational.references import ImmutableReader, verify_reference
from chrona.operational.references import ReplayLedger
from chrona.operational.resources import content_identity


SUPPORTED = {"applyActualIntakeBatch", "resolveActualObservation", "captureSnapshot"}


def check_command(reader: ImmutableReader, command: dict[str, Any]) -> dict[str, Any]:
    """Validate a v0.2 operational command without writing a Store."""
    request_identity = content_identity(command)
    target = command.get("target", {})
    base = command.get("baseRevision")
    expected = command.get("expectedContentIdentity")
    try:
        verified = verify_reference(reader, target)
        if base != target.get("revision", {}).get("token") or expected != target.get("contentIdentity"):
            raise ValueError("E_AUTOMATION_BASE_REVISION")
        if command.get("type") not in SUPPORTED:
            raise ValueError("E_AUTOMATION_OPERATION_UNSUPPORTED")
        for name in ("batch", "project"):
            reference = command.get("payload", {}).get(name)
            if reference is not None:
                verify_reference(reader, reference)
    except ValueError as error:
        code = str(error)
        return {"version": "chrona/automation-result/v0.1", "operation": "command-check", "status": "rejected", "requestContentIdentity": request_identity, "inputs": [target] if target else [], "diagnostics": [{"code": code}], "artifacts": []}
    return {"version": "chrona/automation-result/v0.1", "operation": "command-check", "status": "accepted", "requestContentIdentity": request_identity, "inputs": [verified.reference], "diagnostics": [], "artifacts": []}


def apply_actual_command(reader: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Apply one supported Actual command through its declared local CAS Store."""
    checked = check_command(reader, command)
    if checked["status"] != "accepted":
        checked["operation"] = "command-apply"
        return checked
    target = command["target"]
    store_info = target["store"]
    root = reader.roots.get((store_info["provider"], store_info["identity"]))
    tip = root / "actual-tips" / f"{target['id']}.json" if root else None
    if tip is None or not tip.is_file():
        return _rejected(command, "E_AUTOMATION_TARGET_CLOSURE")
    ledger = ReplayLedger(root / "command-replays.json")
    try:
        replay = ledger.lookup(command["commandId"], command, target)
    except ValueError as error:
        return _rejected(command, str(error))
    if replay:
        return replay.result | {"replayed": True}
    actual = verify_reference(reader, target).value
    store = LocalActualStore(root, actual)
    if store.read()[0] != target["revision"]["token"]:
        return _rejected(command, "E_AUTOMATION_TARGET_CLOSURE")
    payload = command.get("payload", {})
    if command["type"] == "applyActualIntakeBatch":
        batch = verify_reference(reader, payload["batch"], kind="actual-intake-batch").value
        project = verify_reference(reader, payload["project"], kind="project").value
        operation = apply_actual_intake_batch(store, command["baseRevision"], batch["body"], set(project.get("objects", {})), command["commandId"])
        extra = {"actualIntake": {"dispositions": list(operation.dispositions)}}
    elif command["type"] == "resolveActualObservation":
        project = verify_reference(reader, payload["project"], kind="project").value
        operation = resolve_actual_observation(store, command["baseRevision"], payload["observationId"], payload["projectObjectId"], set(project.get("objects", {})), command["commandId"])
        extra = {}
    else:
        return _rejected(command, "E_AUTOMATION_OPERATION_UNSUPPORTED")
    if operation.status != "accepted":
        return _rejected(command, operation.diagnostics, extra)
    result_target = _actual_reference(target, operation.result_revision, operation.actual_set)
    result = {"version": "chrona/automation-result/v0.1", "operation": "command-apply", "status": "accepted", "requestContentIdentity": content_identity(command), "inputs": [target], "resultTarget": result_target, "diagnostics": [], "artifacts": [], **extra}
    ledger.record(command["commandId"], command, target, result)
    return result


def _actual_reference(target: dict[str, Any], revision: str, actual: dict[str, Any]) -> dict[str, Any]:
    digest = sha256(yaml.safe_dump(actual, sort_keys=True).encode()).hexdigest()
    return target | {"revision": {"token": revision}, "contentIdentity": f"sha256:{digest}"}


def _rejected(command: dict[str, Any], code: str | tuple[str, ...], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    codes = (code,) if isinstance(code, str) else code
    return {"version": "chrona/automation-result/v0.1", "operation": "command-apply", "status": "rejected", "requestContentIdentity": content_identity(command), "inputs": [command.get("target", {})], "diagnostics": [{"code": value} for value in codes], "artifacts": [], **(extra or {})}
