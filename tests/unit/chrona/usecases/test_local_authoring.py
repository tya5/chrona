from pathlib import Path

import pytest

from chrona.usecases.local_authoring import discover_store_configuration, initialize_project


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


def test_init_is_non_overwriting_and_creates_a_materializable_example(tmp_path: Path):
    destination = tmp_path / "chrona-project"

    initialized = initialize_project(destination)

    assert initialized == destination
    assert (destination / ".chrona" / "store.yaml").is_file()
    assert (destination / "manifest.yaml").is_file()
    with pytest.raises(ValueError, match="E_INIT_OUTPUT_EXISTS"):
        initialize_project(destination)
