from __future__ import annotations

import errno
import multiprocessing
from pathlib import Path
import sys
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from chrona.storage import file_lock
from chrona.storage.store_lock import StoreLockError, store_write_lock


def _hold_in_child(root: str, acquired, release) -> None:
    with store_write_lock(Path(root)):
        acquired.set()
        if not release.wait(8):
            raise RuntimeError("parent did not release child lock")


def _contend_in_child(root: str, attempting, acquired) -> None:
    attempting.set()
    with store_write_lock(Path(root)):
        acquired.set()


def test_nested_same_thread_acquisition_opens_one_persistent_os_lock(tmp_path, monkeypatch):
    calls = []
    real_lock = file_lock.lock_file
    monkeypatch.setattr("chrona.storage.store_lock.lock_file",
                        lambda handle: (calls.append(handle), real_lock(handle))[1])
    lock_path = tmp_path / ".chrona-store.lock"

    with store_write_lock(tmp_path):
        with store_write_lock(tmp_path / "."):
            assert lock_path.exists()
            assert lock_path.stat().st_size in (0, 1)

    assert len(calls) == 1
    identity = lock_path.stat().st_ino
    with store_write_lock(tmp_path):
        pass
    assert lock_path.stat().st_ino == identity


def test_canonical_root_aliases_share_reentrant_lock_state(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks unavailable: {error}")

    with store_write_lock(root):
        with store_write_lock(alias):
            assert (root / ".chrona-store.lock").exists()
            assert not (alias / ".chrona-store.lock").is_symlink()


def test_other_thread_waits_until_outer_os_lock_is_released(tmp_path):
    entered = Event()
    finished = Event()

    def worker():
        entered.set()
        with store_write_lock(tmp_path):
            finished.set()

    with store_write_lock(tmp_path):
        thread = Thread(target=worker)
        thread.start()
        assert entered.wait(2)
        assert not finished.wait(0.05)
    assert finished.wait(2)
    thread.join(2)
    assert not thread.is_alive()


def test_body_exception_is_unchanged_and_releases_lock(tmp_path):
    failure = OSError(errno.EIO, "body write failed")
    with pytest.raises(OSError) as raised:
        with store_write_lock(tmp_path):
            raise failure
    assert raised.value is failure
    with store_write_lock(tmp_path):
        pass


def test_open_failure_is_typed_as_store_lock_unavailable(tmp_path, monkeypatch):
    real_open = Path.open

    def failing_open(path, *args, **kwargs):
        if path.name == ".chrona-store.lock":
            raise PermissionError(errno.EACCES, "denied", str(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(StoreLockError) as raised:
        with store_write_lock(tmp_path):
            pytest.fail("body must not run if lock acquisition fails")
    assert raised.value.diagnostic_id == "E_STORE_LOCK_UNAVAILABLE"
    assert isinstance(raised.value.__cause__, PermissionError)


def test_os_acquire_failure_is_typed_as_store_lock_unavailable(tmp_path, monkeypatch):
    failure = OSError(errno.EIO, "lock syscall failed")
    monkeypatch.setattr("chrona.storage.store_lock.lock_file",
                        lambda _handle: (_ for _ in ()).throw(failure))
    with pytest.raises(StoreLockError) as raised:
        with store_write_lock(tmp_path):
            pytest.fail("body must not run if lock acquisition fails")
    assert raised.value.diagnostic_id == "E_STORE_LOCK_UNAVAILABLE"
    assert raised.value.__cause__ is failure


def test_interrupted_acquisition_releases_handle_and_thread_mutex(tmp_path, monkeypatch):
    failure = KeyboardInterrupt()
    monkeypatch.setattr("chrona.storage.store_lock.lock_file",
                        lambda _handle: (_ for _ in ()).throw(failure))
    with pytest.raises(KeyboardInterrupt) as raised:
        with store_write_lock(tmp_path):
            pytest.fail("body must not run after interrupted acquisition")
    assert raised.value is failure

    monkeypatch.undo()
    acquired = Event()

    def retry():
        with store_write_lock(tmp_path):
            acquired.set()

    thread = Thread(target=retry)
    thread.start()
    assert acquired.wait(2)
    thread.join(2)
    assert not thread.is_alive()


def test_unlock_oserror_is_not_reclassified_and_file_handle_still_closes(tmp_path, monkeypatch):
    failure = OSError(errno.EIO, "unlock syscall failed")
    monkeypatch.setattr("chrona.storage.store_lock.unlock_file",
                        lambda _handle: (_ for _ in ()).throw(failure))
    with pytest.raises(OSError) as raised:
        with store_write_lock(tmp_path):
            pass
    assert raised.value is failure
    monkeypatch.undo()
    with store_write_lock(tmp_path):
        pass


def test_processes_exclude_one_another_with_the_persistent_os_lock(tmp_path):
    context = multiprocessing.get_context("spawn")
    acquired = context.Event()
    release = context.Event()
    attempting = context.Event()
    second_acquired = context.Event()
    holder = context.Process(target=_hold_in_child,
                             args=(str(tmp_path), acquired, release))
    contender = context.Process(target=_contend_in_child,
                                args=(str(tmp_path), attempting, second_acquired))
    holder.start()
    try:
        assert acquired.wait(5)
        contender.start()
        assert attempting.wait(5)
        assert not second_acquired.wait(0.2)
        release.set()
        assert second_acquired.wait(5)
    finally:
        release.set()
        if contender.pid is not None:
            contender.join(5)
            if contender.is_alive():
                contender.terminate()
                contender.join(2)
        holder.join(5)
        if holder.is_alive():
            holder.terminate()
            holder.join(2)
    assert holder.exitcode == 0
    assert contender.exitcode == 0


def test_forked_child_does_not_inherit_reentrant_owner_state(tmp_path):
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("fork start method unavailable")
    context = multiprocessing.get_context("fork")
    attempting = context.Event()
    acquired = context.Event()
    child = context.Process(target=_contend_in_child,
                            args=(str(tmp_path), attempting, acquired))
    try:
        with store_write_lock(tmp_path):
            child.start()
            assert attempting.wait(3)
            assert not acquired.wait(0.1)
        assert acquired.wait(3)
    finally:
        if child.pid is not None:
            child.join(3)
            if child.is_alive():
                child.terminate()
                child.join(2)
    assert child.exitcode == 0


def test_file_lock_uses_lazy_windows_adapter_without_fcntl(tmp_path, monkeypatch):
    calls = []
    fake = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2,
                           locking=lambda descriptor, mode, length: calls.append((descriptor, mode, length)))
    monkeypatch.setattr(file_lock.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    lock = tmp_path / "lock"
    with lock.open("a+b") as handle:
        file_lock.lock_file(handle)
        file_lock.unlock_file(handle)
    assert [mode for _, mode, _ in calls] == [fake.LK_LOCK, fake.LK_UNLCK]
