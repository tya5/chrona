"""Ephemeral render observations; never an input to artifact decisions."""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, TypeVar

from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory


RenderPhase = Literal["schedule", "layout", "routing", "output"]
T = TypeVar("T")


@dataclass(frozen=True)
class RenderProgressEvent:
    phase: RenderPhase
    completed: int | None = None
    total: int | None = None
    pass_name: str | None = None


@dataclass(frozen=True)
class RenderWorkPhaseEvent:
    """An attempted routing pass, not accepted geometry or completion counts."""

    phase: RenderPhase
    pass_name: str


@dataclass(frozen=True)
class RenderAdvisoryEvent:
    """One early render advisory, distinct from phase/count progress events."""

    advisory: RoutingCostAdvisory


RenderEvent = RenderProgressEvent | RenderWorkPhaseEvent | RenderAdvisoryEvent


class RenderProgress:
    """A best-effort sink shared by one render's use cases and Layout.

    A failed observer is detached: observation cannot turn a valid render into
    a failure. No clock, artifact, resource identity or search budget lives here.
    """

    def __init__(self, observer: Callable[[RenderEvent], None]):
        self._observer: Callable[[RenderEvent], None] | None = observer
        self._immediate_observer: Callable[[RenderEvent], None] | None = None

    def emit(self, event: RenderEvent) -> None:
        if isinstance(event, (RenderAdvisoryEvent, RenderWorkPhaseEvent)) and self._immediate_observer is not None:
            self._immediate_observer(event)
            return
        if self._observer is not None:
            try:
                self._observer(event)
            except Exception:
                self._observer = None

    def phase(self, phase: RenderPhase) -> None:
        self.emit(RenderProgressEvent(phase))

    def advisory(self, advisory: RoutingCostAdvisory) -> None:
        self.emit(RenderAdvisoryEvent(advisory))

    def buffered(self, observer: Callable[[RenderEvent], None]) -> RenderProgress:
        """Buffer candidate counts but immediately report attempted work.

        A work advisory describes an attempt, not accepted candidate geometry.
        The parent remains the best-effort sink; nested buffers preserve it.
        """
        child = RenderProgress(observer)
        child._immediate_observer = self.emit
        return child

    def routing(self, declarations: Sequence[T], *, pass_name: str) -> Iterator[T]:
        """Advance only after a declaration's work returns, not per instance."""
        total = len(declarations)
        if total:
            self.emit(RenderWorkPhaseEvent("routing", pass_name))
        self.emit(RenderProgressEvent("routing", 0, total, pass_name))
        for completed, declaration in enumerate(declarations, 1):
            yield declaration
            self.emit(RenderProgressEvent("routing", completed, total, pass_name))
