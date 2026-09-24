"""Filesystem-only codec for opaque immutable snapshot revision tokens."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


def snapshot_directory(root: Path, token: str) -> Path:
    """Return the one safe snapshot directory corresponding to ``token``.

    Tokens remain opaque protocol values. Percent encoding is injective and is
    deliberately applied only at the local filesystem adapter boundary.
    """
    if not isinstance(token, str) or not token or token in {"Draft", "draft"}:
        raise ValueError("E_IMMUTABLE_SNAPSHOT_REQUIRED")
    component = quote(token, safe="-_").replace(".", "%2E")
    return root / f"revision-{component}"
