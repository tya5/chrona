"""command-request v0.3, automation-result v0.2 and snapshot-ref v0.3 on the strict `storeAddress` (#710, slice S-C).

Command Request v0.2 was retired by #731 (C3); the other two predecessors stay readable until their own slices. Writers
emit the successor, except where the content still carries a legacy loose Store address, which a v0.3 document would not
be allowed to hold. Every verdict is decided from data.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.operational.command_engine import apply_actual_command, check_command
from chrona.operational.resources import (
    COMMAND_SCHEMAS, OperationalResourceError, command_schema_name, parse_command, stamp_automation_result,
)
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.storage.snapshots import LocalBaselineRegistry, snapshot_ref_resource


def _reference(address: str = "projects/main.yaml") -> dict:
    return {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "test"}, "address": address,
            "revision": {"token": "project-r1"}, "contentIdentity": "sha256:" + "a" * 64}


def _command(version: str, address: str = "project.yaml", snapshot_id: str = "q2") -> str:
    return yaml.safe_dump({"version": version, "commandId": "c1", "type": "captureSnapshot", "target": _reference(address),
                           "baseRevision": "project-r1", "payload": {"snapshotId": snapshot_id,
                                                                      "registry": {"provider": "local", "identity": "test"}}})


def test_the_command_ingress_names_the_schema_of_the_declared_version():
    assert set(COMMAND_SCHEMAS) == {"chrona/command/v0.3"}
    assert command_schema_name(_command("chrona/command/v0.3")) == "command-request-v0.3.schema.yaml"
    for payload in ("version: chrona/command/v0.9\n", "- not a mapping\n", "{{{", "version: 5\n", _command("chrona/command/v0.2")):
        assert command_schema_name(payload) == COMMAND_SCHEMAS["chrona/command/v0.3"]


def test_a_retired_v0_2_command_is_refused_and_v0_3_refuses_a_loose_address():
    with pytest.raises(OperationalResourceError, match="E_OPERATIONAL_SCHEMA") as retired:
        parse_command(_command("chrona/command/v0.2"))
    assert "/version" in str(retired.value)
    with pytest.raises(OperationalResourceError, match="E_OPERATIONAL_SCHEMA"):
        parse_command(_command("chrona/command/v0.3", address="my projects/main.yaml"))
    assert parse_command(_command("chrona/command/v0.3"))["version"] == "chrona/command/v0.3"


@pytest.mark.parametrize("snapshot_id", ["..\\..\\x", "a/b", ".", "..", "...", "a\x00b", "a\nb", "a\n", "C:x", "a b", "é", ""])
def test_the_v0_3_snapshot_id_is_one_strict_segment(snapshot_id):
    with pytest.raises(OperationalResourceError, match="E_OPERATIONAL_SCHEMA"):
        parse_command(_command("chrona/command/v0.3", snapshot_id=snapshot_id))


@pytest.mark.parametrize("snapshot_id", ["q2", "baseline-2027-06", "A_b.c-1", ".hidden", "a..b"])
def test_a_legitimate_v0_3_snapshot_id_is_accepted(snapshot_id):
    assert parse_command(_command("chrona/command/v0.3", snapshot_id=snapshot_id))["payload"]["snapshotId"] == snapshot_id


def _result(address: str) -> dict:
    return {"version": "chrona/automation-result/v0.1", "operation": "command-check", "status": "accepted",
            "requestContentIdentity": "sha256:" + "d" * 64, "inputs": [_reference(address)], "diagnostics": [], "artifacts": []}


def test_a_result_names_the_newest_contract_its_content_satisfies():
    assert stamp_automation_result(_result("projects/main.yaml"))["version"] == "chrona/automation-result/v0.2"
    loose = stamp_automation_result(_result("my projects/main.yaml"))
    assert loose["version"] == "chrona/automation-result/v0.1", "a loose legacy address must not claim the strict contract"
    broken = _result("projects/main.yaml") | {"inputs": []}
    assert stamp_automation_result(broken)["version"] == "chrona/automation-result/v0.1", "content valid under neither stays as built"


def test_a_snapshot_ref_is_v0_3_unless_its_project_reference_is_a_legacy_loose_address():
    assert snapshot_ref_resource("q2", _reference())["version"] == "chrona/snapshot-ref/v0.3"
    assert snapshot_ref_resource("q2", _reference("my projects/main.yaml"))["version"] == "chrona/snapshot-ref/v0.2"


def test_both_snapshot_ref_versions_parse_and_v0_2_keeps_its_loose_address():
    identity = ClosureIdentity("snapshot-ref", "q2", "draft", "sha256:" + "0" * 64)
    v3 = snapshot_ref_resource("q2", _reference())
    assert parse_contract(identity, deepcopy(v3)).version == "chrona/snapshot-ref/v0.3"
    loose = snapshot_ref_resource("q2", _reference("my projects/main.yaml"))
    assert parse_contract(identity, deepcopy(loose)).version == "chrona/snapshot-ref/v0.2"
    with pytest.raises(Exception):
        parse_contract(identity, {**loose, "version": "chrona/snapshot-ref/v0.3"})


def test_the_registry_publishes_the_successor_and_still_reads_a_stored_predecessor(tmp_path: Path):
    registry = LocalBaselineRegistry(tmp_path, "test")
    published = registry.publish("q2", _reference())
    assert yaml.safe_load(registry.read(published))["version"] == "chrona/snapshot-ref/v0.3"
    legacy = registry.publish("q3", _reference("my projects/main.yaml"))
    assert yaml.safe_load(registry.read(legacy))["version"] == "chrona/snapshot-ref/v0.2"
    # An immutable v0.2 baseline already in a Store is read byte for byte; the registry never rewrites it.
    payload = yaml.safe_dump({"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "q1",
                              "body": {"project": _reference()}}, sort_keys=True).encode()
    (tmp_path / "snapshots").mkdir(exist_ok=True)
    (tmp_path / "snapshots" / "q1.yaml").write_bytes(payload)
    stored = {"id": "q1", "kind": "snapshot-ref", "store": {"provider": "local", "identity": "test"}, "address": "snapshots/q1.yaml",
              "revision": {"token": "baseline:" + sha256(payload).hexdigest()}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    assert registry.read(stored) == payload


def _store(tmp_path: Path):
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    payload = yaml.safe_dump(project, sort_keys=True).encode()
    path = snapshot_directory(tmp_path, "project-r1") / "project.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    target = _reference("project.yaml") | {"contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)}]})
    return reader, target


@pytest.mark.parametrize(("version", "result_version", "baseline_version"), [
    ("chrona/command/v0.3", "chrona/automation-result/v0.2", "chrona/snapshot-ref/v0.3"),
])
def test_capture_through_the_engine_emits_the_successor_contracts(tmp_path, version, result_version, baseline_version):
    reader, target = _store(tmp_path)
    command = {"version": version, "commandId": "c1", "type": "captureSnapshot", "target": target, "baseRevision": "project-r1",
               "expectedContentIdentity": target["contentIdentity"],
               "payload": {"snapshotId": "q2", "registry": {"provider": "local", "identity": "test"}}}
    checked = check_command(reader, command)
    assert checked["status"] == "accepted" and checked["version"] == result_version
    accepted = apply_actual_command(reader, command)
    assert accepted["status"] == "accepted" and accepted["version"] == result_version
    assert yaml.safe_load(reader.read(accepted["resultTarget"]))["version"] == baseline_version
    replay = apply_actual_command(reader, command)
    assert replay["replayed"] is True and replay["version"] == result_version, "a replay returns the recorded result"
