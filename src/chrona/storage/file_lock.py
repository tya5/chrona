"""Small cross-platform file-lock primitives shared by local writers."""
from __future__ import annotations

import os
from typing import Any


def lock_file(handle: Any) -> None:
    """Acquire the platform's exclusive lock on an open binary file."""
    if os.name == "nt":
        import msvcrt

        # Windows permits locking past EOF. Pre-lock content access would fail
        # when another handle already owns this mandatory byte range.
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
