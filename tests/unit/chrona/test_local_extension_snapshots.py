"""Local extension snapshots retain the one validated byte acquisition for later staging."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from chrona.extensions.profiles import (
    resolve_local_extension_manifests,
    resolve_local_extension_snapshots,
)


PACKAGE = b"version: chrona/profile/v0.3\npackageId: sample\nprofiles: {}\n"


def _project(path: str = "packages/sample.yaml", **extra):
    return {"extensions": [{"packageId": "sample", "path": path, **extra}]}


def test_snapshot_retains_declared_relative_path_raw_bytes_and_decoded_manifest(tmp_path):
    (tmp_path / "packages").mkdir()
    target = tmp_path / "packages/sample.yaml"
    target.write_bytes(PACKAGE)

    snapshots, diagnostics = resolve_local_extension_snapshots(_project(), tmp_path)

    assert diagnostics == []
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.package_id == "sample"
    assert snapshot.path == "packages/sample.yaml"
    assert snapshot.content == PACKAGE
    assert snapshot.manifest == {
        "version": "chrona/profile/v0.3",
        "packageId": "sample",
        "profiles": {},
        "contentIdentity": "sha256:" + sha256(PACKAGE).hexdigest(),
    }


def test_snapshot_reads_source_once_and_remains_stable_if_source_changes(tmp_path, monkeypatch):
    target = tmp_path / "sample.yaml"
    target.write_bytes(PACKAGE)
    original = Path.read_bytes
    reads: list[Path] = []

    def counted_read(path: Path) -> bytes:
        if path == target:
            reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read)
    snapshots, diagnostics = resolve_local_extension_snapshots(_project("sample.yaml"), tmp_path)
    target.write_bytes(b"version: replaced\n")

    assert diagnostics == []
    assert reads == [target]
    assert snapshots[0].content == PACKAGE
    assert snapshots[0].manifest["packageId"] == "sample"


def test_manifest_resolver_is_a_projection_over_the_same_snapshot_acquisition(tmp_path, monkeypatch):
    target = tmp_path / "sample.yaml"
    target.write_bytes(PACKAGE)
    original = Path.read_bytes
    reads = 0

    def counted_read(path: Path) -> bytes:
        nonlocal reads
        if path == target:
            reads += 1
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read)
    manifests, diagnostics = resolve_local_extension_manifests(_project("sample.yaml"), tmp_path)

    assert diagnostics == []
    assert reads == 1
    assert manifests == {"sample": {
        "version": "chrona/profile/v0.3",
        "packageId": "sample",
        "profiles": {},
        "contentIdentity": "sha256:" + sha256(PACKAGE).hexdigest(),
    }}


def test_declared_identity_is_checked_against_the_snapshot_bytes(tmp_path):
    target = tmp_path / "sample.yaml"
    target.write_bytes(PACKAGE)
    project = _project("sample.yaml", contentIdentity="sha256:" + "0" * 64)

    snapshots, diagnostics = resolve_local_extension_snapshots(project, tmp_path)

    assert snapshots == ()
    assert [(item.id, item.path) for item in diagnostics] == [("E_CONTENT_IDENTITY", "/extensions/0/path")]


def test_missing_and_escaping_paths_keep_existing_diagnostics(tmp_path):
    inside = tmp_path / "project"
    inside.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_bytes(PACKAGE)

    missing, missing_diagnostics = resolve_local_extension_snapshots(_project("missing.yaml"), inside)
    escaping, escaping_diagnostics = resolve_local_extension_snapshots(_project("../outside.yaml"), inside)

    assert missing == escaping == ()
    assert [(item.id, item.path) for item in missing_diagnostics] == [("E_EXTENSION_UNRESOLVED", "/extensions/0/path")]
    assert [(item.id, item.path) for item in escaping_diagnostics] == [("E_EXTENSION_UNRESOLVED", "/extensions/0/path")]
    assert "was not found" in missing_diagnostics[0].message
    assert "leaves the Project directory" in escaping_diagnostics[0].message


@pytest.mark.parametrize("content", [b"not: [valid", b"- not-a-mapping\n"])
def test_invalid_or_non_mapping_package_content_is_rejected_without_snapshot(tmp_path, content):
    (tmp_path / "sample.yaml").write_bytes(content)

    snapshots, diagnostics = resolve_local_extension_snapshots(_project("sample.yaml"), tmp_path)

    assert snapshots == ()
    assert [(item.id, item.path) for item in diagnostics] == [("E_EXTENSION_UNRESOLVED", "/extensions/0/path")]
    assert "not a YAML mapping" in diagnostics[0].message
