from hashlib import sha256
from pathlib import Path
import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.operational.command_engine import apply_actual_command
from chrona.operational.store_config import ConfiguredStoreReader


def _write(root: Path, token: str, address: str, value: dict, kind: str, identifier: str):
    payload = yaml.safe_dump(value, sort_keys=True).encode(); path = root / token / address
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "test"}, "address": address, "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def test_apply_intake_uses_v02_batch_cas_and_replays(tmp_path: Path):
    actual = {"version": "chrona/actual-set/v0.2", "kind": "actual-set", "id": "actuals", "body": {"observations": []}}
    store = LocalActualStore(tmp_path, actual); revision, loaded = store.read()
    payload = (tmp_path / revision / "actuals" / "actuals.yaml").read_bytes()
    target = {"id": "actuals", "kind": "actual-set", "store": {"provider": "local", "identity": "test"}, "address": "actuals/actuals.yaml", "revision": {"token": revision}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    project = {"version": "timeline/v0.1", "project": {"id": "p"}, "extensions": [], "objects": {"firmware": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-01-01"}}}, "relations": []}
    project_ref = _write(tmp_path, "project-r1", "project.yaml", project, "project", "p")
    batch = {"version": "chrona/actual-intake-batch/v0.2", "kind": "actual-intake-batch", "id": "batch", "body": {"source": {"system": "supplier", "contentIdentity": "sha256:" + "a" * 64}, "records": [{"externalKey": "42", "projectObjectId": "firmware", "actual": {"finish": "2026-01-02"}}]}}
    batch_ref = _write(tmp_path, "batch-r1", "batch.yaml", batch, "actual-intake-batch", "batch")
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)}]})
    command = {"version": "chrona/command/v0.2", "commandId": "c1", "type": "applyActualIntakeBatch", "target": target, "baseRevision": revision, "expectedContentIdentity": target["contentIdentity"], "payload": {"batch": batch_ref, "project": project_ref}}
    accepted = apply_actual_command(reader, command)
    assert accepted["status"] == "accepted" and accepted["actualIntake"]["dispositions"] == ["inserted"]
    replay = apply_actual_command(reader, command)
    assert replay["replayed"] is True and replay["resultTarget"] == accepted["resultTarget"]
