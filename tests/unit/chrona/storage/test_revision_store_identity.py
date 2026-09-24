from hashlib import sha256

import pytest

from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError
from chrona.storage.snapshot_paths import snapshot_directory


def _reference(payload: bytes) -> dict:
    return {
        "id": "project",
        "kind": "project",
        "store": {"provider": "local", "identity": "test"},
        "address": "project.yaml",
        "revision": {"token": "rev-1"},
        "contentIdentity": f"sha256:{sha256(payload).hexdigest()}",
    }


def test_reader_computes_identity_when_reference_omits_it_and_strict_mode_rejects(tmp_path):
    payload = b'{"project":{"id":"project"}}'
    location = snapshot_directory(tmp_path, "rev-1")
    location.mkdir()
    (location / "project.yaml").write_bytes(payload)
    reference = _reference(payload)
    reference.pop("contentIdentity")

    assert LocalSnapshotReader(tmp_path, "test").read(reference) == payload
    with pytest.raises(SnapshotReadError, match="E_CONTENT_IDENTITY_REQUIRED"):
        LocalSnapshotReader(tmp_path, "test", require_content_identity=True).read(reference)


def test_reader_store_reference_detail_names_expectation_and_missing_resource(tmp_path):
    reference = _reference(b"project")
    with pytest.raises(SnapshotReadError) as wrong_store:
        LocalSnapshotReader(tmp_path, "expected").read(reference)
    assert wrong_store.value.diagnostic_id == "E_STORE_REFERENCE"
    assert "expected local store identity=expected" in wrong_store.value.detail
    assert "received store=" in wrong_store.value.detail

    with pytest.raises(SnapshotReadError) as missing:
        LocalSnapshotReader(tmp_path, "test").read(reference)
    assert missing.value.diagnostic_id == "E_STORE_REFERENCE"
    assert "reference address=project.yaml" in missing.value.detail
    assert "found no file" in missing.value.detail
