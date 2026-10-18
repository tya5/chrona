"""Cross-process coverage for the complete #902 Store write transaction."""
from __future__ import annotations

from hashlib import sha256
import json
import multiprocessing
from pathlib import Path

import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.operational.references import ReplayLedger
from chrona.operational.resources import content_identity
from chrona.operational.store_commands import open_store_reader, run_store_command
from chrona.storage.snapshot_paths import snapshot_directory
from tests.support.store_workspace import PROJECT, StoreWorkspace


def _apply_process(config: str, command: dict, ready, start, output) -> None:
    ready.set()
    if not start.wait(10):
        raise RuntimeError("test coordinator did not release command process")
    reader = open_store_reader(config)
    output.put(run_store_command("command-apply", command, reader))


def _record_process(path: str, command_id: str, ready, start) -> None:
    ready.set()
    if not start.wait(10):
        raise RuntimeError("test coordinator did not release ledger process")
    request = {"commandId": command_id, "type": "test"}
    target = {"kind": "actual-set", "id": "actuals"}
    result = {"status": "accepted", "commandId": command_id}
    ReplayLedger(Path(path)).record(command_id, request, target, result)


def _launch_pair(context, target, args, *, timeout=10):
    start = context.Event()
    ready = [context.Event(), context.Event()]
    processes = [context.Process(target=target, args=args(index, ready[index], start))
                 for index in range(2)]
    for process in processes:
        process.start()
    try:
        assert all(event.wait(timeout) for event in ready)
        start.set()
        for process in processes:
            process.join(timeout)
            assert not process.is_alive(), "child process did not finish"
            assert process.exitcode == 0
    finally:
        start.set()
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(2)
    return processes


def test_same_actual_command_race_replays_one_mutation(tmp_path):
    work = StoreWorkspace(tmp_path)
    command = work.intake("same-command", work.batch("batch", finish="2026-01-12"))
    before = work.snapshot()
    context = multiprocessing.get_context("spawn")
    output = context.Queue()

    _launch_pair(context, _apply_process,
                 lambda _index, ready, start: (str(work.config), command, ready, start, output))
    results = [output.get(timeout=5) for _ in range(2)]
    assert [result["status"] for result in results] == ["accepted", "accepted"]
    assert sum(bool(result.get("replayed")) for result in results) == 1

    revision, actual = LocalActualStore(
        work.store, {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals",
                     "body": {"observations": []}}).read()
    assert revision != work.initial_revision
    assert len(actual["body"]["observations"]) == 1
    assert sum(1 for path in work.store.glob("revision-*/actuals/actuals.yaml")) == 2
    ledger = json.loads((work.store / "command-replays.json").read_text(encoding="utf-8"))
    assert list(ledger) == ["same-command"]
    assert work.snapshot() != before


def test_direct_concurrent_replay_records_do_not_lose_distinct_ids(tmp_path):
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    ready = [context.Event(), context.Event()]
    processes = [context.Process(target=_record_process,
                                 args=(str(tmp_path / "command-replays.json"), f"command-{i}",
                                       ready[i], start)) for i in range(2)]
    for process in processes:
        process.start()
    try:
        assert all(event.wait(5) for event in ready)
        start.set()
        for process in processes:
            process.join(8)
            assert not process.is_alive()
            assert process.exitcode == 0
    finally:
        start.set()
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(2)
    ledger = json.loads((tmp_path / "command-replays.json").read_text(encoding="utf-8"))
    assert set(ledger) == {"command-0", "command-1"}


def _snapshot_fixture(root: Path) -> tuple[Path, Path, dict]:
    input_root, registry_root = root / "input-store", root / "registry-store"
    payload = yaml.safe_dump(PROJECT, sort_keys=True).encode("utf-8")
    project_path = snapshot_directory(input_root, "project-r1") / "project.yaml"
    project_path.parent.mkdir(parents=True)
    project_path.write_bytes(payload)
    config = root / "store-config.yaml"
    config.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [
        {"provider": "local", "identity": "input", "root": "input-store", "integrity": "required"},
        {"provider": "local", "identity": "registry", "root": "registry-store", "integrity": "required"},
    ]}), encoding="utf-8")
    target = {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "input"},
              "address": "project.yaml", "revision": {"token": "project-r1"},
              "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    return config, input_root, {"target": target, "registry_root": registry_root}


def _snapshot_command(command_id: str, snapshot_id: str, target: dict) -> dict:
    return {"version": "chrona/command/v0.3", "commandId": command_id,
            "type": "captureSnapshot", "target": target, "baseRevision": "project-r1",
            "expectedContentIdentity": target["contentIdentity"],
            "payload": {"snapshotId": snapshot_id,
                        "registry": {"provider": "local", "identity": "registry"}}}


def test_snapshot_replay_and_name_race_lock_registry_not_input(tmp_path):
    config, input_root, stores = _snapshot_fixture(tmp_path)
    target = stores["target"]
    registry_root = stores["registry_root"]
    before_input = {p.relative_to(input_root): p.read_bytes()
                    for p in input_root.rglob("*") if p.is_file()}
    context = multiprocessing.get_context("spawn")
    output = context.Queue()

    replay_command = _snapshot_command("snapshot-replay", "replayed", target)
    _launch_pair(context, _apply_process,
                 lambda _index, ready, start: (str(config), replay_command, ready, start, output))
    replay_results = [output.get(timeout=5) for _ in range(2)]
    assert [result["status"] for result in replay_results] == ["accepted", "accepted"]
    assert sum(bool(result.get("replayed")) for result in replay_results) == 1
    replay_path = registry_root / "snapshots" / "replayed.yaml"
    replay_bytes = replay_path.read_bytes()

    collision_commands = (
        _snapshot_command("collision-a", "collision", target),
        _snapshot_command("collision-b", "collision", target),
    )
    _launch_pair(context, _apply_process,
                 lambda index, ready, start: (str(config), collision_commands[index], ready, start, output))
    collision_results = [output.get(timeout=5) for _ in range(2)]
    assert sorted(result["status"] for result in collision_results) == ["accepted", "rejected"]
    assert sum(any(row["code"] == "E_BASELINE_EXISTS" for row in result["diagnostics"])
               for result in collision_results) == 1
    collision_path = registry_root / "snapshots" / "collision.yaml"
    assert collision_path.is_file()
    assert replay_path.read_bytes() == replay_bytes
    assert not list(registry_root.glob("snapshots/.*.tmp"))

    assert (registry_root / ".chrona-store.lock").is_file()
    assert not (input_root / ".chrona-store.lock").exists()
    after_input = {p.relative_to(input_root): p.read_bytes()
                   for p in input_root.rglob("*") if p.is_file()}
    assert after_input == before_input
    ledger = json.loads((registry_root / "command-replays.json").read_text(encoding="utf-8"))
    accepted_collision_identity = next(result["requestContentIdentity"] for result in collision_results
                                       if result["status"] == "accepted")
    accepted_collision_id = next(command["commandId"] for command in collision_commands
                                 if content_identity(command) == accepted_collision_identity)
    assert set(ledger) == {"snapshot-replay", accepted_collision_id}
