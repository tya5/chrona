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
        return ReplayRecord(command_id, request_identity, target_identity, dict(entry["result"]))

    def record(self, command_id: str, request: dict[str, Any], target: dict[str, Any], result: dict[str, Any]) -> ReplayRecord:
        existing = self.lookup(command_id, request, target)
        if existing is not None:
            return existing
        entries = self._entries()
        request_identity = content_identity(request)
        target_identity = content_identity(target)
        entries[command_id] = {"requestIdentity": request_identity, "targetIdentity": target_identity, "result": result}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_bytes(canonical_bytes(entries))
        temporary.replace(self.path)
        return ReplayRecord(command_id, request_identity, target_identity, dict(result))

    def _entries(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"E_COMMAND_ID_REUSE: the replay ledger {self.path} is not a mapping")
        return value
