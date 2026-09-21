"""M26 revision-bound command validation and machine result construction."""
from __future__ import annotations

from typing import Any

from chrona.operational.references import ImmutableReader, verify_reference
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
