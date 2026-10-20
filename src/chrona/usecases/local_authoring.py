"""Local authoring initialization and deterministic Store configuration discovery."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from chrona.resources import minimal_template_resource, template_resource
from chrona.core.store_address import resolve_store_address
from chrona.usecases.materialize import UnavailableFontProviders, copy_context_closure, materializer_store_roots
from chrona.usecases.deck_context import SelectedDeckContext, load_deck_manifest, select_deck_context


@dataclass(frozen=True)
class StoreConfiguration:
    path: Path
    project_root: Path


@dataclass(frozen=True)
class DeferredSlide:
    slide_id: str
    context: str
    providers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"slideId": self.slide_id, "context": self.context, "providers": list(self.providers)}

    def as_diagnostic(self) -> dict[str, object]:
        return {"code": "W_INIT_EXAMPLE_SLIDE_DEFERRED", "severity": "warning",
                "component": "initialization", "sourceRef": self.context, "revisionRefs": [],
                "message": "Obtain the required font provider and initialize a new directory to include this slide.",
                "details": self.as_dict()}


@dataclass(frozen=True)
class InitializationResult:
    directory: Path
    available_slides: tuple[str, ...] = ()
    deferred_slides: tuple[DeferredSlide, ...] = ()


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


def initialize_project(destination: Path, *, example: str | None = None) -> InitializationResult:
    """Create an editable starter or an explicitly selected corpus without replacement."""
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"E_INIT_OUTPUT_EXISTS: {destination} already exists and is not empty; init into a new or empty directory")
    source = minimal_template_resource() if example is None else template_resource(example)
    _copy_template(source, destination)
    if example is None or not (destination / "manifest.yaml").is_file():
        return InitializationResult(destination)  # plain Projects, no Contexts and so no Store
    # Contexts are immutable references.  A freshly initialized project must
    # therefore contain their snapshot closure before its Store config is
    # advertised to commands; mutable source paths are never a reader fallback.
    store_root = destination / ".chrona" / "store"
    manifest_path = destination / "manifest.yaml"
    loaded_manifest = load_deck_manifest(manifest_path)
    manifest = dict(loaded_manifest.document)
    if not isinstance(manifest, dict) or manifest.get("version") != "chrona/example-materializer/v0.1":
        raise ValueError("E_INIT_EXAMPLE_MANIFEST: invalid example manifest")
    slides = manifest.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("E_INIT_EXAMPLE_MANIFEST: expected nonempty slides")
    contexts: dict[str, SelectedDeckContext] = {}
    slide_addresses: dict[str, str] = {}
    for slide in slides:
        if not isinstance(slide, dict) or not isinstance(slide.get("id"), str):
            raise ValueError("E_INIT_EXAMPLE_MANIFEST: expected slide id")
        selected = select_deck_context(manifest_path, loaded_manifest, slide["id"])
        contexts[selected.address] = selected
        slide_addresses[slide["id"]] = selected.address
        for key in ("expectedSvg", "expectedScene"):
            if key in slide:
                output = resolve_store_address(destination, slide[key])
                if not output.is_relative_to(destination.resolve() / "generated"):
                    raise ValueError("E_INIT_EXAMPLE_MANIFEST: derived outputs must be under generated/")
    unavailable: dict[str, tuple[str, ...]] = {}
    shared_stores = materializer_store_roots(destination.resolve(), manifest.get("stores"))
    for address, selected in contexts.items():
        with TemporaryDirectory(prefix="chrona-init-closure-") as temporary:
            staged = Path(temporary)
            try:
                copy_context_closure(destination.resolve(), selected.source_path or selected, staged,
                                     **({"stores": shared_stores} if shared_stores else {}))
            except UnavailableFontProviders as error:
                unavailable[address] = error.providers
                continue
            for source_file in staged.rglob("*"):
                if source_file.is_file():
                    target = store_root / source_file.relative_to(staged)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source_file, target)
    retained = [slide for slide in slides if slide_addresses[slide["id"]] not in unavailable]
    deferred = tuple(DeferredSlide(slide["id"], slide_addresses[slide["id"]],
                                   unavailable[slide_addresses[slide["id"]]])
                     for slide in slides if slide not in retained)
    if not retained:
        raise ValueError("E_INIT_EXAMPLE_UNAVAILABLE: no slides have all required font providers")
    if deferred:
        retained_paths = {slide_addresses[slide["id"]] for slide in retained}
        retained_paths.update(slide[key] for slide in retained for key in ("expectedSvg", "expectedScene") if key in slide)
        # Virtual Context addresses never name authored files to remove.
        omitted_paths = {address for address in unavailable if contexts[address].source_path is not None}
        omitted_paths.update(slide[key] for slide in slides if slide not in retained
                             for key in ("expectedSvg", "expectedScene") if key in slide)
        for address in omitted_paths - retained_paths:
            resolve_store_address(destination, address).unlink(missing_ok=True)
        manifest["slides"] = retained
        if manifest.get("context") in unavailable:
            replacement = next((slide.get("context") for slide in retained if slide.get("context")), None)
            if replacement is None:
                manifest.pop("context", None)
            else:
                manifest["context"] = replacement
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    config = destination / ".chrona" / "store.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    document = yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [{
        "provider": "local", "identity": f"{example}-example", "root": _config_relative(store_root, config.parent),
    }]}, sort_keys=False)
    config.write_text(document, encoding="utf-8")
    return InitializationResult(destination, tuple(slide["id"] for slide in retained), deferred)


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
