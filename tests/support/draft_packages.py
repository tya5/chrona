"""Explicit immutable-package Stores for Draft ingress integration tests."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from chrona.storage.snapshot_paths import snapshot_directory


def stage_project_package_store(root: Path, project: Mapping[str, Any], resource_root: Path) -> Path:
    """Stage exact declared package bytes without rewriting Project pins.

    The fixture's resource tree supplies bytes; production still reads only
    its explicitly configured immutable Store. Supplied content identities
    remain untouched and are checked by the normal reader.
    """
    root.mkdir(parents=True, exist_ok=True)
    stores: dict[tuple[str, str], Path] = {}
    for extension in project.get("extensions", ()):
        reference = extension["resource"]
        provider, identity = reference["store"]["provider"], reference["store"]["identity"]
        if provider == "package":
            continue
        if provider != "local":
            raise ValueError(f"test package Store provider must be local: {provider}")
        store = stores.setdefault((provider, identity), root / f"store-{len(stores)}")
        target = snapshot_directory(store, reference["revision"]["token"]) / reference["address"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((resource_root / reference["address"]).read_bytes())
    if not stores:
        raise ValueError("package Store fixture requires a declared local reference")
    config = root / "store-config.yaml"
    config.write_text(yaml.safe_dump({
        "version": "chrona/store-config/v0.1",
        "stores": [{"provider": provider, "identity": identity,
                    "root": store.name, "integrity": "optional"}
                   for (provider, identity), store in stores.items()],
    }, sort_keys=False), encoding="utf-8")
    return config
