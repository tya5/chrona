from pathlib import Path

import pytest

from chrona.usecases.local_authoring import discover_store_configuration, initialize_project
from chrona.operational.store_config import load_store_config
from chrona.presentation.model.closure import resolve_render_context
from chrona.resources import safe_load


def test_explicit_store_config_wins_over_discovered_project_config(tmp_path: Path):
    project = tmp_path / "project"
    configured = project / ".chrona" / "store.yaml"
    configured.parent.mkdir(parents=True)
    configured.write_text("version: chrona/store-config/v0.1\nstores: []\n")
    explicit = tmp_path / "explicit.yaml"; explicit.write_text("version: chrona/store-config/v0.1\nstores: []\n")

    resolved = discover_store_configuration(explicit=explicit, start=project / "nested")

    assert resolved.path == explicit.resolve()


def test_store_config_is_discovered_only_by_project_local_upward_walk(tmp_path: Path):
    root = tmp_path / "project"
    config = root / ".chrona" / "store.yaml"
    config.parent.mkdir(parents=True); config.write_text("version: chrona/store-config/v0.1\nstores: []\n")

    resolved = discover_store_configuration(start=root / "a" / "b")

    assert resolved.path == config
    with pytest.raises(ValueError, match="E_STORE_CONFIG_REQUIRED"):
        discover_store_configuration(start=tmp_path / "outside")


def test_init_creates_only_an_editable_minimal_draft_and_is_non_overwriting(tmp_path: Path):
    destination = tmp_path / "chrona-project"

    initialized = initialize_project(destination)

    assert initialized == destination
    assert {path.name for path in destination.iterdir()} == {"README.md", "actual.yaml", "project.yaml"}
    assert not (destination / ".chrona").exists()
    assert not (destination / "manifest.yaml").exists()
    with pytest.raises(ValueError, match="E_INIT_OUTPUT_EXISTS"):
        initialize_project(destination)


def test_explicit_halcyon_init_is_store_resolvable_without_root_revision_closures(tmp_path: Path):
    destination = tmp_path / "chrona-project"

    initialized = initialize_project(destination, example="halcyon-1")

    assert initialized == destination
    assert (destination / "manifest.yaml").is_file()
    assert (destination / ".chrona" / "store.yaml").is_file()
    assert not tuple(destination.glob("revision-*"))
    config = load_store_config(str(destination / ".chrona" / "store.yaml"))
    closures = []
    for path in sorted((destination / "contexts").glob("*.yaml")):
        context = safe_load(path.read_bytes())
        context_reference = {
            "id": context["id"], "kind": "render-context",
            "store": context["body"]["project"]["store"], "address": path.relative_to(destination).as_posix(),
            "revision": context["body"]["project"]["revision"],
        }
        closures.append(resolve_render_context(context_reference, config))
    assert closures[0].context.identity.id == "halcyon-1-01-mission-brief"
    assert len(closures) == 12
    assert tuple((destination / ".chrona" / "store").glob("revision-*"))
