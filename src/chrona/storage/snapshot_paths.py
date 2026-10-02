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
        raise ValueError(f"E_IMMUTABLE_SNAPSHOT_REQUIRED: revision token {token!r} is empty or names the mutable Draft; an immutable revision is required")
    component = quote(token, safe="-_").replace(".", "%2E")
    return root / f"revision-{component}"
