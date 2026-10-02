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
from chrona.operational.resources import content_identity, diagnostic_row, stamp_automation_result
from chrona.storage.revision_store import ProjectSnapshot
from chrona.storage.snapshots import LocalBaselineRegistry, capture_baseline_v02


SUPPORTED = {"applyActualIntakeBatch", "resolveActualObservation", "captureSnapshot"}


def check_command(reader: ImmutableReader, command: dict[str, Any]) -> dict[str, Any]:
    """Validate a v0.2 operational command without writing a Store."""
    request_identity = content_identity(command)
    target = command.get("target", {})
    base = command.get("baseRevision")
    expected = command.get("expectedContentIdentity")
    try:
        verified = verify_reference(reader, target)
        current = verified.reference.get("revision", {}).get("token")
        if base != current:
            raise ValueError(f"E_AUTOMATION_BASE_REVISION: baseRevision {base!r} is not the target's revision {current!r}")
        if expected is not None and expected != verified.reference.get("contentIdentity"):
            raise ValueError(f"E_AUTOMATION_BASE_REVISION: expectedContentIdentity {expected} is not the target's "
                             f"{verified.reference.get('contentIdentity')}")
        if command.get("type") not in SUPPORTED:
            raise ValueError(_unsupported(command))
        for name in ("batch", "project"):
            reference = command.get("payload", {}).get(name)
            if reference is not None:
                verify_reference(reader, reference)
    except ValueError as error:
        return stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-check", "status": "rejected", "requestContentIdentity": request_identity, "inputs": [target] if target else [], "diagnostics": [diagnostic_row(str(error))], "artifacts": []})
    return stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-check", "status": "accepted", "requestContentIdentity": request_identity, "inputs": [verified.reference], "diagnostics": [], "artifacts": []})


def apply_actual_command(reader: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Apply one supported Actual command through its declared local CAS Store."""
    checked = check_command(reader, command)
    if checked["status"] != "accepted":
        checked["operation"] = "command-apply"
        return checked
    target = checked["inputs"][0]
    if command["type"] == "captureSnapshot":
        verified = verify_reference(reader, target, kind="project")
        registry_selector = command["payload"]["registry"]
        root = reader.roots.get((registry_selector["provider"], registry_selector["identity"]))
        if root is None:
            return _rejected(command, f"E_AUTOMATION_TARGET_CLOSURE: the Store config declares no Store "
                                      f"{registry_selector['provider']}/{registry_selector['identity']} for the snapshot registry")
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
    root = reader.roots.get((store_info["provider"], store_info["identity"]))
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
    actual = verify_reference(reader, target).value
    store = LocalActualStore(root, actual)
    current_tip = store.read()[0]
    if current_tip != target["revision"]["token"]:
        return _rejected(command, f"E_AUTOMATION_TARGET_CLOSURE: the reference revision {target['revision']['token']!r} "
                                  f"is not the current tip {current_tip!r} of Actual {target['id']!r}")
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
        return _rejected(command, _unsupported(command))
    if operation.status != "accepted":
        return _rejected(command, operation.diagnostics, extra)
    result_target = _actual_reference(target, operation.result_revision, operation.actual_set)
    result = stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "accepted", "requestContentIdentity": content_identity(command), "inputs": [target], "resultTarget": result_target, "diagnostics": [], "artifacts": [], **extra})
    ledger.record(command["commandId"], command, target, result)
    return result


def _actual_reference(target: dict[str, Any], revision: str, actual: dict[str, Any]) -> dict[str, Any]:
    digest = sha256(yaml.safe_dump(actual, sort_keys=True).encode()).hexdigest()
    return target | {"revision": {"token": revision}, "contentIdentity": f"sha256:{digest}"}


def _unsupported(command: dict[str, Any]) -> str:
    return f"E_AUTOMATION_OPERATION_UNSUPPORTED: command type {command.get('type')!r} is not supported; supported types: {', '.join(sorted(SUPPORTED))}"


def _rejected(command: dict[str, Any], code: str | tuple[str, ...], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """A rejected command-apply result; each entry of ``code`` is ``"E_X"`` or ``"E_X: detail"``."""
    codes = (code,) if isinstance(code, str) else code
    return stamp_automation_result({"version": "chrona/automation-result/v0.2", "operation": "command-apply", "status": "rejected", "requestContentIdentity": content_identity(command), "inputs": [command.get("target", {})], "diagnostics": [diagnostic_row(value) for value in codes], "artifacts": [], **(extra or {})})
