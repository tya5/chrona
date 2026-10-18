"""Immutable-reference verification and durable command replay records."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any, Protocol
import yaml

from chrona.operational.resources import canonical_bytes, content_identity, json_value
from chrona.resources import safe_load
from chrona.storage.store_lock import store_write_lock


class ImmutableReader(Protocol):
    def read(self, reference: dict[str, Any]) -> bytes: ...


def _reason(error: Exception) -> str:
    """What an inner failure says, without repeating its leading diagnostic code."""
    detail = getattr(error, "detail", "") or str(error)
    return re.sub(r"^[EW]_[A-Z0-9_]+:?\s*", "", detail) or getattr(error, "diagnostic_id", "") or detail


@dataclass(frozen=True)
class VerifiedReference:
    reference: dict[str, Any]
    value: dict[str, Any]


def verify_reference(reader: ImmutableReader, reference: dict[str, Any], *, kind: str | None = None) -> VerifiedReference:
    """Verify one complete immutable reference without consulting a mutable tip."""
    required = {"id", "kind", "store", "address", "revision"}
    if not isinstance(reference, dict):
        raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: a reference must be a mapping, got {type(reference).__name__}")
    missing = sorted(required - set(reference))
    if missing or not reference.get("revision", {}).get("token"):
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE: the reference "
                         + (f"is missing {', '.join(missing)}" if missing else "has no revision.token"))
    name = f"{reference.get('kind')} {reference.get('id')!r}"
    if kind and reference.get("kind") != kind:
        raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: expected a {kind} reference, got {name}")
    try:
        payload = reader.read(reference)
        value = json_value(safe_load(payload))
    except (OSError, KeyError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: {name} cannot be read: {_reason(error)}") from error
    if not isinstance(value, dict):
        raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: {name} is not a mapping document")
    computed_identity = f"sha256:{sha256(payload).hexdigest()}"
    if reference.get("contentIdentity") is not None and computed_identity != reference["contentIdentity"]:
        raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: {name} has contentIdentity {reference['contentIdentity']}, "
                         f"the stored bytes are {computed_identity}")
    actual_kind = "project" if reference["kind"] == "project" else value.get("kind")
    actual_id = value.get("project", {}).get("id") if reference["kind"] == "project" else value.get("id")
    if actual_kind != reference["kind"] or actual_id != reference["id"]:
        raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: the reference names {name}, the stored document is "
                         f"{actual_kind} {actual_id!r}")
    return VerifiedReference(dict(reference) | {"contentIdentity": reference.get("contentIdentity", computed_identity)}, value)


@dataclass(frozen=True)
class ReplayRecord:
    command_id: str
    request_identity: str
    target_identity: str
    result: dict[str, Any]
    request: dict[str, Any] | None = None


class ReplayLedger:
    """Store-owned, durable command-ID ledger with collision detection."""

    def __init__(self, path: Path):
        self.path = path

    def lookup(self, command_id: str, request: dict[str, Any], target: dict[str, Any]) -> ReplayRecord | None:
        entries = self._entries()
        entry = entries.get(command_id)
        if entry is None:
            return None
        request_identity = content_identity(request)
        target_identity = content_identity(target)
        if entry["requestIdentity"] != request_identity or entry["targetIdentity"] != target_identity:
            raise ValueError(f"E_COMMAND_ID_REUSE: command id {command_id!r} was already used for a different request or target")
        request_value = entry.get("request")
        return ReplayRecord(command_id, request_identity, target_identity, dict(entry["result"]),
                            dict(request_value) if isinstance(request_value, dict) else None)

    def history(self, command_id: str) -> ReplayRecord | None:
        """Return a stored execution row, checking optional retained intent integrity.

        Pre-H1 records have no ``request`` and remain useful for reference-based
        history operations. A malformed row or mismatched retained request is
        not safe history authority.
        """
        try:
            entries = self._entries()
            entry = entries.get(command_id)
            if entry is None:
                return None
            if (not isinstance(entry, dict)
                    or not isinstance(entry.get("requestIdentity"), str)
                    or not isinstance(entry.get("targetIdentity"), str)
                    or not isinstance(entry.get("result"), dict)):
                raise ValueError("ledger row is incomplete")
            has_request = "request" in entry
            request = entry.get("request")
            if has_request:
                if not isinstance(request, dict) or content_identity(request) != entry["requestIdentity"]:
                    raise ValueError("retained canonical request does not match requestIdentity")
            return ReplayRecord(command_id, entry["requestIdentity"], entry["targetIdentity"],
                                dict(entry["result"]), dict(request) if isinstance(request, dict) else None)
        except (OSError, TypeError, ValueError, KeyError) as error:
            raise ValueError(f"E_COMMAND_HISTORY_UNAVAILABLE: stored history for command {command_id!r} is corrupt") from error

    def record(self, command_id: str, request: dict[str, Any], target: dict[str, Any], result: dict[str, Any]) -> ReplayRecord:
        with store_write_lock(self.path.parent):
            return self._record(command_id, request, target, result)

    def _record(self, command_id: str, request: dict[str, Any], target: dict[str, Any], result: dict[str, Any]) -> ReplayRecord:
        existing = self.lookup(command_id, request, target)
        if existing is not None:
            return existing
        entries = self._entries()
        request_identity = content_identity(request)
        target_identity = content_identity(target)
        retained_request = json_value(request)
        entries[command_id] = {"requestIdentity": request_identity, "targetIdentity": target_identity,
                               "result": result, "request": retained_request}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_bytes(canonical_bytes(entries))
        temporary.replace(self.path)
        return ReplayRecord(command_id, request_identity, target_identity, dict(result), dict(retained_request))

    def _entries(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"E_COMMAND_ID_REUSE: the replay ledger {self.path} is not a mapping")
        return value
