"""Ephemeral render observations; never an input to artifact decisions."""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, TypeVar


RenderPhase = Literal["schedule", "layout", "routing", "output"]
T = TypeVar("T")


@dataclass(frozen=True)
class RenderProgressEvent:
    phase: RenderPhase
    completed: int | None = None
    total: int | None = None
    pass_name: str | None = None


class RenderProgress:
    """A best-effort sink shared by one render's use cases and Layout.

    A failed observer is detached: observation cannot turn a valid render into
    a failure. No clock, artifact, resource identity or search budget lives here.
    """

    def __init__(self, observer: Callable[[RenderProgressEvent], None]):
        self._observer: Callable[[RenderProgressEvent], None] | None = observer

    def emit(self, event: RenderProgressEvent) -> None:
        if self._observer is not None:
            try:
                self._observer(event)
            except Exception:
                self._observer = None

    def phase(self, phase: RenderPhase) -> None:
        self.emit(RenderProgressEvent(phase))

    def routing(self, declarations: Sequence[T], *, pass_name: str) -> Iterator[T]:
        """Advance only after a declaration's work returns, not per instance."""
        total = len(declarations)
        self.emit(RenderProgressEvent("routing", 0, total, pass_name))
        for completed, declaration in enumerate(declarations, 1):
            yield declaration
            self.emit(RenderProgressEvent("routing", completed, total, pass_name))
