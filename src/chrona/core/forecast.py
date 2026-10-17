"""Derived forecast facts, independent of scheduling algorithms and presentation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic


@dataclass(frozen=True)
class ForecastItem:
    placement: Mapping[str, date]
    completed: bool


@dataclass(frozen=True)
class ForecastOutcome:
    """Complete forecast facts or fatal diagnostics, never a changed plan outcome.

    Findings include reported fixed-point misses and informational observations.
    An unsuccessful outcome exposes no partial item set as a usable forecast.
    """

    items: Mapping[str, ForecastItem]
    diagnostics: tuple[Diagnostic, ...] = ()
    findings: tuple[Diagnostic, ...] = ()
    unmatched_actual_ids: tuple[str, ...] = ()
    moved_count: int = 0
    analysis: Any | None = None
    warnings: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.diagnostics
