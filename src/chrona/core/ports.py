"""Capabilities the core depends on, named where every layer may see them.

A port is the narrow view an inner layer needs of an outer one. Storage supplies
the adapters; nothing here knows how a resource is stored.
"""
from __future__ import annotations

from typing import Any, Protocol


class SnapshotReadError(ValueError):
    """A pinned resource could not be read as declared."""

    def __init__(self, diagnostic_id: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id


class SnapshotReader(Protocol):
    """Read the exact bytes of one immutable, identity-addressed resource."""

    def read(self, reference: dict[str, Any]) -> bytes:  # pragma: no cover - protocol
        ...
