import json

import pytest

from chrona.storage.revision_store import LocalTransactionalStore
from chrona.storage.snapshot_paths import snapshot_directory


def _project(title: str) -> dict:
    return {"project": {"id": "demo", "title": title}}


def test_local_transactional_store_persists_and_restarts_under_the_shared_codec(tmp_path):
    root = tmp_path / "store"
    first = LocalTransactionalStore(root, "local", _project("first"))
    initial = first.read()
    second = first.write(initial.revision, _project("second"))

    assert second is not None
    token = second.revision.removeprefix("local:")
    assert (snapshot_directory(root, token) / "project.json").is_file()
    assert not (root / token).exists()

    restarted = LocalTransactionalStore(root, "local", _project("ignored")).read()
    assert restarted == second
    assert restarted.parents == (initial.revision,)


@pytest.mark.parametrize("token", ("baseline:" + "a" * 64, "CON", "baseline%3Aabc"))
def test_local_transactional_store_restart_uses_codec_for_opaque_tip_tokens(tmp_path, token):
    root = tmp_path / "store"
    payload = b'{"project":{"id":"demo","title":"persisted"}}'
    directory = snapshot_directory(root, token)
    directory.mkdir(parents=True)
    (directory / "project.json").write_bytes(payload)
    (directory / "parents.json").write_text(json.dumps(["local:parent"]), encoding="utf-8")
    (root / "tip.json").write_text(json.dumps({"token": token}), encoding="utf-8")

    snapshot = LocalTransactionalStore(root, "local", _project("ignored")).read()

    assert snapshot.revision == f"local:{token}"
    assert snapshot.project["project"]["title"] == "persisted"
    assert snapshot.parents == ("local:parent",)


def test_local_transactional_store_does_not_fallback_to_pre_codec_raw_directory(tmp_path):
    root = tmp_path / "store"
    token = "local-legacy-safe-token"
    raw = root / token
    raw.mkdir(parents=True)
    (raw / "project.json").write_bytes(b'{"project":{"id":"demo"}}')
    (root / "tip.json").write_text(json.dumps({"token": token}), encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        LocalTransactionalStore(root, "local", _project("ignored"))
