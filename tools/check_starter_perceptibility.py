#!/usr/bin/env python3
"""Fail release conformance on perceptibility errors in the real default Draft."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import DraftExtensionPackageReader
from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import default_preset_resource, default_preset_root, safe_load
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = Path(__file__).resolve().parents[1]


def _starter_package_reader(project_path: Path, project: dict[str, Any], temporary: Path) -> DraftExtensionPackageReader:
    """Stage exact declared local package bytes in a temporary configured Store."""
    stores: dict[tuple[str, str], Path] = {}
    for extension in project.get("extensions", ()):
        reference = extension["resource"]
        provider, identity = reference["store"]["provider"], reference["store"]["identity"]
        if provider == "package":
            continue
        if provider != "local":
            raise ValueError(f"starter package Store requires an explicit provider adapter: {provider}")
        key = (provider, identity)
        store = stores.setdefault(key, temporary / f"store-{len(stores)}")
        token = reference["revision"]["token"]
        target = snapshot_directory(store, token) / reference["address"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((project_path.parent / reference["address"]).read_bytes())
    if not stores:
        return DraftExtensionPackageReader()
    config = temporary / "store-config.yaml"
    config.write_text(yaml.safe_dump({
        "version": "chrona/store-config/v0.1",
        "stores": [{"provider": provider, "identity": identity, "root": store.name,
                    "integrity": "optional"}
                   for (provider, identity), store in stores.items()],
    }, sort_keys=False), encoding="utf-8")
    return DraftExtensionPackageReader(lambda: load_store_config(str(config)))


def starter_rendered_review():
    """Render the real packaged default through its declared package pins."""
    project_path = ROOT / "examples/halcyon-1/project.yaml"
    project = safe_load(project_path.read_bytes())
    with TemporaryDirectory(prefix="chrona-starter-perceptibility-") as directory:
        package_reader = _starter_package_reader(project_path, project, Path(directory))
        draft = resolve_draft_render(
            project_path=project_path,
            preset_path=Path(str(default_preset_resource())),
            preset_root=Path(str(default_preset_root())),
            package_reader=package_reader,
        )
        return render_review(RenderRequest(
            draft.closure, draft.asset_root, ReferenceScheduler(),
            renderer=V05SvgRenderer(), asset_root=draft.asset_root,
            draft_auto_block=draft.auto_block,
        ))


def starter_scene_document() -> dict:
    """Render the packaged default, not a simplified Scene-only approximation."""
    return scene_document(starter_rendered_review().scene)


def starter_errors(document: dict) -> tuple:
    """Use #446's sole evaluator and its existing error severity contract."""
    return tuple(item for item in evaluate_scene_perceptibility(document)
                 if item.severity == "error")


def main() -> int:
    errors = starter_errors(starter_scene_document())
    for item in errors:
        print(f"ERROR {item.code} {item.scene_path} primitives={','.join(item.primitive_ids)}")
    print(f"Starter perceptibility: {'FAIL' if errors else 'PASS'} ({len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
