"""Minimal immutable Project snapshots; local persistence adapters follow this protocol."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from typing import Any
from pathlib import Path

from chrona.core.ports import SnapshotReadError
from chrona.storage.snapshot_paths import snapshot_directory


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
    parents: tuple[str, ...] = ()


class MemoryRevisionStore:
    """Deterministic, immutable reference adapter used until the local adapter exists."""

    def __init__(self, project: dict[str, Any]):
        self._sequence = 0
        self._snapshot = self._make_snapshot(project)
        self._history: dict[str, ProjectSnapshot] = {self._snapshot.revision: self._snapshot}
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []
        self._commands: dict[str, tuple[dict[str, Any], dict[str, Any], bool]] = {}
        self._commands: dict[str, tuple[dict[str, Any], dict[str, Any], bool]] = {}

    def read(self) -> ProjectSnapshot:
        return self._copy(self._snapshot)

    def read_revision(self, revision: str) -> ProjectSnapshot | None:
        snapshot = self._history.get(revision)
        return self._copy(snapshot) if snapshot else None

    def write(self, expected_revision: str, project: dict[str, Any]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._redo.clear()
        self._snapshot = self._make_snapshot(project, (expected_revision,))
        self._history[self._snapshot.revision] = self._snapshot
        return self.read()

    def write_with_parents(self, expected_revision: str, project: dict[str, Any], parents: tuple[str, ...]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision or expected_revision not in parents or any(parent not in self._history for parent in parents):
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._redo.clear()
        self._snapshot = self._make_snapshot(project, parents)
        self._history[self._snapshot.revision] = self._snapshot
        return self.read()

    def record_command(self, command_id: str, base: str, result: str | None, operations: Any) -> None:
        self._commands[command_id] = (deepcopy(self._undo[-1]), deepcopy(self._snapshot.project), False)

    def undo(self, expected_revision: str, command_id: str) -> ProjectSnapshot | None:
        entry = self._commands.get(command_id)
        if expected_revision != self._snapshot.revision or entry is None or entry[2] or self._snapshot.project != entry[1]:
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

    @staticmethod
    def _copy(snapshot: ProjectSnapshot) -> ProjectSnapshot:
        return ProjectSnapshot(snapshot.revision, snapshot.content_identity, deepcopy(snapshot.project), snapshot.parents)

    def _make_snapshot(self, project: dict[str, Any], parents: tuple[str, ...] = ()) -> ProjectSnapshot:
        digest = sha256(_canonical(project)).hexdigest()
        self._sequence += 1
        return ProjectSnapshot(f"memory:{self._sequence}:{digest}", f"sha256:{digest}", deepcopy(project), parents)


class LocalTransactionalStore:
    """Process-local CAS writer whose revisions are immutable local snapshots."""

    def __init__(self, root: Path, identity: str, project: dict[str, Any]):
        self.root, self.identity = root, identity
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []
        self._commands: dict[str, tuple[dict[str, Any], dict[str, Any], bool]] = {}
        self._sequence = 0
        self._tip = root / "tip.json"
        if self._tip.is_file():
            self._snapshot = self._read_tip()
        else:
            self._snapshot = self._persist(project)
        self._history: dict[str, ProjectSnapshot] = {self._snapshot.revision: self._snapshot}

    def read(self) -> ProjectSnapshot:
        return self._copy(self._snapshot)

    def read_revision(self, revision: str) -> ProjectSnapshot | None:
        snapshot = self._history.get(revision)
        return self._copy(snapshot) if snapshot else None

    def write(self, expected_revision: str, project: dict[str, Any]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._redo.clear()
        self._snapshot = self._persist(project, (expected_revision,))
        self._history[self._snapshot.revision] = self._snapshot
        return self.read()

    def write_with_parents(self, expected_revision: str, project: dict[str, Any], parents: tuple[str, ...]) -> ProjectSnapshot | None:
        if expected_revision != self._snapshot.revision or expected_revision not in parents or any(parent not in self._history for parent in parents):
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._redo.clear()
        self._snapshot = self._persist(project, parents)
        self._history[self._snapshot.revision] = self._snapshot
        return self.read()

    def record_command(self, command_id: str, base: str, result: str | None, operations: Any) -> None:
        self._commands[command_id] = (deepcopy(self._undo[-1]), deepcopy(self._snapshot.project), False)

    def undo(self, expected_revision: str, command_id: str) -> ProjectSnapshot | None:
        entry = self._commands.get(command_id)
        if expected_revision != self._snapshot.revision or entry is None or entry[2] or self._snapshot.project != entry[1]:
            return None
        self._redo.append(deepcopy(self._snapshot.project))
        self._snapshot = self._persist(entry[0])
        self._commands[command_id] = (entry[0], entry[1], True)
        return self.read()

    def redo(self, expected_revision: str, command_id: str) -> ProjectSnapshot | None:
        entry = self._commands.get(command_id)
        if expected_revision != self._snapshot.revision or entry is None or not entry[2] or self._snapshot.project != entry[0]:
            return None
        self._undo.append(deepcopy(self._snapshot.project))
        self._snapshot = self._persist(entry[1])
        self._commands[command_id] = (entry[0], entry[1], False)
        return self.read()

    @staticmethod
    def _copy(snapshot: ProjectSnapshot) -> ProjectSnapshot:
        return ProjectSnapshot(snapshot.revision, snapshot.content_identity, deepcopy(snapshot.project), snapshot.parents)

    def _persist(self, project: dict[str, Any], parents: tuple[str, ...] = ()) -> ProjectSnapshot:
        payload = _canonical(project)
        digest = sha256(payload).hexdigest()
        self._sequence += 1
        token = f"local-{self._sequence}-{digest[:12]}"
        path = self.root / token
        path.mkdir(parents=True, exist_ok=False)
        (path / "project.json").write_bytes(payload)
        (path / "parents.json").write_text(json.dumps(list(parents)), encoding="utf-8")
        self._tip.write_text(json.dumps({"token": token}), encoding="utf-8")
        return ProjectSnapshot(f"local:{token}", f"sha256:{digest}", deepcopy(project), parents)

    def _read_tip(self) -> ProjectSnapshot:
        token = json.loads(self._tip.read_text(encoding="utf-8"))["token"]
        payload = (self.root / token / "project.json").read_bytes()
        project = json.loads(payload)
        digest = sha256(payload).hexdigest()
        parents_path = self.root / token / "parents.json"
        parents = tuple(json.loads(parents_path.read_text(encoding="utf-8"))) if parents_path.is_file() else ()
        return ProjectSnapshot(f"local:{token}", f"sha256:{digest}", project, parents)


class LocalSnapshotReader:
    """Read-only reader for pre-materialized immutable local snapshot directories."""

    def __init__(self, root: Path, identity: str, *, require_content_identity: bool = False):
        self.root = root
        self.identity = identity
        self.require_content_identity = require_content_identity

    def read(self, reference: dict[str, Any]) -> bytes:
        store = reference.get("store", {})
        if store.get("provider") != "local" or store.get("identity") != self.identity:
            raise SnapshotReadError("E_STORE_REFERENCE")
        token = reference.get("revision", {}).get("token", "")
        address = reference.get("address", "")
        if (
            not token
            or not address
            or address.startswith("/")
            or "\\" in address
            or ".." in address.split("/")
        ):
            raise SnapshotReadError("E_IMMUTABLE_SNAPSHOT_REQUIRED")
        try:
            path = snapshot_directory(self.root, token) / address
        except ValueError as error:
            raise SnapshotReadError(str(error)) from error
        if not path.is_file():
            raise SnapshotReadError("E_STORE_REFERENCE")
        payload = path.read_bytes()
        actual_identity = f"sha256:{sha256(payload).hexdigest()}"
        expected_identity = reference.get("contentIdentity")
        if expected_identity is None and self.require_content_identity:
            raise SnapshotReadError("E_CONTENT_IDENTITY_REQUIRED")
        if expected_identity is not None and expected_identity != actual_identity:
            raise SnapshotReadError("E_CONTENT_IDENTITY")
        return payload
