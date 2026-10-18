from hashlib import sha256
import errno
from pathlib import Path
import pytest
import yaml

from chrona.operational.command_engine import check_command


class Reader:
    def __init__(self, payload): self.payload = payload
    def read(self, reference): return self.payload


def test_command_check_has_no_write_and_validates_target_precondition():
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    payload = yaml.safe_dump(project).encode(); digest = "sha256:" + sha256(payload).hexdigest()
    target = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "p.yaml", "revision": {"token": "r1"}, "contentIdentity": digest}
    command = {"version": "chrona/command/v0.3", "commandId": "c1", "type": "captureSnapshot", "target": target, "baseRevision": "r1", "expectedContentIdentity": digest, "payload": {"snapshotId": "q2", "registry": target | {"id": "r", "kind": "snapshot-registry"}}}
    assert check_command(Reader(payload), command)["status"] == "accepted"
    assert check_command(Reader(payload), command | {"baseRevision": "old"})["diagnostics"][0]["code"] == "E_AUTOMATION_BASE_REVISION"


def test_command_check_accepts_revision_only_target_and_returns_computed_identity():
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    payload = yaml.safe_dump(project).encode()
    target = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "p.yaml", "revision": {"token": "r1"}}
    command = {"version": "chrona/command/v0.3", "commandId": "c1", "type": "captureSnapshot", "target": target, "baseRevision": "r1", "payload": {"snapshotId": "q2", "registry": target | {"id": "r", "kind": "snapshot-registry"}}}

    result = check_command(Reader(payload), command)

    assert result["status"] == "accepted"
    assert result["inputs"][0]["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()


def test_expected_content_identity_is_an_optional_lock_that_still_rejects_a_stale_value():
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    payload = yaml.safe_dump(project).encode()
    target = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "p.yaml", "revision": {"token": "r1"}}
    command = {"version": "chrona/command/v0.3", "commandId": "c1", "type": "captureSnapshot", "target": target, "baseRevision": "r1", "payload": {"snapshotId": "q2", "registry": target | {"id": "r", "kind": "snapshot-registry"}}}

    assert check_command(Reader(payload), command)["status"] == "accepted"
    result = check_command(Reader(payload), command | {"expectedContentIdentity": "sha256:" + "0" * 64})
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["code"] == "E_AUTOMATION_BASE_REVISION"


def _snapshot_apply_request(root):
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    reader = Reader(yaml.safe_dump(project).encode())
    reader.roots = {("local", "registry"): root}
    target = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "input"},
              "address": "p.yaml", "revision": {"token": "r1"}}
    command = {"version": "chrona/command/v0.3", "commandId": "c1", "type": "captureSnapshot",
               "target": target, "baseRevision": "r1",
               "payload": {"snapshotId": "q2", "registry": {"provider": "local", "identity": "registry"}}}
    return reader, command


def test_store_lock_entry_failure_rejects_before_publication(tmp_path, monkeypatch):
    from chrona.operational.command_engine import apply_actual_command
    reader, command = _snapshot_apply_request(tmp_path)
    original_open = Path.open

    def denied(path, *args, **kwargs):
        if path.name == ".chrona-store.lock":
            raise PermissionError(errno.EACCES, "denied", str(path))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    result = apply_actual_command(reader, command)
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["code"] == "E_STORE_LOCK_UNAVAILABLE"
    assert list(tmp_path.iterdir()) == []


def test_publication_io_failure_is_not_misreported_as_lock_refusal(tmp_path, monkeypatch):
    from chrona.operational.command_engine import apply_actual_command
    reader, command = _snapshot_apply_request(tmp_path)
    failure = OSError(errno.EIO, "publication failed")

    def fail(*args):
        raise failure

    monkeypatch.setattr("chrona.operational.command_engine._apply_checked_command", fail)
    with pytest.raises(OSError) as raised:
        apply_actual_command(reader, command)
    assert raised.value is failure
