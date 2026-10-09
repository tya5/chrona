"""Named immutable baseline publication over Revision Store snapshots."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
import yaml

from chrona.core.store_address import StoreAddressError, check_store_segment, resolve_store_address
from chrona.storage.revision_store import ProjectSnapshot
from chrona.storage.publication import publish_exclusive


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
            "version": "chrona/snapshot-ref/v0.1",
            "kind": "snapshot-ref",
            "id": snapshot_id,
            "body": {"project": deepcopy(project_ref)},
        }
        self._resources[snapshot_id] = deepcopy(resource)
        return deepcopy(resource)

    def read(self, snapshot_id: str) -> dict[str, Any] | None:
        value = self._resources.get(snapshot_id)
        return deepcopy(value) if value else None


# A published baseline is always v0.3 (strict `storeAddress`, #710). v0.2 is never written any more (#731), but it
# stays readable and parseable for good: an immutable v0.2 baseline already in a Store (the committed
# `examples/halcyon-1/snapshots/baseline-2027-06.yaml`, whose bytes a Context pins) can never be rewritten.
SNAPSHOT_REF_VERSION = "chrona/snapshot-ref/v0.3"


def snapshot_ref_resource(snapshot_id: str, project_ref: dict[str, Any]) -> dict[str, Any]:
    """The named baseline resource, at the current snapshot-ref version."""
    return {"version": SNAPSHOT_REF_VERSION, "kind": "snapshot-ref", "id": snapshot_id, "body": {"project": deepcopy(project_ref)}}


class LocalBaselineRegistry:
    """Append-only local registry: publishes v0.3 baseline resources and reads stored v0.2 and v0.3 ones."""

    def __init__(self, root: Path, identity: str, *, require_content_identity: bool = True):
        self.root = root
        self.identity = identity
        self.require_content_identity = require_content_identity

    def publish(self, snapshot_id: str, project_ref: dict[str, Any]) -> dict[str, Any] | None:
        try:
            check_store_segment(snapshot_id)
            target = resolve_store_address(self.root, f"snapshots/{snapshot_id}.yaml")
        except StoreAddressError:
            return None
        resource = snapshot_ref_resource(snapshot_id, project_ref)
        payload = yaml.safe_dump(resource, sort_keys=True).encode("utf-8")
        digest = sha256(payload).hexdigest()
        try:
            publish_exclusive(target, payload)
        except FileExistsError:
            return None
        return {"id": snapshot_id, "kind": "snapshot-ref", "store": {"provider": "local", "identity": self.identity}, "address": f"snapshots/{snapshot_id}.yaml", "revision": {"token": f"baseline:{digest}"}, "contentIdentity": f"sha256:{digest}"}

    def read(self, reference: dict[str, Any]) -> bytes:
        store = reference.get("store", {})
        address = reference.get("address", "")
        if store != {"provider": "local", "identity": self.identity} or not isinstance(address, str) or not address.startswith("snapshots/"):
            raise ValueError(f"E_BASELINE_REFERENCE: a baseline reference needs store local/{self.identity} and an address under "
                             f"snapshots/; got store={store} address={address!r}")
        try:
            path = resolve_store_address(self.root, address)
        except StoreAddressError as error:
            raise ValueError(f"E_BASELINE_REFERENCE: baseline address {address!r} is not a safe Store address") from error
        if not path.is_file():
            raise ValueError(f"E_BASELINE_REFERENCE: no baseline file at {address!r} in the Store")
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise ValueError(f"E_BASELINE_REFERENCE: baseline file {address!r} could not be read") from error
        digest = sha256(payload).hexdigest()
        expected_identity = reference.get("contentIdentity")
        if expected_identity is None and self.require_content_identity:
            raise ValueError(f"E_CONTENT_IDENTITY_REQUIRED: the baseline reference {address!r} has no contentIdentity and this Store requires one")
        if expected_identity is not None and expected_identity != f"sha256:{digest}":
            raise ValueError(f"E_BASELINE_REFERENCE: baseline {address!r} has contentIdentity {expected_identity}, the stored bytes are sha256:{digest}")
        if reference.get("revision", {}).get("token") != f"baseline:{digest}":
            raise ValueError(f"E_BASELINE_REFERENCE: baseline {address!r} has revision token {reference.get('revision', {}).get('token')!r}, "
                             f"expected baseline:{digest}")
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
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_STORE_REFERENCE: snapshot {snapshot_id!r} needs a project reference; "
             f"got reference id {target_reference.get('id')!r} with kind {target_reference.get('kind')!r}",),
        )
    snapshot: ProjectSnapshot = project_store.read()
    if snapshot.revision != base_revision:
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_CONFLICT: snapshot {snapshot_id!r} expected base revision {base_revision!r}, "
             f"current project revision is {snapshot.revision!r}",),
        )
    revision = target_reference.get("revision", {}).get("token")
    expected_identity = target_reference.get("contentIdentity")
    if revision != snapshot.revision or (expected_identity is not None and expected_identity != snapshot.content_identity):
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_CONTENT_IDENTITY: snapshot {snapshot_id!r} reference {target_reference.get('id')!r} "
             f"has revision {revision!r} (current {snapshot.revision!r}) and identity {expected_identity!r} "
             f"(current {snapshot.content_identity!r})",),
        )
    project_id = snapshot.project.get("project", {}).get("id")
    if target_reference.get("id") != project_id or not target_reference.get("address") or not target_reference.get("store"):
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_STORE_REFERENCE: snapshot {snapshot_id!r} reference {target_reference.get('id')!r} "
             f"must name current project {project_id!r} and include address/store "
             f"(address present={bool(target_reference.get('address'))}, store present={bool(target_reference.get('store'))})",),
        )
    verified_reference = deepcopy(target_reference) | {"contentIdentity": snapshot.content_identity}
    resource = snapshot_store.publish(snapshot_id, verified_reference)
    if resource is None:
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_SNAPSHOT_EXISTS: snapshot {snapshot_id!r} already has a published immutable resource "
             f"for project reference {target_reference.get('id')!r}",),
        )
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
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_CONFLICT: baseline {snapshot_id!r} expected base revision {base_revision!r}, "
             f"current project revision is {snapshot.revision!r}",),
        )
    expected_identity = target_reference.get("contentIdentity")
    revision = target_reference.get("revision", {}).get("token")
    project_id = snapshot.project.get("project", {}).get("id")
    if (target_reference.get("kind") != "project" or revision != snapshot.revision
            or (expected_identity is not None and expected_identity != snapshot.content_identity)
            or target_reference.get("id") != project_id):
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_BASELINE_REFERENCE: baseline {snapshot_id!r} needs project reference {project_id!r} "
             f"at revision {snapshot.revision!r} with identity {snapshot.content_identity!r}; "
             f"got reference {target_reference.get('id')!r}, kind {target_reference.get('kind')!r}, "
             f"revision {revision!r}, identity {expected_identity!r}",),
        )
    verified_reference = deepcopy(target_reference) | {"contentIdentity": snapshot.content_identity}
    reference = registry.publish(snapshot_id, verified_reference)
    if reference is None:
        try:
            check_store_segment(snapshot_id)
        except StoreAddressError:
            reason = f"baseline id {snapshot_id!r} is not one safe Store segment"
        else:
            reason = (f"baseline id {snapshot_id!r} already exists or could not be atomically published "
                      f"at snapshots/{snapshot_id}.yaml")
        return SnapshotCaptureResult(
            "rejected", None,
            (f"E_BASELINE_EXISTS: {reason} for project reference {target_reference.get('id')!r}",),
        )
    return SnapshotCaptureResult("accepted", reference, ())
