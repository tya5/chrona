"""Exact local Store routing for M26 CLI operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from chrona.operational.resources import parse_document
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshots import LocalBaselineRegistry


class ConfiguredStoreReader:
    def __init__(self, config: dict[str, Any]):
        self.roots: dict[tuple[str, str], Path] = {}
        for entry in config["stores"]:
            key = (entry["provider"], entry["identity"])
            if key in self.roots:
                raise ValueError("E_STORE_CONFIG")
            self.roots[key] = Path(entry["root"])

    def read(self, reference: dict[str, Any]) -> bytes:
        store = reference.get("store", {})
        key = (store.get("provider"), store.get("identity"))
        root = self.roots.get(key)
        if root is None:
            raise ValueError("E_AUTOMATION_TARGET_CLOSURE")
        if reference.get("kind") == "snapshot-ref":
            return LocalBaselineRegistry(root, key[1]).read(reference)
        return LocalSnapshotReader(root, key[1]).read(reference)


def load_store_config(path: str) -> ConfiguredStoreReader:
    return ConfiguredStoreReader(parse_document(Path(path).read_text(encoding="utf-8"), "store-config-v0.1.schema.yaml"))
