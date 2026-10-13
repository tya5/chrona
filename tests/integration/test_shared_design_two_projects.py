"""One authored shared design is consumed by two Projects and both public render paths (#1342)."""
from __future__ import annotations

from pathlib import Path
import shutil

import yaml

from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import snapshot_reader_for
from chrona.presentation.scene.serialization import serialize_scene
from chrona.resources import safe_load
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.context_review import render_context_closure, resolve_context_closure
from chrona.usecases.materialize import copy_context_closure, materialize

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict:
    return safe_load(path.read_bytes())


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _share_design(context_path: Path) -> None:
    context = _load(context_path)
    for key, resource_id, address in (
        ("theme", "target-b", "themes/briefing.yaml"),
        ("colorScheme", "target-b", "schemes/briefing.yaml"),
        ("layout", "target-b", "layouts/briefing.yaml"),
    ):
        reference = context["body"][key]
        reference.update(id=resource_id, store={"provider": "local", "identity": "shared-designs"},
                         address=address, revision={"token": "example-v1"})
        reference.pop("contentIdentity", None)
    _write(context_path, context)


def _render_both_paths(project: Path, slide_id: str, context_path: Path, designs_revision: Path,
                       store_config: Path, *, output: Path) -> tuple[bytes, bytes]:
    materialized = materialize(project / "manifest.yaml", slide_id, output, write=True)

    own_store = project / ".chrona" / "store"
    own_store.mkdir(parents=True, exist_ok=True)
    reference, token = copy_context_closure(
        project, context_path, own_store, stores={"shared-designs": designs_revision},
    )
    staged_context = snapshot_directory(own_store, token) / context_path.relative_to(project)
    assert staged_context.read_bytes() == context_path.read_bytes()

    config = load_store_config(str(store_config))
    reader, snapshot_root = snapshot_reader_for(config, reference)
    closure = resolve_context_closure(reference, reader)
    rendered = render_context_closure(closure, snapshot_root)

    svg = materialized.rendered.artifact.content
    scene = serialize_scene(materialized.rendered.scene)
    assert rendered.artifact.content == svg
    assert serialize_scene(rendered.scene) == scene
    return scene, svg


def test_two_projects_share_one_authored_design_through_materializer_and_render_review(tmp_path: Path) -> None:
    sources = {
        "halcyon-1": (ROOT / "examples" / "halcyon-1", "target-b", "contexts/21-target-b.yaml"),
        "chrona-roadmap": (ROOT / "examples" / "chrona-roadmap", "roadmap", "contexts/roadmap.yaml"),
    }
    projects: dict[str, Path] = {}
    for name, (source, _slide, _context) in sources.items():
        project = tmp_path / name
        shutil.copytree(source, project)
        projects[name] = project

    designs_revision = tmp_path / "designs" / "revision-example-v1"
    # Target B's design is the packaged shared design `designs/target-b/` (design reuse step 2).
    packaged = ROOT / "src" / "chrona" / "resources" / "designs" / "target-b"
    for folder, source in (
        ("themes", "theme.yaml"),
        ("schemes", "scheme.yaml"),
        ("layouts", "layout.yaml"),
    ):
        target = designs_revision / folder / "briefing.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(packaged / source, target)

    for project in projects.values():
        manifest_path = project / "manifest.yaml"
        manifest = _load(manifest_path)
        manifest["stores"] = [{"identity": "shared-designs", "root": "../designs/revision-example-v1"}]
        _write(manifest_path, manifest)
        _share_design(project / sources[project.name][2])

    config_dir = tmp_path / ".chrona"
    config_path = config_dir / "store.yaml"
    _write(config_path, {"version": "chrona/store-config/v0.1", "stores": [
        {"provider": "local", "identity": "halcyon-1-example", "root": "../halcyon-1/.chrona/store", "integrity": "optional"},
        {"provider": "local", "identity": "chrona-roadmap-example", "root": "../chrona-roadmap/.chrona/store", "integrity": "optional"},
        {"provider": "local", "identity": "shared-designs", "root": "../designs", "integrity": "optional"},
    ]})

    contexts = {name: project / sources[name][2] for name, project in projects.items()}
    original_contexts = {name: path.read_bytes() for name, path in contexts.items()}
    before: dict[str, tuple[bytes, bytes]] = {}
    for name, project in projects.items():
        slide = sources[name][1]
        before[name] = _render_both_paths(
            project, slide, contexts[name], designs_revision, config_path,
            output=tmp_path / "materialized" / f"{name}-before",
        )

    theme_path = designs_revision / "themes" / "briefing.yaml"
    theme = _load(theme_path)
    theme["body"]["values"]["size.body"]["value"] = 13
    _write(theme_path, theme)

    for name, project in projects.items():
        slide = sources[name][1]
        after = _render_both_paths(
            project, slide, contexts[name], designs_revision, config_path,
            output=tmp_path / "materialized" / f"{name}-after",
        )
        assert after[0] != before[name][0]
        assert after[1] != before[name][1]
        assert contexts[name].read_bytes() == original_contexts[name]

    assert all(contexts[name].read_bytes() == original_contexts[name] for name in projects)
    # Context references identify the shared resources, but deliberately carry no byte pin.
    for context_path in contexts.values():
        body = _load(context_path)["body"]
        for key in ("theme", "colorScheme", "layout"):
            assert body[key]["store"]["identity"] == "shared-designs"
            assert body[key]["revision"]["token"] == "example-v1"
            assert "contentIdentity" not in body[key]
