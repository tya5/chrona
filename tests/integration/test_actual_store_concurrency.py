"""Independent local Actual writers must not accept the same stale base (#902)."""
from copy import deepcopy
import multiprocessing
from pathlib import Path

from chrona.commands.actual_commands import LocalActualStore


SEED = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "concurrent-proof",
    "body": {"asOf": "2026-10-18", "observations": []},
}


def _writer(root, as_of, ready, release):
    store = LocalActualStore(Path(root), deepcopy(SEED))
    base, candidate = store.read()
    ready.send(("ready", base))
    if not release.wait(30):
        raise RuntimeError("test coordinator did not release writer")
    candidate["body"]["asOf"] = as_of
    written = store.write(base, candidate)
    ready.send(("result", written[0] if written else None))
    ready.close()


def _receive(connection, expected):
    assert connection.poll(30), f"writer did not report {expected}"
    kind, value = connection.recv()
    assert kind == expected
    return value


def _files(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_two_processes_opening_one_base_preserve_first_commit_and_reject_stale_writer(tmp_path):
    seed_revision, _ = LocalActualStore(tmp_path, deepcopy(SEED)).read()
    initial_files = _files(tmp_path)
    context = multiprocessing.get_context("spawn")
    workers = []
    try:
        for as_of in ("2026-10-19", "2026-10-20"):
            receive, send = context.Pipe(duplex=False)
            release = context.Event()
            process = context.Process(target=_writer, args=(str(tmp_path), as_of, send, release))
            process.start()
            send.close()
            workers.append((process, receive, release))
        assert [_receive(receive, "ready") for _, receive, _ in workers] == [seed_revision] * 2

        workers[0][2].set()
        accepted_revision = _receive(workers[0][1], "result")
        assert accepted_revision is not None and accepted_revision != seed_revision
        after_first = _files(tmp_path)
        workers[1][2].set()
        stale_result = _receive(workers[1][1], "result")
        assert stale_result is None, "stale process must not replace the first writer's accepted content"
        assert _files(tmp_path) == after_first  # no new revision, overwritten tip or immutable bytes
        revision, actual = LocalActualStore(tmp_path, deepcopy(SEED)).read()
        assert revision == accepted_revision and actual["body"]["asOf"] == "2026-10-19"
        for path, content in initial_files.items():
            if path.parts[0] != "actual-tips":
                assert (tmp_path / path).read_bytes() == content
    finally:
        for _, _, release in workers:
            release.set()
        for process, receive, _ in workers:
            process.join(10)
            if process.is_alive():
                process.terminate()
                process.join(10)
            receive.close()
        assert all(process.exitcode == 0 for process, _, _ in workers)
