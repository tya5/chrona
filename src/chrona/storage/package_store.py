"""The packaged store: read-only resources shipped in the `chrona.resources` package (#1342).

A Render Context may reference a shared design held here (`store: {provider: package, identity: chrona.resources}`) from
every render path. The address is a safe relative address under the package; a `contentIdentity` is optional, so editing a
packaged design never needs a Context edit, and a given one is verified against the packaged bytes.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
from typing import Any

from chrona.core.ports import SnapshotReadError
from chrona.core.store_address import StoreAddressError, check_store_address

PACKAGE_PROVIDER = "package"
PACKAGE_IDENTITY = "chrona.resources"


def is_package_reference(reference: Any) -> bool:
    store = reference.get("store") if isinstance(reference, dict) else None
    return isinstance(store, dict) and store.get("provider") == PACKAGE_PROVIDER


def read_package_reference(reference: dict[str, Any]) -> bytes:
    """The exact bytes of the packaged resource ``reference`` names, verified against a stated ``contentIdentity``."""
    store, address = reference.get("store", {}), reference.get("address")
    if store.get("identity") != PACKAGE_IDENTITY:
        raise SnapshotReadError("E_STORE_REFERENCE", f"a package reference requires store identity {PACKAGE_IDENTITY}; received {store.get('identity')!r}")
    try:
        segments = check_store_address(address)
    except StoreAddressError as error:
        raise SnapshotReadError("E_STORE_REFERENCE", f"package address={address!r} is not a safe Store address") from error
    resource = files("chrona.resources").joinpath(*segments)
    if not resource.is_file():
        raise SnapshotReadError("E_STORE_REFERENCE", f"package address={address!r}; found no packaged resource")
    payload = resource.read_bytes()
    expected, actual = reference.get("contentIdentity"), "sha256:" + sha256(payload).hexdigest()
    if expected is not None and expected != actual:
        raise SnapshotReadError("E_CONTENT_IDENTITY", f"package address={address!r} has contentIdentity {expected}, the packaged bytes are {actual}")
    return payload
