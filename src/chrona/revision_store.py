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
    def default(item: Any) -> str:
        if isinstance(item, date):
            return item.isoformat()
        raise TypeError(f"not canonicalizable: {type(item)!r}")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=default).encode()


@dataclass(frozen=True)
class ProjectSnapshot:
    revision: str
    content_identity: str
    project: dict[str, Any]


class MemoryRevisionStore:
    """Deterministic, immutable reference adapter used until the local adapter exists."""

    def __init__(self, project: dict[str, Any]):
        self._sequence = 0
        self._snapshot = self._make_snapshot(project)
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []

    def read(self) -> ProjectSnapshot:
        return ProjectSnapshot(self._snapshot.revision, self._snapshot.content_identity, deepcopy(self._snapshot.project))

    def write(self, expected_revision: str, project: dict[str, Any]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._redo.clear()
        self._snapshot = self._make_snapshot(project)
        return self.read()

    def undo(self, expected_revision: str) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision or not self._undo:
            return None
        self._redo.append(deepcopy(self._snapshot.project))
        self._snapshot = self._make_snapshot(self._undo.pop())
        return self.read()

    def redo(self, expected_revision: str) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision or not self._redo:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._snapshot = self._make_snapshot(self._redo.pop())
        return self.read()

    def _make_snapshot(self, project: dict[str, Any]) -> ProjectSnapshot:
        digest = sha256(_canonical(project)).hexdigest()
        self._sequence += 1
        return ProjectSnapshot(f"memory:{self._sequence}:{digest}", f"sha256:{digest}", deepcopy(project))


class LocalTransactionalStore:
    """Process-local CAS writer whose revisions are immutable local snapshots."""

    def __init__(self, root: Path, identity: str, project: dict[str, Any]):
        self.root, self.identity = root, identity
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []
        self._sequence = 0
        self._tip = root / "tip.json"
        if self._tip.is_file():
            self._snapshot = self._read_tip()
        else:
            self._snapshot = self._persist(project)

    def read(self) -> ProjectSnapshot:
        return ProjectSnapshot(self._snapshot.revision, self._snapshot.content_identity, deepcopy(self._snapshot.project))

    def write(self, expected_revision: str, project: dict[str, Any]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._redo.clear()
        self._snapshot = self._persist(project)
        return self.read()

    def undo(self, expected_revision: str) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision or not self._undo:
            return None
        self._redo.append(deepcopy(self._snapshot.project))
        self._snapshot = self._persist(self._undo.pop())
        return self.read()

    def redo(self, expected_revision: str) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision or not self._redo:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._snapshot = self._persist(self._redo.pop())
        return self.read()

    def _persist(self, project: dict[str, Any]) -> ProjectSnapshot:
        payload = _canonical(project)
        digest = sha256(payload).hexdigest()
        self._sequence += 1
        token = f"local-{self._sequence}-{digest[:12]}"
        path = self.root / token
        path.mkdir(parents=True, exist_ok=False)
        (path / "project.json").write_bytes(payload)
        self._tip.write_text(json.dumps({"token": token}), encoding="utf-8")
        return ProjectSnapshot(f"local:{token}", f"sha256:{digest}", deepcopy(project))

    def _read_tip(self) -> ProjectSnapshot:
        token = json.loads(self._tip.read_text(encoding="utf-8"))["token"]
        payload = (self.root / token / "project.json").read_bytes()
        project = json.loads(payload)
        digest = sha256(payload).hexdigest()
        return ProjectSnapshot(f"local:{token}", f"sha256:{digest}", project)


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
