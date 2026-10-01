"""#723: content identity verification is required by default on the Store read path.

Every test decides from reference data and the reader flag; nothing depends on the host OS.
"""
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.app import cli
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.storage.snapshots import LocalBaselineRegistry
from chrona.usecases.local_authoring import initialize_project

PAYLOAD = b"id: project\n"
IDENTITY = "sha256:" + sha256(PAYLOAD).hexdigest()
WRONG = "sha256:" + "0" * 64


def _store(tmp_path: Path) -> dict:
    directory = snapshot_directory(tmp_path, "rev-1")
    directory.mkdir(parents=True)
    (directory / "project.yaml").write_bytes(PAYLOAD)
    return {"id": "project", "kind": "project", "store": {"provider": "local", "identity": "test"},
            "address": "project.yaml", "revision": {"token": "rev-1"}, "contentIdentity": IDENTITY}


def _unpinned(reference: dict) -> dict:
    return {key: value for key, value in reference.items() if key != "contentIdentity"}


def test_default_reader_reads_a_matching_identity(tmp_path):
    assert LocalSnapshotReader(tmp_path, "test").read(_store(tmp_path)) == PAYLOAD


def test_default_reader_refuses_a_mismatching_identity(tmp_path):
    reference = _store(tmp_path) | {"contentIdentity": WRONG}
    with pytest.raises(SnapshotReadError, match="E_CONTENT_IDENTITY$"):
        LocalSnapshotReader(tmp_path, "test").read(reference)


def test_default_reader_refuses_a_missing_identity(tmp_path):
    reference = _unpinned(_store(tmp_path))
    with pytest.raises(SnapshotReadError, match="E_CONTENT_IDENTITY_REQUIRED"):
        LocalSnapshotReader(tmp_path, "test").read(reference)


def test_optional_remains_an_explicit_opt_out_that_still_checks_a_supplied_identity(tmp_path):
    reference = _store(tmp_path)
    reader = LocalSnapshotReader(tmp_path, "test", require_content_identity=False)
    assert reader.read(_unpinned(reference)) == PAYLOAD
    with pytest.raises(SnapshotReadError, match="E_CONTENT_IDENTITY$"):
        reader.read(reference | {"contentIdentity": WRONG})


def _baseline(tmp_path: Path) -> tuple[LocalBaselineRegistry, dict]:
    registry = LocalBaselineRegistry(tmp_path, "test")
    reference = registry.publish("q2", {"id": "p", "kind": "project"})
    assert reference is not None
    return registry, reference


def test_baseline_registry_defaults_to_required_and_opts_out_explicitly(tmp_path):
    registry, reference = _baseline(tmp_path)
    assert registry.read(reference)
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY_REQUIRED"):
        registry.read(_unpinned(reference))
    with pytest.raises(ValueError, match="E_BASELINE_REFERENCE"):
        registry.read(reference | {"contentIdentity": WRONG})
    opted_out = LocalBaselineRegistry(tmp_path, "test", require_content_identity=False)
    assert opted_out.read(_unpinned(reference)) == registry.read(reference)


def _config(tmp_path: Path, **extra) -> ConfiguredStoreReader:
    return ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)} | extra]})


def test_store_config_without_integrity_means_required(tmp_path):
    reference = _store(tmp_path)
    reader = _config(tmp_path)
    assert reader.integrity == {("local", "test"): "required"}
    assert reader.read(reference) == PAYLOAD
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY_REQUIRED"):
        reader.read(_unpinned(reference))
    with pytest.raises(SnapshotReadError, match="E_CONTENT_IDENTITY$"):
        reader.read(reference | {"contentIdentity": WRONG})


def test_store_config_optional_is_an_explicit_opt_out_for_both_readers(tmp_path):
    reference = _store(tmp_path)
    reader = _config(tmp_path, integrity="optional")
    assert reader.read(_unpinned(reference)) == PAYLOAD
    _, baseline = _baseline(tmp_path)
    assert reader.read(_unpinned(baseline))
    with pytest.raises(SnapshotReadError, match="E_CONTENT_IDENTITY$"):
        reader.read(reference | {"contentIdentity": WRONG})


def test_init_example_writes_required_integrity(tmp_path):
    destination = initialize_project(tmp_path / "project", example="halcyon-1")
    stores = yaml.safe_load((destination / ".chrona" / "store.yaml").read_text(encoding="utf-8"))["stores"]
    assert [store["integrity"] for store in stores] == ["required"]


def test_cli_opt_out_flag_replaces_the_strict_flag():
    parser = cli._parser()
    base = ["validate", "--snapshot-reference", "r.yaml", "--snapshot-root", "s", "--store-identity", "test"]
    assert parser.parse_args(base).allow_missing_content_identity is False
    assert parser.parse_args([*base, "--allow-missing-content-identity"]).allow_missing_content_identity is True
