from hashlib import sha256
import yaml

from chrona.operational.command_engine import check_command


class Reader:
    def __init__(self, payload): self.payload = payload
    def read(self, reference): return self.payload


def test_command_check_has_no_write_and_validates_target_precondition():
    project = {"version": "timeline/v0.1", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    payload = yaml.safe_dump(project).encode(); digest = "sha256:" + sha256(payload).hexdigest()
    target = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "p.yaml", "revision": {"token": "r1"}, "contentIdentity": digest}
    command = {"version": "chrona/command/v0.2", "commandId": "c1", "type": "captureSnapshot", "target": target, "baseRevision": "r1", "expectedContentIdentity": digest, "payload": {"snapshotId": "q2", "registry": target | {"id": "r", "kind": "snapshot-registry"}}}
    assert check_command(Reader(payload), command)["status"] == "accepted"
    assert check_command(Reader(payload), command | {"baseRevision": "old"})["diagnostics"][0]["code"] == "E_AUTOMATION_BASE_REVISION"
