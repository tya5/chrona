from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.core.ports import SnapshotReadError
from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import DraftExtensionPackageReader
from chrona.storage.snapshot_paths import snapshot_directory
from tests.support.store_workspace import STORE_IDENTITY, StoreWorkspace


def _identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _reader(work: StoreWorkspace, *, integrity: str | None = None) -> DraftExtensionPackageReader:
    if integrity is not None:
        config = yaml.safe_load(work.config.read_text(encoding="utf-8"))
        config["stores"][0]["integrity"] = integrity
        work.config.write_text(yaml.safe_dump(config), encoding="utf-8")
    return DraftExtensionPackageReader(lambda: load_store_config(str(work.config)))


def test_package_reference_bypasses_store_config_loader():
    loaded = False

    def unexpected_config_load():
        nonlocal loaded
        loaded = True
        raise AssertionError("packaged resources do not need local Store configuration")

    reader = DraftExtensionPackageReader(unexpected_config_load)
    reference = {
        "id": "default-font-metrics", "kind": "profile-package",
        "store": {"provider": "package", "identity": "chrona.resources"},
        "address": "fonts/default-font-metrics.yaml", "revision": {"token": "v0.1"},
    }

    payload = reader.read(reference)

    assert payload.startswith(b"algorithm:")
    assert not loaded


def test_named_local_stores_are_routed_independently_with_one_lazy_config_load(tmp_path):
    work = StoreWorkspace(tmp_path)
    second_store = tmp_path / "second-store"
    first_payload = b"packageId: first\n"
    second_payload = b"packageId: second\n"
    first_path = snapshot_directory(work.store, "package-r1") / "packages/first.yaml"
    second_path = snapshot_directory(second_store, "package-r2") / "packages/second.yaml"
    first_path.parent.mkdir(parents=True, exist_ok=True)
    second_path.parent.mkdir(parents=True, exist_ok=True)
    first_path.write_bytes(first_payload)
    second_path.write_bytes(second_payload)
    config = yaml.safe_load(work.config.read_text(encoding="utf-8"))
    config["stores"].append({
        "provider": "local", "identity": "second", "root": str(second_store), "integrity": "required",
    })
    work.config.write_text(yaml.safe_dump(config), encoding="utf-8")
    loads = 0

    def load():
        nonlocal loads
        loads += 1
        return load_store_config(str(work.config))

    reader = DraftExtensionPackageReader(load)
    first = {"id": "first-ref", "kind": "profile-package",
             "store": {"provider": "local", "identity": STORE_IDENTITY},
             "address": "packages/first.yaml", "revision": {"token": "package-r1"},
             "contentIdentity": _identity(first_payload)}
    second = {"id": "second-ref", "kind": "profile-package",
              "store": {"provider": "local", "identity": "second"},
              "address": "packages/second.yaml", "revision": {"token": "package-r2"},
              "contentIdentity": _identity(second_payload)}

    assert reader.read(first) == first_payload
    assert reader.read(second) == second_payload
    assert loads == 1


def test_no_config_loader_fails_closed_for_store_reference():
    reader = DraftExtensionPackageReader()
    reference = {
        "id": "pinned-package", "kind": "profile-package",
        "store": {"provider": "local", "identity": "local-test"},
        "address": "packages/pinned.yaml", "revision": {"token": "r1"},
    }

    with pytest.raises(SnapshotReadError) as raised:
        reader.read(reference)

    assert raised.value.diagnostic_id == "E_STORE_CONFIG_REQUIRED"


@pytest.mark.parametrize("integrity", ["optional", "required"])
def test_store_integrity_controls_missing_pin_but_always_checks_a_supplied_pin(tmp_path, integrity):
    work = StoreWorkspace(tmp_path)
    reader = _reader(work, integrity=integrity)
    unpinned = {key: value for key, value in work.project_ref.items() if key != "contentIdentity"}

    if integrity == "required":
        with pytest.raises(SnapshotReadError) as missing:
            reader.read(unpinned)
        assert missing.value.diagnostic_id == "E_CONTENT_IDENTITY_REQUIRED"
    else:
        assert reader.read(unpinned) == reader.read(work.project_ref)

    with pytest.raises(SnapshotReadError) as mismatch:
        reader.read({**work.project_ref, "contentIdentity": "sha256:" + "0" * 64})
    assert mismatch.value.diagnostic_id == "E_CONTENT_IDENTITY"
