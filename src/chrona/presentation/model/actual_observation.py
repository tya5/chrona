"""Renderer-neutral meaning of a started, unfinished Actual observation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping


@dataclass(frozen=True)
class InProgressActual:
    """An Actual start and the explicit as-of cutoff used to display it.

    The cutoff is presentation context, not a fabricated Actual ``finish``.
    A value with no cutoff or a zero-length interval is retained so consumers
    can preserve their established missing-as-of/invalid-cutoff handling.
    """

    start: date
    as_of: date | None

    @property
    def drawable(self) -> bool:
        return self.as_of is not None and self.as_of > self.start


def in_progress_actual(actual: Mapping[str, object] | None,
                       as_of: date | None) -> InProgressActual | None:
    """Return the normalized source fact for any span Actual with a start but no finish.

    Progress does not determine whether the observation is in progress: 0, an
    intermediate fraction, 1, or no progress all retain the same temporal
    meaning. This helper never mutates or completes the source payload.
    """
    if not isinstance(actual, Mapping):
        return None
    start = actual.get("start")
    if isinstance(start, date) and actual.get("finish") is None and actual.get("at") is None:
        return InProgressActual(start, as_of)
    return None


def finish_variance(planned: Mapping[str, object], actual: Mapping[str, object] | None,
                    as_of: date | None) -> int | None:
    """Return known finish variance, using the cutoff for a started open Actual."""
    planned_end = planned.get("end")
    if not isinstance(planned_end, date) or not isinstance(actual, Mapping):
        return None
    finish = actual.get("finish")
    if isinstance(finish, date):
        return (finish - planned_end).days
    opened = in_progress_actual(actual, as_of)
    if opened is not None and opened.drawable and opened.as_of > planned_end:
        return (opened.as_of - planned_end).days
    return None
