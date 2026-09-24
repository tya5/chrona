"""Capabilities the core depends on, named where every layer may see them.

A port is the narrow view an inner layer needs of an outer one. Storage supplies
the adapters; nothing here knows how a resource is stored.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Protocol, Sequence

from chrona.core.diagnostics import Diagnostic


class SnapshotReadError(ValueError):
    """A pinned resource could not be read as declared."""

    def __init__(self, diagnostic_id: str, detail: str = ""):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail


class SnapshotReader(Protocol):
    """Read the exact bytes of one immutable, identity-addressed resource."""

    def read(self, reference: dict[str, Any]) -> bytes:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class ScheduleOutcome:
    """The semantic scheduling result a use case needs, independent of an algorithm."""

    placements: Mapping[str, Mapping[str, date]]
    diagnostics: Sequence[Diagnostic]
    analysis: Any | None = None

    @property
    def ok(self) -> bool:
        return not self.diagnostics


class Scheduler(Protocol):
    def schedule(self, project: Mapping[str, Any], *, extension_diagnostics: Sequence[Diagnostic] = ()) -> ScheduleOutcome:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class RenderArtifact:
    """Opaque bytes emitted by one declared presentation target."""

    target_kind: str
    media_type: str
    content: bytes
    adapter_identity: str


class Renderer(Protocol):
    target_kind: str

    def render(self, surface: object, *, viewport: tuple[float, float]) -> RenderArtifact:  # pragma: no cover - protocol
        ...
