from hashlib import sha256

import pytest

from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.materialize import _copy_reference


def test_snapshot_directory_is_injective_and_windows_safe(tmp_path):
    baseline = snapshot_directory(tmp_path, "baseline:abc")
    escaped = snapshot_directory(tmp_path, "baseline%3Aabc")
    assert baseline.name == "revision-baseline%3Aabc"
    assert escaped.name == "revision-baseline%253Aabc"
    assert baseline != escaped
    assert snapshot_directory(tmp_path, ".").name == "revision-%2E"
    assert snapshot_directory(tmp_path, "..").name == "revision-%2E%2E"
    assert snapshot_directory(tmp_path, "CON").name == "revision-CON"
    assert snapshot_directory(tmp_path, "release.").name == "revision-release%2E"


def test_local_snapshot_reader_reads_a_captured_baseline_token(tmp_path):
    token, address, payload = "baseline:012345", "snapshots/q2.yaml", b"version: chrona/snapshot-ref/v0.2\n"
    path = snapshot_directory(tmp_path, token) / address
    path.parent.mkdir(parents=True); path.write_bytes(payload)
    reference = {"store": {"provider": "local", "identity": "test"}, "revision": {"token": token},
                 "address": address, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    assert LocalSnapshotReader(tmp_path, "test").read(reference) == payload


def test_materializer_copies_baseline_token_under_the_same_encoded_directory(tmp_path):
    example = tmp_path / "example"; example.mkdir()
    (example / "project.yaml").write_text("version: timeline/v0.7\n", encoding="utf-8")
    token = "baseline:abc"
    reference = {"revision": {"token": token}, "address": "project.yaml", "kind": "project"}
    snapshot = tmp_path / "snapshot"; snapshot.mkdir()
    _copy_reference(example, reference, snapshot)
    assert (snapshot_directory(snapshot, token) / "project.yaml").is_file()


@pytest.mark.parametrize("token", ("", "draft", "Draft"))
def test_snapshot_directory_rejects_non_immutable_tokens(tmp_path, token):
    with pytest.raises(ValueError, match="E_IMMUTABLE_SNAPSHOT_REQUIRED"):
        snapshot_directory(tmp_path, token)


@pytest.mark.parametrize("address", ("/outside.yaml", r"outside\\resource.yaml", "folder/../outside.yaml"))
def test_local_snapshot_reader_rejects_addresses_that_can_escape_a_snapshot(tmp_path, address):
    reference = {"store": {"provider": "local", "identity": "test"}, "revision": {"token": "baseline:abc"},
                 "address": address}
    with pytest.raises(Exception, match="E_IMMUTABLE_SNAPSHOT_REQUIRED"):
        LocalSnapshotReader(tmp_path, "test").read(reference)
