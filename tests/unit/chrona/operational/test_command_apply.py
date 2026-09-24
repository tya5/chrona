from hashlib import sha256
from pathlib import Path
import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.operational.command_engine import apply_actual_command
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.storage.snapshot_paths import snapshot_directory


def _write(root: Path, token: str, address: str, value: dict, kind: str, identifier: str):
    payload = yaml.safe_dump(value, sort_keys=True).encode(); path = snapshot_directory(root, token) / address
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "test"}, "address": address, "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def test_apply_intake_uses_v02_batch_cas_and_replays(tmp_path: Path):
    actual = {"version": "chrona/actual-set/v0.2", "kind": "actual-set", "id": "actuals", "body": {"observations": []}}
    store = LocalActualStore(tmp_path, actual); revision, loaded = store.read()
    payload = (snapshot_directory(tmp_path, revision) / "actuals" / "actuals.yaml").read_bytes()
    target = {"id": "actuals", "kind": "actual-set", "store": {"provider": "local", "identity": "test"}, "address": "actuals/actuals.yaml", "revision": {"token": revision}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    project = {"version": "timeline/v0.6", "project": {"id": "p"}, "extensions": [], "objects": {"firmware": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-01-01"}}}, "relations": []}
    project_ref = _write(tmp_path, "project-r1", "project.yaml", project, "project", "p")
    batch = {"version": "chrona/actual-intake-batch/v0.2", "kind": "actual-intake-batch", "id": "batch", "body": {"source": {"system": "supplier", "contentIdentity": "sha256:" + "a" * 64}, "records": [{"externalKey": "42", "projectObjectId": "firmware", "actual": {"finish": "2026-01-02"}}]}}
    batch_ref = _write(tmp_path, "batch-r1", "batch.yaml", batch, "actual-intake-batch", "batch")
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)}]})
    command = {"version": "chrona/command/v0.2", "commandId": "c1", "type": "applyActualIntakeBatch", "target": target, "baseRevision": revision, "expectedContentIdentity": target["contentIdentity"], "payload": {"batch": batch_ref, "project": project_ref}}
    accepted = apply_actual_command(reader, command)
    assert accepted["status"] == "accepted" and accepted["actualIntake"]["dispositions"] == ["inserted"]
    replay = apply_actual_command(reader, command)
    assert replay["replayed"] is True and replay["resultTarget"] == accepted["resultTarget"]


def test_apply_capture_publishes_named_baseline(tmp_path: Path):
    project = {"version": "timeline/v0.6", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    target = _write(tmp_path, "project-r1", "project.yaml", project, "project", "p")
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)}]})
    command = {"version": "chrona/command/v0.2", "commandId": "capture-1", "type": "captureSnapshot", "target": target, "baseRevision": "project-r1", "expectedContentIdentity": target["contentIdentity"], "payload": {"snapshotId": "q2", "registry": {"provider": "local", "identity": "test"}}}
    accepted = apply_actual_command(reader, command)
    assert accepted["status"] == "accepted"
    assert reader.read(accepted["resultTarget"])
    replay = apply_actual_command(reader, command)
    assert replay["replayed"] is True and replay["resultTarget"] == accepted["resultTarget"]


def test_apply_capture_rejects_different_command_for_existing_baseline(tmp_path: Path):
    project = {"version": "timeline/v0.6", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    target = _write(tmp_path, "project-r1", "project.yaml", project, "project", "p")
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)}]})
    command = {"version": "chrona/command/v0.2", "commandId": "capture-1", "type": "captureSnapshot", "target": target, "baseRevision": "project-r1", "expectedContentIdentity": target["contentIdentity"], "payload": {"snapshotId": "q2", "registry": {"provider": "local", "identity": "test"}}}
    assert apply_actual_command(reader, command)["status"] == "accepted"
    rejected = apply_actual_command(reader, command | {"commandId": "capture-2"})
    assert rejected["status"] == "rejected"
    assert rejected["diagnostics"] == [{"code": "E_BASELINE_EXISTS"}]
