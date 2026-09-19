"""Named immutable baseline publication over Revision Store snapshots."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from .revision_store import ProjectSnapshot


class RevisionStore(Protocol):
    def read(self) -> ProjectSnapshot: ...


@dataclass(frozen=True)
class SnapshotCaptureResult:
    status: str
    snapshot_ref: dict[str, Any] | None
    diagnostics: tuple[str, ...]


class MemorySnapshotStore:
    """Append-only baseline resource adapter used by the local M7 implementation."""

    def __init__(self, store_identity: str):
        self.store_identity = store_identity
        self._resources: dict[str, dict[str, Any]] = {}

    def publish(self, snapshot_id: str, project_ref: dict[str, Any]) -> dict[str, Any] | None:
        if snapshot_id in self._resources:
            return None
        resource = {
            "version": "chrona/presentation/v0.1",
            "kind": "snapshot-ref",
            "id": snapshot_id,
            "body": {"project": deepcopy(project_ref)},
        }
        self._resources[snapshot_id] = deepcopy(resource)
        return deepcopy(resource)

    def read(self, snapshot_id: str) -> dict[str, Any] | None:
        value = self._resources.get(snapshot_id)
        return deepcopy(value) if value else None


def capture_snapshot(
    project_store: RevisionStore,
    base_revision: str,
    target_reference: dict[str, Any],
    snapshot_id: str,
    snapshot_store: MemorySnapshotStore,
) -> SnapshotCaptureResult:
    """Publish one immutable baseline reference after exact revision verification."""
    if not snapshot_id or target_reference.get("kind") != "project":
        return SnapshotCaptureResult("rejected", None, ("E_STORE_REFERENCE",))
    snapshot: ProjectSnapshot = project_store.read()
    if snapshot.revision != base_revision:
        return SnapshotCaptureResult("rejected", None, ("E_CONFLICT",))
    revision = target_reference.get("revision", {}).get("token")
    if revision != snapshot.revision or target_reference.get("contentIdentity") != snapshot.content_identity:
        return SnapshotCaptureResult("rejected", None, ("E_CONTENT_IDENTITY",))
    project_id = snapshot.project.get("project", {}).get("id")
    if target_reference.get("id") != project_id or not target_reference.get("address") or not target_reference.get("store"):
        return SnapshotCaptureResult("rejected", None, ("E_STORE_REFERENCE",))
    resource = snapshot_store.publish(snapshot_id, target_reference)
    if resource is None:
        return SnapshotCaptureResult("rejected", None, ("E_SNAPSHOT_EXISTS",))
    return SnapshotCaptureResult("accepted", resource, ())
