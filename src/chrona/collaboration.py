"""Explicit M12 collaboration boundary; no last-writer-wins."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class CollaborationResult:
    status: str
    diagnostic: str | None = None
    conflict: dict[str, Any] | None = None
    revision: str | None = None


@dataclass(frozen=True)
class AuditRecord:
    command_id: str
    fingerprint: str
    decision: str
    actor: str
    base_revision: str
    result_revision: str | None
    time: str
    diagnostic: str | None


class AuditLog:
    """Append-only collaboration observations, independent from Project state."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)


def fingerprint(command: Any) -> str:
    return "sha256:" + sha256(json.dumps(command, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _audit(audit: AuditLog | None, command: dict[str, Any], decision: str, now: str, diagnostic: str | None, result_revision: str | None = None) -> None:
    if audit is not None:
        audit.append(AuditRecord(command.get("commandId", ""), fingerprint(command.get("payload", {})), decision,
                                 command.get("actor", {}).get("principal", ""), command.get("baseRevision", ""),
                                 result_revision, now, diagnostic))


def _authorization(command: dict[str, Any], decision: dict[str, Any], now: str, audit: AuditLog | None) -> CollaborationResult | None:
    if decision.get("decision") != "allow":
        _audit(audit, command, "deny", now, "E_AUTHORIZATION_DENIED")
        return CollaborationResult("rejected", "E_AUTHORIZATION_DENIED")
    approval = command.get("approval")
    if approval and approval.get("commandFingerprint") != fingerprint(command.get("payload", {})):
        _audit(audit, command, "allow", now, "E_APPROVAL_FINGERPRINT_MISMATCH")
        return CollaborationResult("rejected", "E_APPROVAL_FINGERPRINT_MISMATCH")
    if approval and approval.get("expiresAt", "") <= now:
        _audit(audit, command, "allow", now, "E_APPROVAL_EXPIRED")
        return CollaborationResult("rejected", "E_APPROVAL_EXPIRED")
    return None


def submit(store: Any, command: dict[str, Any], decision: dict[str, Any], now: str, audit: AuditLog | None = None) -> CollaborationResult:
    """Check a submission and record every decision; stale writes materialize a conflict."""
    rejected = _authorization(command, decision, now, audit)
    if rejected:
        return rejected
    snap = store.read()
    if snap.revision != command.get("baseRevision"):
        base = store.read_revision(command.get("baseRevision"))
        conflict = {"id": "conflict:" + command["commandId"], "parents": [command["baseRevision"], snap.revision],
                    "path": "project", "kind": "semantic", "left": base.project if base else None,
                    "right": snap.project, "provenance": {"actor": command["actor"]["principal"]}}
        _audit(audit, command, "allow", now, "E_COMMAND_STALE_BASE_REVISION")
        return CollaborationResult("conflict", "E_COMMAND_STALE_BASE_REVISION", conflict)
    _audit(audit, command, "allow", now, None, snap.revision)
    return CollaborationResult("accepted", revision=snap.revision)


def resolve_merge_conflict(store: Any, conflict: dict[str, Any], command: dict[str, Any], decision: dict[str, Any], now: str, audit: AuditLog | None = None) -> CollaborationResult:
    """Create a CAS-protected resolution revision with both conflict parents."""
    rejected = _authorization(command, decision, now, audit)
    if rejected:
        return rejected
    payload = command.get("payload", {})
    selected = payload.get("selected")
    if command.get("type") != "resolveMergeConflict" or payload.get("conflictId") != conflict.get("id") or selected not in {"left", "right"}:
        _audit(audit, command, "allow", now, "E_CONFLICT_RESOLUTION")
        return CollaborationResult("rejected", "E_CONFLICT_RESOLUTION")
    project = conflict.get(selected)
    if not isinstance(project, dict):
        _audit(audit, command, "allow", now, "E_CONFLICT_RESOLUTION")
        return CollaborationResult("rejected", "E_CONFLICT_RESOLUTION")
    parents = tuple(conflict.get("parents", ()))
    resolved = store.write_with_parents(command.get("baseRevision", ""), project, parents)
    if resolved is None:
        _audit(audit, command, "allow", now, "E_COMMAND_STALE_BASE_REVISION")
        return CollaborationResult("conflict", "E_COMMAND_STALE_BASE_REVISION")
    _audit(audit, command, "allow", now, None, resolved.revision)
    return CollaborationResult("accepted", revision=resolved.revision)


def replica_status(known_revision: str, remote_revision: str) -> CollaborationResult:
    return CollaborationResult("behind", "I_REPLICA_BEHIND") if known_revision != remote_revision else CollaborationResult("current")
