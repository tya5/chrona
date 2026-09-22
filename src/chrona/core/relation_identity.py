"""Canonical identities for ordered Project dependency declarations."""
from __future__ import annotations

from typing import Mapping, Any


def relation_identity(index: int, relation: Mapping[str, Any]) -> str:
    """Return a unique deterministic identity without requiring an author-supplied id."""
    declared = relation.get("id")
    return f"relation:{index}:{declared}" if isinstance(declared, str) and declared else f"relation:{index}"
