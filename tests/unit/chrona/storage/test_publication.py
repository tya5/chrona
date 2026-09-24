import os
from pathlib import Path

import pytest

from chrona.storage.publication import publish_exclusive


def test_exclusive_publication_writes_once_and_rejects_existing_destination(tmp_path):
    destination = tmp_path / "outputs" / "result.json"

    publish_exclusive(destination, b"completed")

    assert destination.read_bytes() == b"completed"
    with pytest.raises(FileExistsError):
        publish_exclusive(destination, b"replacement")
    assert destination.read_bytes() == b"completed"


def test_exclusive_publication_cleans_reservation_when_replacement_fails(tmp_path, monkeypatch):
    destination = tmp_path / "result.json"
    original_replace = Path.replace

    def fail_replace(source: Path, target: Path) -> Path:
        assert target == destination
        assert target.read_bytes() == b""
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        publish_exclusive(destination, b"completed")
    monkeypatch.setattr(Path, "replace", original_replace)

    assert not destination.exists()
    assert not (tmp_path / f".result.json.{os.getpid()}.tmp").exists()
