"""Small cross-platform advisory file-lock primitives shared by local writers."""
from __future__ import annotations

import os
from typing import Any


def lock_file(handle: Any) -> None:
    """Acquire an exclusive one-byte advisory lock on an open binary file."""
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        if not handle.read(1):
            handle.seek(0)
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def unlock_file(handle: Any) -> None:
    """Release an exclusive lock previously acquired by :func:`lock_file`."""
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
