"""Cross-process coverage for durable authoring-command receipts."""
from __future__ import annotations

import json
from hashlib import sha256
import multiprocessing
import os
from pathlib import Path

import yaml

from chrona.operational.authoring_commands import _receipt_directory
from chrona.operational.resources import content_identity


def _apply_authoring_process(path: str, command: dict, ready, start, output) -> None:
    ready.set()
    if not start.wait(10):
        raise RuntimeError("test coordinator did not release authoring process")
    from chrona.operational.authoring_commands import transact_authoring_command
    from chrona.usecases.authoring_commands import apply_authoring_command

    output.put(apply_authoring_command(Path(path), command, transact=transact_authoring_command))


def test_same_authoring_command_process_race_publishes_one_revision_and_receipt(tmp_path):
    workspace = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {
            "project": {"id": "project", "tasks": [
                {"id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}},
            ]},
            "presentation": {"mode": "guided", "binding": {
                "preset": {"id": "starter", "version": "1", "path": "preset.yaml"},
            }},
        },
    }
    path = tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")
    command = {
        "version": "chrona/authoring-command/v0.1", "commandId": "cross-process-same-command",
        "type": "setWorkspaceTask", "target": {"kind": "authoring-workspace", "path": path.name},
        "baseRevision": content_identity(workspace),
        "payload": {"task": {"id": "one", "title": "Changed", "planned": {
            "start": "2026-01-03", "finish": "2026-01-04",
        }}},
    }

    context = multiprocessing.get_context("spawn")
    start = context.Event()
    ready = [context.Event(), context.Event()]
    output = context.Queue()
    processes = [context.Process(target=_apply_authoring_process,
                                 args=(str(path), command, ready[index], start, output))
                 for index in range(2)]
    for process in processes:
        process.start()
    try:
        assert all(event.wait(10) for event in ready)
        start.set()
        for process in processes:
            process.join(15)
            assert not process.is_alive(), "authoring child process did not finish"
            assert process.exitcode == 0
    finally:
        start.set()
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(2)

    results = [output.get(timeout=5) for _ in range(2)]
    # The process that lost the race replays the winner's result and says so (#1892 row 3).
    assert sorted("replayed" in item for item in results) == [False, True]
    fresh, = [item for item in results if "replayed" not in item]
    replay, = [item for item in results if "replayed" in item]
    assert replay == fresh | {"replayed": True, "revisionIsCurrent": True}
    results = [fresh, fresh]
    assert results[0]["status"] == "accepted"
    stored = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert stored["body"]["project"]["tasks"][0]["title"] == "Changed"
    canonical = path.resolve()
    scope = "sha256:" + sha256(os.path.normcase(str(canonical)).encode("utf-8")).hexdigest()
    receipt_dir = _receipt_directory(canonical, scope)
    receipts = list(receipt_dir.glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["commandId"] == command["commandId"]
    assert receipt["result"] == results[0]


def test_different_authoring_commands_from_one_base_serialize_to_one_winner(tmp_path):
    workspace = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {
            "project": {"id": "project", "tasks": [
                {"id": "one", "title": "One", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}},
            ]},
            "presentation": {"mode": "guided", "binding": {
                "preset": {"id": "starter", "version": "1", "path": "preset.yaml"},
            }},
        },
    }
    path = tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")
    commands = [
        {
            "version": "chrona/authoring-command/v0.1", "commandId": f"race-{index}",
            "type": "setWorkspaceTask", "target": {"kind": "authoring-workspace", "path": path.name},
            "baseRevision": content_identity(workspace),
            "payload": {"task": {"id": "one", "title": f"Winner {index}", "planned": {
                "start": "2026-01-03", "finish": "2026-01-04",
            }}},
        }
        for index in range(2)
    ]
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    ready = [context.Event(), context.Event()]
    output = context.Queue()
    processes = [context.Process(target=_apply_authoring_process,
                                 args=(str(path), commands[index], ready[index], start, output))
                 for index in range(2)]
    for process in processes:
        process.start()
    try:
        assert all(event.wait(10) for event in ready)
        start.set()
        for process in processes:
            process.join(15)
            assert not process.is_alive(), "authoring child process did not finish"
            assert process.exitcode == 0
    finally:
        start.set()
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(2)

    results = [output.get(timeout=5) for _ in range(2)]
    assert sorted(result["status"] for result in results) == ["accepted", "rejected"]
    rejected = next(result for result in results if result["status"] == "rejected")
    assert rejected["diagnostics"][0]["code"] == "E_AUTHORING_BASE_REVISION"
    winner = next(result for result in results if result["status"] == "accepted")
    assert winner["resultRevision"] != content_identity(workspace)
    stored = yaml.safe_load(path.read_text(encoding="utf-8"))
    accepted_command = next(command for command in commands if command["commandId"] == winner["commandId"])
    assert stored["body"]["project"]["tasks"][0]["title"] == accepted_command["payload"]["task"]["title"]
    canonical = path.resolve()
    scope = "sha256:" + sha256(os.path.normcase(str(canonical)).encode("utf-8")).hexdigest()
    receipts = list(_receipt_directory(canonical, scope).glob("*.json"))
    assert len(receipts) == 1
    assert json.loads(receipts[0].read_text(encoding="utf-8"))["commandId"] == winner["commandId"]
