"""Minimal immutable Project snapshots; local persistence adapters follow this protocol."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from typing import Any
from pathlib import Path


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=lambda item: item.isoformat() if isinstance(item, date) else TypeError()).encode()


@dataclass(frozen=True)
class ProjectSnapshot:
    revision: str
    content_identity: str
    project: dict[str, Any]


class MemoryRevisionStore:
    """Deterministic, immutable reference adapter used until the local adapter exists."""

    def __init__(self, project: dict[str, Any]):
        self._snapshot = self._make_snapshot(project)

    def read(self) -> ProjectSnapshot:
        return ProjectSnapshot(self._snapshot.revision, self._snapshot.content_identity, deepcopy(self._snapshot.project))

    def write(self, expected_revision: str, project: dict[str, Any]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision:
            return None
        self._snapshot = self._make_snapshot(project)
        return self.read()

    @staticmethod
    def _make_snapshot(project: dict[str, Any]) -> ProjectSnapshot:
        digest = sha256(_canonical(project)).hexdigest()
        return ProjectSnapshot(f"memory:{digest}", f"sha256:{digest}", deepcopy(project))


class SnapshotReadError(ValueError):
    def __init__(self, diagnostic_id: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id


class LocalSnapshotReader:
    """Read-only reader for pre-materialized immutable local snapshot directories."""

    def __init__(self, root: Path, identity: str):
        self.root = root
        self.identity = identity

    def read(self, reference: dict[str, Any]) -> bytes:
        store = reference.get("store", {})
        if store.get("provider") != "local" or store.get("identity") != self.identity:
            raise SnapshotReadError("E_STORE_REFERENCE")
        token = reference.get("revision", {}).get("token", "")
        address = reference.get("address", "")
        if not token or not address or token in {"Draft", "draft"} or "/" in token or ".." in address.split("/"):
            raise SnapshotReadError("E_IMMUTABLE_SNAPSHOT_REQUIRED")
        path = self.root / token / address
        if not path.is_file():
            raise SnapshotReadError("E_STORE_REFERENCE")
        payload = path.read_bytes()
        if reference.get("contentIdentity") != f"sha256:{sha256(payload).hexdigest()}":
            raise SnapshotReadError("E_CONTENT_IDENTITY")
        return payload
