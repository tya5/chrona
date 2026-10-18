"""Neutral value exchanged between a use case and a file transaction owner."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PreparedFileMutation:
    """Complete candidate bytes and opaque result prepared by an application use case.

    ``result_revision`` is the next content identity, or ``None`` for a logical
    refusal. A successful no-op has the same revision as its input and is still
    eligible for a durable idempotency receipt.
    """

    files: Mapping[str, bytes]
    result_revision: str | None
    result: dict[str, Any]
