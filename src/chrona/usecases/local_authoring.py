"""Local authoring initialization and deterministic Store configuration discovery."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import yaml

from chrona.usecases.materialize import copy_context_closure


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
    source = files("chrona.resources").joinpath("examples", example)
    if not source.is_dir():
        raise ValueError("E_INIT_EXAMPLE")
    _copy_template(source, destination)
    # Contexts are immutable references.  A freshly initialized project must
    # therefore contain their snapshot closure before its Store config is
    # advertised to commands; mutable source paths are never a reader fallback.
    for context in sorted((destination / "contexts").glob("*.yaml")):
        copy_context_closure(destination, context, destination)
    config = destination / ".chrona" / "store.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [{
        "provider": "local", "identity": f"{example}-example", "root": str(destination.resolve()), "integrity": "optional",
    }]}, sort_keys=False), encoding="utf-8")
    return destination


def _copy_template(source: object, destination: Path) -> None:
    """Copy packaged template bytes without recovering a source-checkout path."""
    for child in source.iterdir():  # type: ignore[union-attr]
        target = destination / child.name
        if child.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _copy_template(child, target)
        elif child.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(child.read_bytes())
