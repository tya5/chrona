"""Renderer-neutral Date-only axis intervals for presentation scenes.

This module deliberately returns temporal facts only.  Coordinate projection,
font choice and SVG emission remain later Scene/adapter responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


AxisLevel = Literal["quarter", "month", "week", "day"]
_LEVELS = frozenset({"quarter", "month", "week", "day"})
_ERROR = "E_PRESENTATION_AXIS_INVALID"


@dataclass(frozen=True)
class AxisInterval:
    """One clipped half-open interval labelled by its natural calendar bucket."""

    start: date
    end: date
    level: AxisLevel
    label: str
    index: int


def axis_intervals(start: date, end: date, level: AxisLevel, *, tick_step: int = 1) -> tuple[AxisInterval, ...]:
    """Return deterministic, clipped Date-only intervals for ``[start, end)``.

    Weeks are ISO-8601 weeks starting Monday.  Labels use the natural bucket
    rather than the clipped interval start, so a partial first week retains the
    ISO week-year that actually owns it.  ``tick_step`` retains every nth
    natural bucket; it never changes the time window or any retained interval.
    """
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise ValueError(_ERROR)
    if level not in _LEVELS or isinstance(tick_step, bool) or not isinstance(tick_step, int) or tick_step < 1:
        raise ValueError(_ERROR)

    bucket_start = _bucket_start(start, level)
    result: list[AxisInterval] = []
    index = 0
    while bucket_start < end:
        bucket_end = _next_bucket_start(bucket_start, level)
        if index % tick_step == 0:
            result.append(AxisInterval(
                start=max(start, bucket_start),
                end=min(end, bucket_end),
                level=level,
                label=_label(bucket_start, level),
                index=index,
            ))
        bucket_start = bucket_end
        index += 1
    return tuple(result)


def _bucket_start(value: date, level: AxisLevel) -> date:
    if level == "day":
        return value
    if level == "week":
        return value - timedelta(days=value.weekday())
    if level == "month":
        return value.replace(day=1)
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


def _next_bucket_start(value: date, level: AxisLevel) -> date:
    if level == "day":
        return value + timedelta(days=1)
    if level == "week":
        return value + timedelta(days=7)
    if level == "month":
        return date(value.year + 1, 1, 1) if value.month == 12 else date(value.year, value.month + 1, 1)
    return date(value.year + 1, 1, 1) if value.month == 10 else date(value.year, value.month + 3, 1)


def _label(natural_start: date, level: AxisLevel) -> str:
    if level == "day":
        return natural_start.isoformat()
    if level == "week":
        iso_year, iso_week, _ = natural_start.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if level == "month":
        return f"{natural_start:%Y-%m}"
    return f"{natural_start.year}-Q{(natural_start.month - 1) // 3 + 1}"
