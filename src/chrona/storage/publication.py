"""Exclusive local-file publication with an explicit reservation visibility contract."""
from __future__ import annotations

import os
from pathlib import Path


def publish_exclusive(destination: Path, payload: bytes) -> None:
    """Publish ``payload`` without overwriting an existing destination.

    The destination is exclusively reserved before its completed sibling
    temporary is replaced over it.  This preserves no-overwrite behavior on
    supported filesystems.  During that bounded replacement interval an
    uncoordinated reader can observe the reserved destination as empty; callers
    must therefore treat this as completed-command output, or verify immutable
    content identity and retry a transient concurrent read.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    reserved_destination = False
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        with destination.open("xb"):
            pass
        reserved_destination = True
        temporary.replace(destination)
        reserved_destination = False
    finally:
        temporary.unlink(missing_ok=True)
        if reserved_destination:
            destination.unlink(missing_ok=True)
