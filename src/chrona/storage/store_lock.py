"""Canonical-root, reentrant coordination for cooperating local Store writers."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import threading
from typing import Iterator

from chrona.storage.file_lock import lock_file, unlock_file


class StoreLockError(OSError):
    """The Store write lock could not be opened or acquired."""

    diagnostic_id = "E_STORE_LOCK_UNAVAILABLE"

    def __init__(self, root: Path, error: OSError):
        self.root = root
        self.detail = (f"could not acquire Store write lock at {root / '.chrona-store.lock'}; "
                       f"check directory permissions and retry ({error})")
        super().__init__(self.detail)


@dataclass
class _RootLock:
    mutex: threading.RLock
    depth: int = 0
    handle: object | None = None


_states_guard = threading.Lock()
_states: dict[str, _RootLock] = {}


def _after_fork_child() -> None:
    """Discard inherited thread ownership and OS handles in a forked child."""
    global _states_guard, _states
    for state in _states.values():
        handle = state.handle
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
    _states_guard = threading.Lock()
    _states = {}


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork_child)


def _root_lock(root: Path) -> tuple[Path, _RootLock]:
    resolved = Path(root).resolve(strict=False)
    identity = os.path.normcase(os.fspath(resolved))
    with _states_guard:
        state = _states.get(identity)
        if state is None:
            state = _RootLock(threading.RLock())
            _states[identity] = state
    return resolved, state


@contextmanager
def store_write_lock(root: Path) -> Iterator[None]:
    """Exclude other threads and processes writing the same canonical Store root.

    The root's persistent lock file is never removed or replaced. Reentrant
    acquisitions by the owning thread share the outer OS lock and file handle.
    """
    try:
        resolved, state = _root_lock(Path(root))
        state.mutex.acquire()
    except OSError as error:
        raise StoreLockError(Path(root), error) from error

    outer = state.depth == 0
    if outer:
        handle = None
        try:
            resolved.mkdir(parents=True, exist_ok=True)
            handle = (resolved / ".chrona-store.lock").open("a+b")
            lock_file(handle)
        except BaseException as error:
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
            state.mutex.release()
            if isinstance(error, OSError):
                raise StoreLockError(resolved, error) from error
            raise
        state.handle = handle
    state.depth += 1
    try:
        yield
    finally:
        state.depth -= 1
        if state.depth == 0:
            handle = state.handle
            state.handle = None
            try:
                if handle is not None:
                    unlock_file(handle)
            finally:
                try:
                    if handle is not None:
                        handle.close()
                finally:
                    state.mutex.release()
        else:
            state.mutex.release()
