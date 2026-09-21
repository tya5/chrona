"""Named immutable baseline publication over Revision Store snapshots."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Protocol
import yaml

from chrona.storage.revision_store import ProjectSnapshot


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


class LocalBaselineRegistry:
    """Append-only local registry for immutable v0.2 baseline resources."""

    def __init__(self, root: Path, identity: str, *, require_content_identity: bool = False):
        self.root = root
        self.identity = identity
        self.require_content_identity = require_content_identity

    def publish(self, snapshot_id: str, project_ref: dict[str, Any]) -> dict[str, Any] | None:
        if not snapshot_id or "/" in snapshot_id or snapshot_id in {".", ".."}:
            return None
        resource = {"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": snapshot_id, "body": {"project": deepcopy(project_ref)}}
        payload = yaml.safe_dump(resource, sort_keys=True).encode("utf-8")
        digest = sha256(payload).hexdigest()
        target = self.root / "snapshots" / f"{snapshot_id}.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(payload)
            os.link(temporary, target)
        except FileExistsError:
            return None
        finally:
            temporary.unlink(missing_ok=True)
        return {"id": snapshot_id, "kind": "snapshot-ref", "store": {"provider": "local", "identity": self.identity}, "address": f"snapshots/{snapshot_id}.yaml", "revision": {"token": f"baseline:{digest}"}, "contentIdentity": f"sha256:{digest}"}

    def read(self, reference: dict[str, Any]) -> bytes:
        store = reference.get("store", {})
        address = reference.get("address", "")
        if store != {"provider": "local", "identity": self.identity} or not address.startswith("snapshots/") or ".." in address.split("/"):
            raise ValueError("E_BASELINE_REFERENCE")
        path = self.root / address
        if not path.is_file():
            raise ValueError("E_BASELINE_REFERENCE")
        payload = path.read_bytes()
        digest = sha256(payload).hexdigest()
        expected_identity = reference.get("contentIdentity")
        if expected_identity is None and self.require_content_identity:
            raise ValueError("E_CONTENT_IDENTITY_REQUIRED")
        if (expected_identity is not None and expected_identity != f"sha256:{digest}") or reference.get("revision", {}).get("token") != f"baseline:{digest}":
            raise ValueError("E_BASELINE_REFERENCE")
        return payload


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
    expected_identity = target_reference.get("contentIdentity")
    if revision != snapshot.revision or (expected_identity is not None and expected_identity != snapshot.content_identity):
        return SnapshotCaptureResult("rejected", None, ("E_CONTENT_IDENTITY",))
    project_id = snapshot.project.get("project", {}).get("id")
    if target_reference.get("id") != project_id or not target_reference.get("address") or not target_reference.get("store"):
        return SnapshotCaptureResult("rejected", None, ("E_STORE_REFERENCE",))
    verified_reference = deepcopy(target_reference) | {"contentIdentity": snapshot.content_identity}
    resource = snapshot_store.publish(snapshot_id, verified_reference)
    if resource is None:
        return SnapshotCaptureResult("rejected", None, ("E_SNAPSHOT_EXISTS",))
    return SnapshotCaptureResult("accepted", resource, ())


def capture_baseline_v02(
    project_store: RevisionStore,
    base_revision: str,
    target_reference: dict[str, Any],
    snapshot_id: str,
    registry: LocalBaselineRegistry,
) -> SnapshotCaptureResult:
    """Capture one exact Project reference in an append-only v0.2 registry."""
    snapshot: ProjectSnapshot = project_store.read()
    if snapshot.revision != base_revision:
        return SnapshotCaptureResult("rejected", None, ("E_CONFLICT",))
    expected_identity = target_reference.get("contentIdentity")
    if target_reference.get("kind") != "project" or target_reference.get("revision", {}).get("token") != snapshot.revision or (expected_identity is not None and expected_identity != snapshot.content_identity) or target_reference.get("id") != snapshot.project.get("project", {}).get("id"):
        return SnapshotCaptureResult("rejected", None, ("E_BASELINE_REFERENCE",))
    verified_reference = deepcopy(target_reference) | {"contentIdentity": snapshot.content_identity}
    reference = registry.publish(snapshot_id, verified_reference)
    if reference is None:
        return SnapshotCaptureResult("rejected", None, ("E_BASELINE_EXISTS",))
    return SnapshotCaptureResult("accepted", reference, ())
