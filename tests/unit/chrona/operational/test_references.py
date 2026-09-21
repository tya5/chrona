import json
from pathlib import Path

import pytest

from chrona.operational.references import ReplayLedger, verify_reference


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
    request = {"version": "chrona/command/v0.2", "commandId": "c1"}
    target = {"id": "actual", "revision": {"token": "r1"}}
    ledger = ReplayLedger(tmp_path / "replays.json")
    first = ledger.record("c1", request, target, {"status": "accepted"})
    replay = ReplayLedger(tmp_path / "replays.json").lookup("c1", request, target)
    assert replay == first
    with pytest.raises(ValueError, match="E_COMMAND_ID_REUSE"):
        ledger.lookup("c1", request | {"reason": "different"}, target)
