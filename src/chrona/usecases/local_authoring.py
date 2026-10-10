"""Local authoring initialization and deterministic Store configuration discovery."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from chrona.resources import minimal_template_resource, template_resource
from chrona.usecases.materialize import copy_context_closure


EXAMPLE_INTEGRITY_COMMENT = (
    "  # This example Store opts out of required content identity: the example Contexts leave inner\n"
    "  # references unpinned by design (ADR-0030). Example corpus only; Stores you create keep `required`.\n"
)


@dataclass(frozen=True)
class StoreConfiguration:
    path: Path
    project_root: Path


def discover_store_configuration(*, explicit: Path | None = None, start: Path | None = None) -> StoreConfiguration:
    """Resolve only an explicit config or a project-local `.chrona/store.yaml` ancestor."""
    if explicit is not None:
        path = explicit.resolve()
        if not path.is_file():
            raise ValueError(f"E_STORE_CONFIG_REQUIRED: {explicit} is not a file; pass an existing Store config")
        return StoreConfiguration(path, path.parent.parent if path.parent.name == ".chrona" else path.parent)
    current = (start or Path.cwd()).resolve()
    for root in (current, *current.parents):
        path = root / ".chrona" / "store.yaml"
        if path.is_file():
            return StoreConfiguration(path, root)
    raise ValueError(f"E_STORE_CONFIG_REQUIRED: no .chrona/store.yaml in {start or 'the current directory'} or any parent; pass --store-config")


def initialize_project(destination: Path, *, example: str | None = None) -> Path:
    """Create an editable starter or an explicitly selected corpus without replacement."""
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"E_INIT_OUTPUT_EXISTS: {destination} already exists and is not empty; init into a new or empty directory")
    source = minimal_template_resource() if example is None else template_resource(example)
    _copy_template(source, destination)
    if example is None or not (destination / "manifest.yaml").is_file():
        return destination  # the starter, or numbered stages: plain Projects, no Contexts and so no Store
    # Contexts are immutable references.  A freshly initialized project must
    # therefore contain their snapshot closure before its Store config is
    # advertised to commands; mutable source paths are never a reader fallback.
    store_root = destination / ".chrona" / "store"
    for context in sorted((destination / "contexts").glob("*.yaml")):
        copy_context_closure(destination, context, store_root)
    config = destination / ".chrona" / "store.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    document = yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [{
        "provider": "local", "identity": f"{example}-example", "root": _config_relative(store_root, config.parent), "integrity": "optional",
    }]}, sort_keys=False)
    # The example corpus is not a trust boundary and its Contexts leave inner references unpinned by design
    # (ADR-0030), so the example Store opts out explicitly (#727); every other Store keeps the `required` default (#723).
    document = document.replace("  integrity: optional\n", EXAMPLE_INTEGRITY_COMMENT + "  integrity: optional\n")
    config.write_text(document, encoding="utf-8")
    return destination


def _config_relative(store_root: Path, config_directory: Path) -> str:
    """The Store root as the config file spells it: relative to the config's own directory, with forward slashes.

    A relative root is resolved against the config file (#781), so the directory can be moved, copied or committed and
    the file holds no host path.
    """
    return Path(os.path.relpath(store_root, config_directory)).as_posix()


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
