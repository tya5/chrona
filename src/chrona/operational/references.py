"""Immutable-reference verification and durable command replay records."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Protocol
import yaml

from chrona.operational.resources import canonical_bytes, content_identity, json_value


class ImmutableReader(Protocol):
    def read(self, reference: dict[str, Any]) -> bytes: ...


@dataclass(frozen=True)
class VerifiedReference:
    reference: dict[str, Any]
    value: dict[str, Any]


def verify_reference(reader: ImmutableReader, reference: dict[str, Any], *, kind: str | None = None) -> VerifiedReference:
    """Verify one complete immutable reference without consulting a mutable tip."""
    required = {"id", "kind", "store", "address", "revision", "contentIdentity"}
    if not isinstance(reference, dict) or required - set(reference) or not reference.get("revision", {}).get("token"):
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE")
    if kind and reference.get("kind") != kind:
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE")
    try:
        payload = reader.read(reference)
        value = json_value(yaml.safe_load(payload))
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE") from error
    if not isinstance(value, dict):
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE")
    if f"sha256:{sha256(payload).hexdigest()}" != reference["contentIdentity"]:
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE")
    actual_kind = "project" if reference["kind"] == "project" else value.get("kind")
    actual_id = value.get("project", {}).get("id") if reference["kind"] == "project" else value.get("id")
    if actual_kind != reference["kind"] or actual_id != reference["id"]:
        raise ValueError("E_AUTOMATION_TARGET_CLOSURE")
    return VerifiedReference(dict(reference), value)


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
            raise ValueError("E_COMMAND_ID_REUSE")
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
            raise ValueError("E_COMMAND_ID_REUSE")
        return value
