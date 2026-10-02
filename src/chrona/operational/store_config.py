"""Exact local Store routing for M26 CLI operations."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from chrona.operational.resources import parse_document
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshots import LocalBaselineRegistry


def resolve_store_root(root: str, base: Path | None) -> Path:
    """An absolute `root` as written; a relative one against `base`, the directory of the config file (#781).

    Without a base (a mapping built in code) a relative root keeps meaning "relative to the working directory".
    """
    path = Path(root)
    if base is None or path.is_absolute():
        return path
    return Path(os.path.normpath(base / path))


class ConfiguredStoreReader:
    def __init__(self, config: dict[str, Any], *, base: Path | None = None):
        self.roots: dict[tuple[str, str], Path] = {}
        self.integrity: dict[tuple[str, str], str] = {}
        for entry in config["stores"]:
            key = (entry["provider"], entry["identity"])
            if key in self.roots:
                raise ValueError(f"E_STORE_CONFIG: Store {key[0]}/{key[1]} is declared more than once")
            self.roots[key] = resolve_store_root(entry["root"], base)
            self.integrity[key] = entry.get("integrity", "required")  # required unless the Store explicitly opts out (#723)

    def read(self, reference: dict[str, Any]) -> bytes:
        store = reference.get("store", {})
        key = (store.get("provider"), store.get("identity"))
        root = self.roots.get(key)
        if root is None:
            raise ValueError(f"E_AUTOMATION_TARGET_CLOSURE: the Store config declares no Store {key[0]}/{key[1]}")
        required = self.integrity[key] == "required"
        if required and not reference.get("contentIdentity"):
            raise ValueError(f"E_CONTENT_IDENTITY_REQUIRED: the reference {reference.get('id')!r} has no contentIdentity and Store {key[0]}/{key[1]} requires one")
        token = reference.get("revision", {}).get("token")
        if reference.get("kind") == "snapshot-ref" and isinstance(token, str) and token.startswith("baseline:"):
            return LocalBaselineRegistry(root, key[1], require_content_identity=required).read(reference)
        return LocalSnapshotReader(root, key[1], require_content_identity=required).read(reference)


def load_store_config(path: str) -> ConfiguredStoreReader:
    config_path = Path(path).resolve()  # the same resolution `discover_store_configuration` applies: a relative root is anchored here
    return ConfiguredStoreReader(parse_document(config_path.read_text(encoding="utf-8"), "store-config-v0.1.schema.yaml"), base=config_path.parent)
