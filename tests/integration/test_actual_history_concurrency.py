"""An Actual inverse and an ordinary write cannot both win the same base."""
from __future__ import annotations

import json
import multiprocessing

from chrona.operational.store_commands import open_store_reader, run_store_command
from chrona.operational.resources import content_identity
from tests.support.store_workspace import StoreWorkspace


def _apply_process(config, command, ready, start, output) -> None:
    ready.set()
    if not start.wait(10):
        raise RuntimeError("test coordinator did not release command process")
    reader = open_store_reader(config)
    output.put(run_store_command("command-apply", command, reader))


def test_same_base_actual_revert_races_an_ordinary_intake_write(tmp_path):
    work = StoreWorkspace(tmp_path)

    origin_command = work.intake("origin-write", work.batch("origin-batch", finish="2026-01-12"))
    origin = run_store_command("command-apply", origin_command, open_store_reader(str(work.config)))
    assert origin["status"] == "accepted"
    shared_target = origin["resultTarget"]

    inverse = {
        "version": "chrona/command/v0.4", "commandId": "racing-revert",
        "type": "revertActualCommand", "target": shared_target,
        "baseRevision": shared_target["revision"]["token"],
        "expectedContentIdentity": shared_target["contentIdentity"],
        "payload": {"commandId": "origin-write"},
    }
    ordinary = work.intake("racing-intake", work.batch("racing-batch", finish="2026-01-19", key="43"),
                           target=shared_target)
    before_revisions = {
        path.relative_to(work.store).as_posix(): path.read_bytes()
        for path in work.store.glob("revision-*/actuals/actuals.yaml")
    }
    assert len(before_revisions) == 2  # seed plus accepted origin

    context = multiprocessing.get_context("spawn")
    start = context.Event()
    ready = [context.Event(), context.Event()]
    output = context.Queue()
    commands = (inverse, ordinary)
    processes = [context.Process(target=_apply_process,
                                 args=(str(work.config), commands[index], ready[index], start, output))
                 for index in range(2)]
    for process in processes:
        process.start()
    try:
        assert all(event.wait(10) for event in ready), "both commands must be staged before releasing the race"
        start.set()
        results = [output.get(timeout=10), output.get(timeout=10)]
        for process in processes:
            process.join(10)
            assert not process.is_alive(), "command process did not finish"
            assert process.exitcode == 0
    finally:
        start.set()
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(2)

    assert sorted(result["status"] for result in results) == ["accepted", "rejected"]
    rejected = next(result for result in results if result["status"] == "rejected")
    assert rejected["diagnostics"]
    assert rejected["diagnostics"][0]["code"] in {"E_AUTOMATION_TARGET_CLOSURE", "E_AUTOMATION_BASE_REVISION"}

    current_tip = work.tip()["token"]
    current_actual = work.actual_reference(current_tip)
    assert current_tip != shared_target["revision"]["token"]
    revision_files = {
        path.relative_to(work.store).as_posix(): path.read_bytes()
        for path in work.store.glob("revision-*/actuals/actuals.yaml")
    }
    assert len(revision_files) == len(before_revisions) + 1
    for path, payload in before_revisions.items():
        assert revision_files[path] == payload, f"an existing immutable revision was overwritten: {path}"
    accepted_result = next(result for result in results if result["status"] == "accepted")
    assert current_actual["contentIdentity"] == accepted_result["resultTarget"]["contentIdentity"]

    ledger = json.loads((work.store / "command-replays.json").read_text(encoding="utf-8"))
    accepted_identity = next(result["requestContentIdentity"] for result in results if result["status"] == "accepted")
    accepted_command_id = next(command["commandId"] for command in commands
                               if content_identity(command) == accepted_identity)
    assert set(ledger) == {"origin-write", accepted_command_id}
