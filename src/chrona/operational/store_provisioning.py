"""Provision a workspace-local Store and seed it with immutable resources (#1892 row 2, the Store route).

A Store root is laid out as ADR-0027 and ``revision_store.LocalSnapshotReader`` read it: a resource is the file
``<root>/revision-<token>/<address>`` and its reference is ``{id, kind, store, address, revision.token, contentIdentity}``.
An Actual Set also has the adapter-private tip ``actual-tips/<id>.json`` that ``LocalActualStore`` creates; commands never
create a missing tip, so provisioning does, once, through that same class. Nothing here edits a resource that exists:
a Project or a batch is content-addressed (the same bytes are the same revision), an Actual Set changes only by command.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.core.diagnostics import Diagnostic
from chrona.core.store_address import StoreAddressError, check_store_segment
from chrona.operational.workspace_initialization import publish_new_file
from chrona.resources import safe_load, schema_validator
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.storage.store_lock import store_write_lock

CONFIG_PATH = ".chrona/store.yaml"
DEFAULT_IDENTITY = "workspace"
RESOURCE_KINDS = ("project", "actual-set", "actual-intake-batch")
_ADDRESS_DIRECTORY = {"project": "projects", "actual-intake-batch": "batches", "actual-set": "actuals"}


REJECTED_CODES = frozenset({"E_STORE_RESOURCE_INVALID", "E_STORE_SELECTION"})
"""Codes the caller causes by its input (a rejected result); the others are conflicts with what the workspace holds."""


class StoreProvisioningError(Exception):
    """A refusal with its stable code and the argument pointer it concerns."""

    def __init__(self, code: str, detail: str, pointer: str = "/") -> None:
        super().__init__(detail)
        self.code, self.detail, self.pointer = code, detail, pointer


@dataclass(frozen=True)
class CreatedStore:
    config: Path
    identity: str
    replayed: bool


@dataclass(frozen=True)
class PublishedResource:
    reference: dict[str, Any]
    replayed: bool


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _real_directory(path: Path, what: str) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise StoreProvisioningError("E_STORE_DIRECTORY", f"{what} is a symlink or not a directory; remove or rename it first")
    path.mkdir(exist_ok=True)


def create_local_store(workspace: Path, identity: str) -> CreatedStore:
    """Write ``.chrona/store.yaml`` (one local Store, root ``.chrona/store``, integrity required) and create the root."""
    config = workspace / CONFIG_PATH
    _real_directory(config.parent, ".chrona")
    document = {"version": "chrona/store-config/v0.1",
                "stores": [{"provider": "local", "identity": identity, "root": "store", "integrity": "required"}]}
    payload = yaml.safe_dump(document, sort_keys=False).encode("utf-8")
    replayed = False
    try:
        publish_new_file(config, payload)
    except FileExistsError:
        if config.is_symlink() or not config.is_file() or config.read_bytes() != payload:
            raise StoreProvisioningError(
                "E_STORE_CONFIG_EXISTS", f"{CONFIG_PATH} already exists with other content; use it as it is "
                "(publish_resource) or choose another storeConfig path in a Store tool") from None
        replayed = True
    _real_directory(config.parent / "store", ".chrona/store")
    return CreatedStore(config, identity, replayed)


def _reference(identity: str, kind: str, resource_id: str, address: str, token: str, payload: bytes) -> dict[str, Any]:
    return {"id": resource_id, "kind": kind, "store": {"provider": "local", "identity": identity}, "address": address,
            "revision": {"token": token}, "contentIdentity": _sha(payload)}


def select_store(roots: dict[tuple[str, str], Path], identity: str | None) -> tuple[str, Path]:
    """The one local Store a resource goes to: the named one, or the only one the configuration declares."""
    stores = {name: root for (provider, name), root in roots.items() if provider == "local"}
    if identity is not None:
        if identity not in stores:
            raise StoreProvisioningError("E_STORE_SELECTION", f"the Store configuration declares no local Store {identity!r}; "
                                         f"it declares {', '.join(sorted(stores)) or 'none'}", "/store")
        return identity, stores[identity]
    if len(stores) != 1:
        raise StoreProvisioningError("E_STORE_SELECTION", "the Store configuration declares "
                                     f"{'no' if not stores else len(stores)} local Stores; name one with 'store'", "/store")
    name, root = next(iter(stores.items()))
    return name, root


def publish_store_resource(root: Path, identity: str, kind: str, resource_id: str, document: dict[str, Any],
                           payload: bytes) -> PublishedResource:
    """Seed one validated resource into the Store at ``root`` and return its reference, or replay an identical one."""
    try:
        check_store_segment(resource_id)
    except StoreAddressError:
        raise StoreProvisioningError("E_STORE_RESOURCE_INVALID", f"the {kind} id {resource_id!r} is not one safe Store "
                                     "segment (letters, digits, '.', '_' and '-')", "/") from None
    root.mkdir(parents=True, exist_ok=True)
    address = f"{_ADDRESS_DIRECTORY[kind]}/{resource_id}.yaml"
    with store_write_lock(root):
        if kind == "actual-set":
            return _publish_actual_set(root, identity, resource_id, document, address)
        token = f"{kind}:{hashlib.sha256(payload).hexdigest()[:16]}"
        path = snapshot_directory(root, token) / address
        reference = _reference(identity, kind, resource_id, address, token, payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            publish_new_file(path, payload)
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                raise StoreProvisioningError("E_STORE_RESOURCE_EXISTS", f"{address} at revision {token} holds other content; "
                                             "a Store revision is never overwritten") from None
            return PublishedResource(reference, True)
        return PublishedResource(reference, False)


def _publish_actual_set(root: Path, identity: str, resource_id: str, document: dict[str, Any], address: str) -> PublishedResource:
    payload = yaml.safe_dump(document, sort_keys=True).encode()
    try:
        tip = root / "actual-tips" / f"{resource_id}.json"
        existed = tip.is_file()
        token, _ = LocalActualStore(root, document).read()
    except ValueError as error:
        raise StoreProvisioningError("E_STORE_RESOURCE_INVALID", str(error).partition(": ")[2] or str(error)) from None
    stored = (snapshot_directory(root, token) / address).read_bytes()
    if existed and safe_load(stored) != safe_load(payload):
        raise StoreProvisioningError(
            "E_STORE_RESOURCE_EXISTS", f"the Actual Set {resource_id!r} is already in the Store at revision {token} with other "
            "content; an Actual Set changes only through commands (applyActualIntakeBatch, resolveActualObservation, "
            "revertActualCommand)")
    return PublishedResource(_reference(identity, "actual-set", resource_id, address, token, stored), existed)


def document_bytes(document: dict[str, Any]) -> bytes:
    """The bytes an inline document is stored as (the same dump ``create_project`` writes)."""
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")


def batch_diagnostics(document: dict[str, Any]) -> tuple[Diagnostic, ...]:
    """The schema findings of an Actual Intake Batch as ``E_SCHEMA`` diagnostics; empty means valid."""
    errors = sorted(schema_validator("actual-intake-batch-v0.2.schema.yaml").iter_errors(document),
                    key=lambda item: [str(part) for part in item.absolute_path])
    return tuple(Diagnostic("E_SCHEMA", item.message, "/" + "/".join(
        str(part).replace("~", "~0").replace("/", "~1") for part in item.absolute_path)) for item in errors)


def read_source(path: Path) -> tuple[Any, bytes]:
    """A resource file's decoded document and its bytes."""
    payload = path.read_bytes()
    return safe_load(payload), payload

