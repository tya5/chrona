"""The engine Store lock covers replay lookup through durable replay recording."""
from __future__ import annotations

from contextlib import contextmanager
import json
import multiprocessing

from chrona.commands.actual_commands import LocalActualStore
from chrona.operational.store_commands import open_store_reader, run_store_command
from tests.support.store_workspace import StoreWorkspace


def _transaction_worker(config, command, role, at_record, release_record,
                        lock_attempt, lookup_entered, output):
    from chrona.operational import command_engine, references

    reader = open_store_reader(config)
    original_record = references.ReplayLedger.record
    original_lookup = references.ReplayLedger.lookup
    if role == "writer":
        def blocked_record(self, *args, **kwargs):
            at_record.set()
            if not release_record.wait(10):
                raise RuntimeError("test coordinator did not release replay recording")
            return original_record(self, *args, **kwargs)

        references.ReplayLedger.record = blocked_record
    else:
        original_lock = command_engine.store_write_lock

        @contextmanager
        def observed_lock(root):
            lock_attempt.set()
            with original_lock(root):
                yield

        def observed_lookup(self, *args, **kwargs):
            lookup_entered.set()
            return original_lookup(self, *args, **kwargs)

        command_engine.store_write_lock = observed_lock
        references.ReplayLedger.lookup = observed_lookup
    output.put(run_store_command("command-apply", command, reader))


def test_engine_lock_keeps_competitor_out_until_replay_is_recorded(tmp_path):
    work = StoreWorkspace(tmp_path)
    command = work.intake("span-command", work.batch("span-batch", finish="2026-01-12"))
    context = multiprocessing.get_context("spawn")
    at_record, release_record = context.Event(), context.Event()
    lock_attempt, lookup_entered = context.Event(), context.Event()
    output = context.Queue()
    writer = context.Process(target=_transaction_worker,
        args=(str(work.config), command, "writer", at_record, release_record,
              lock_attempt, lookup_entered, output))
    competitor = context.Process(target=_transaction_worker,
        args=(str(work.config), command, "competitor", at_record, release_record,
              lock_attempt, lookup_entered, output))
    writer.start()
    try:
        assert at_record.wait(10), "writer did not reach replay recording after publication"
        competitor.start()
        assert lock_attempt.wait(5), "competitor did not attempt the engine transaction lock"
        assert not lookup_entered.wait(0.2), "competitor entered replay lookup before writer recorded"
        release_record.set()
        results = [output.get(timeout=10), output.get(timeout=10)]
        for process in (writer, competitor):
            process.join(10)
            assert not process.is_alive(), "command process did not finish"
            assert process.exitcode == 0
    finally:
        release_record.set()
        for process in (writer, competitor):
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(2)

    assert [result["status"] for result in results] == ["accepted", "accepted"]
    assert sum(bool(result.get("replayed")) for result in results) == 1
    revision, actual = LocalActualStore(
        work.store, {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals",
                     "body": {"observations": []}}).read()
    assert revision != work.initial_revision
    assert len(actual["body"]["observations"]) == 1
    ledger = json.loads((work.store / "command-replays.json").read_text(encoding="utf-8"))
    assert list(ledger) == ["span-command"]
