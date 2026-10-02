"""Every automation-result row carries a message, and the owners name the offending value (#829 S3)."""
import json
from pathlib import Path

import pytest

from chrona.operational.baselines import compare_baseline
from chrona.operational.command_engine import apply_actual_command, check_command
from chrona.operational.references import ReplayLedger, verify_reference
from chrona.operational.resources import diagnostic_row, stamp_automation_result
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.usecases.diagnostic_messages import is_bare


def _result(rows):
    return {"version": "chrona/automation-result/v0.2", "operation": "command-check", "status": "rejected",
            "requestContentIdentity": "sha256:" + "0" * 64, "inputs": [], "diagnostics": rows, "artifacts": []}


def test_the_builder_gives_every_row_a_message_that_is_not_the_code():
    rows = stamp_automation_result(_result([{"code": "E_X_NEW"}, {"code": "E_Y", "message": "E_Y"},
                                            {"code": "E_Z", "message": "the value 7 is out of range"}]))["diagnostics"]
    assert [row["code"] for row in rows] == ["E_X_NEW", "E_Y", "E_Z"]
    assert all(not is_bare(row["code"], row["message"]) for row in rows)
    assert rows[2]["message"] == "the value 7 is out of range"


def test_an_accepted_result_stays_without_diagnostics():
    accepted = _result([]) | {"status": "accepted"}
    assert stamp_automation_result(accepted)["diagnostics"] == []


@pytest.mark.parametrize("text,row", [
    ("E_X", {"code": "E_X"}),
    ("E_X: the detail", {"code": "E_X", "message": "the detail"}),
    ("E_X:no space", {"code": "E_X", "message": "no space"}),
    ("not a code", {"code": "E_AUTOMATION_FAILURE", "message": "not a code"}),
])
def test_diagnostic_row_splits_the_leading_code_from_the_detail(text, row):
    assert diagnostic_row(text) == row


def _store(tmp_path: Path, identity: str = "s") -> ConfiguredStoreReader:
    return ConfiguredStoreReader({"stores": [{"provider": "local", "identity": identity, "root": str(tmp_path)}]})


def _reference(**overrides):
    base = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "project.yaml",
            "revision": {"token": "r1"}}
    return base | overrides


def test_a_store_that_is_declared_twice_or_not_at_all_is_named(tmp_path: Path):
    with pytest.raises(ValueError, match=r"E_STORE_CONFIG: Store local/s is declared more than once"):
        ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "s", "root": str(tmp_path)}] * 2})
    with pytest.raises(ValueError, match=r"E_AUTOMATION_TARGET_CLOSURE: .*no Store local/other"):
        _store(tmp_path).read(_reference(store={"provider": "local", "identity": "other"}))


def test_verify_reference_names_what_is_wrong_with_the_reference(tmp_path: Path):
    reader = _store(tmp_path)
    def failure(reference, **kwargs):
        with pytest.raises(ValueError) as caught:
            verify_reference(reader, reference, **kwargs)
        return str(caught.value)
    assert "a reference must be a mapping" in failure("nope")
    assert "is missing address, store" in failure({"id": "p", "kind": "project", "revision": {"token": "r"}})
    assert "has no revision.token" in failure(_reference(revision={}))
    assert "expected a actual-set reference, got project 'p'" in failure(_reference(), kind="actual-set")
    assert "project 'p' cannot be read" in failure(_reference())


def test_a_wrong_base_revision_and_an_unsupported_type_are_named(tmp_path: Path):
    reader = _MemoryReader({"id": "p", "kind": "project", "project": {"id": "p"}})
    target = _reference(contentIdentity=reader.identity)
    stale = check_command(reader, {"type": "captureSnapshot", "target": target, "baseRevision": "r0"})
    assert stale["diagnostics"][0]["code"] == "E_AUTOMATION_BASE_REVISION"
    assert "'r0'" in stale["diagnostics"][0]["message"] and "'r1'" in stale["diagnostics"][0]["message"]
    wrong_type = check_command(reader, {"type": "frobnicate", "target": target, "baseRevision": "r1"})
    row = wrong_type["diagnostics"][0]
    assert row["code"] == "E_AUTOMATION_OPERATION_UNSUPPORTED"
    assert "'frobnicate'" in row["message"] and "captureSnapshot" in row["message"]


class _MemoryReader:
    def __init__(self, document):
        from hashlib import sha256
        self.payload = json.dumps(document).encode()
        self.identity = "sha256:" + sha256(self.payload).hexdigest()
        self.roots = {}

    def read(self, reference):
        return self.payload


def test_a_reused_command_id_names_the_id(tmp_path: Path):
    ledger = ReplayLedger(tmp_path / "ledger.json")
    ledger.record("c1", {"a": 1}, {"t": 1}, {"status": "accepted"})
    with pytest.raises(ValueError, match=r"E_COMMAND_ID_REUSE: command id 'c1'"):
        ledger.lookup("c1", {"a": 2}, {"t": 1})


def test_the_baseline_comparison_keeps_the_detail_of_a_failed_reference(tmp_path: Path):
    reader = _MemoryReader({"id": "q2", "kind": "snapshot-ref", "body": {}})
    reference = _reference(id="q2", kind="snapshot-ref", contentIdentity=reader.identity)
    result = compare_baseline(reader, reference, reader, reference)
    row = result["diagnostics"][0]
    assert row["code"] == "E_BASELINE_REFERENCE" and "'q2'" in row["message"] and "body.project" in row["message"]
