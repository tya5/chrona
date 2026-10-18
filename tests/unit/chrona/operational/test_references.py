import json
from pathlib import Path

import pytest

from chrona.operational.references import ReplayLedger, verify_reference
from chrona.operational.resources import content_identity


class Reader:
    def __init__(self, payload: bytes): self.payload = payload
    def read(self, reference): return self.payload


def _project_payload():
    return b"project:\n  id: p\n"


def _reference(payload):
    import hashlib
    return {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "project.json", "revision": {"token": "r1"}, "contentIdentity": "sha256:" + hashlib.sha256(payload).hexdigest()}


def test_reference_verification_requires_exact_bytes_kind_and_id():
    payload = _project_payload()
    assert verify_reference(Reader(payload), _reference(payload), kind="project").value["project"]["id"] == "p"
    with pytest.raises(ValueError, match="E_AUTOMATION_TARGET_CLOSURE"):
        verify_reference(Reader(payload), _reference(payload) | {"id": "other"})


def test_replay_ledger_survives_reopen_and_rejects_changed_command_id(tmp_path: Path):
    request = {"version": "chrona/command/v0.3", "commandId": "c1"}
    target = {"id": "actual", "revision": {"token": "r1"}}
    ledger = ReplayLedger(tmp_path / "replays.json")
    first = ledger.record("c1", request, target, {"status": "accepted"})
    replay = ReplayLedger(tmp_path / "replays.json").lookup("c1", request, target)
    assert replay == first
    with pytest.raises(ValueError, match="E_COMMAND_ID_REUSE"):
        ledger.lookup("c1", request | {"reason": "different"}, target)


def test_replay_history_retains_and_verifies_the_canonical_request(tmp_path: Path):
    request = {"version": "chrona/command/v0.4", "commandId": "c1", "type": "revertActualCommand",
               "payload": {"commandId": "origin"}}
    target = {"id": "actual", "revision": {"token": "r1"}}
    ledger = ReplayLedger(tmp_path / "replays.json")

    recorded = ledger.record("c1", request, target, {"status": "accepted"})
    reopened = ReplayLedger(ledger.path).history("c1")

    assert recorded.request == request
    assert reopened == recorded
    assert reopened.request_identity == content_identity(request)
    assert ReplayLedger(ledger.path).history("missing") is None


def test_legacy_history_is_readable_without_rewriting_the_ledger(tmp_path: Path):
    path = tmp_path / "replays.json"
    request = {"version": "chrona/command/v0.3", "commandId": "old"}
    target = {"id": "actual", "revision": {"token": "r1"}}
    from chrona.operational.resources import canonical_bytes
    legacy = {"old": {"requestIdentity": content_identity(request), "targetIdentity": content_identity(target),
                      "result": {"status": "accepted"}}}
    path.write_bytes(canonical_bytes(legacy))
    original = path.read_bytes()
    ledger = ReplayLedger(path)

    assert ledger.history("old").request is None
    assert ledger.lookup("old", request, target).result == {"status": "accepted"}
    assert ledger.record("old", request, target, {"status": "changed"}).result == {"status": "accepted"}
    assert path.read_bytes() == original


def test_history_rejects_a_corrupt_retained_request(tmp_path: Path):
    path = tmp_path / "replays.json"
    request = {"version": "chrona/command/v0.4", "commandId": "c1"}
    target = {"id": "actual", "revision": {"token": "r1"}}
    ledger = ReplayLedger(path)
    ledger.record("c1", request, target, {"status": "accepted"})
    row = json.loads(path.read_text(encoding="utf-8"))
    row["c1"]["request"]["commandId"] = "tampered"
    path.write_text(json.dumps(row), encoding="utf-8")

    with pytest.raises(ValueError, match="E_COMMAND_HISTORY_UNAVAILABLE"):
        ledger.history("c1")
