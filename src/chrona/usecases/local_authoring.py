"""Local authoring initialization and deterministic Store configuration discovery."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import yaml


@dataclass(frozen=True)
class StoreConfiguration:
    path: Path
    project_root: Path


def discover_store_configuration(*, explicit: Path | None = None, start: Path | None = None) -> StoreConfiguration:
    """Resolve only an explicit config or a project-local `.chrona/store.yaml` ancestor."""
    if explicit is not None:
        path = explicit.resolve()
        if not path.is_file():
            raise ValueError("E_STORE_CONFIG_REQUIRED")
        return StoreConfiguration(path, path.parent.parent if path.parent.name == ".chrona" else path.parent)
    current = (start or Path.cwd()).resolve()
    for root in (current, *current.parents):
        path = root / ".chrona" / "store.yaml"
        if path.is_file():
            return StoreConfiguration(path, root)
    raise ValueError("E_STORE_CONFIG_REQUIRED")


def initialize_project(destination: Path, *, example: str = "halcyon-1") -> Path:
    """Create a complete local project without ever replacing authored files."""
    if example != "halcyon-1":
        raise ValueError("E_INIT_EXAMPLE")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("E_INIT_OUTPUT_EXISTS")
    package_root = Path(__file__).resolve().parents[3]
    source = package_root / "examples" / example
    if not source.is_dir():
        raise ValueError("E_INIT_EXAMPLE")
    shutil.copytree(source, destination, dirs_exist_ok=True)
    config = destination / ".chrona" / "store.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [{
        "provider": "local", "identity": f"{example}-local", "root": str(destination.resolve()), "integrity": "optional",
    }]}, sort_keys=False), encoding="utf-8")
    return destination
