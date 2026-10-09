"""Pure calendar interval facts and stable band identity, shared before Layout.

No measurement, Scheme, coordinate, Scene or renderer dependencies live here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


AxisLevel = Literal["year", "half", "quarter", "month", "week", "day"]
_LEVELS = frozenset({"year", "half", "quarter", "month", "week", "day"})
_ERROR = "E_PRESENTATION_AXIS_INVALID"


@dataclass(frozen=True)
class AxisInterval:
    """One clipped half-open interval labelled by its natural calendar bucket."""

    start: date
    end: date
    level: AxisLevel
    label: str
    index: int
    natural_start: date
    natural_end: date


def axis_intervals(start: date, end: date, level: AxisLevel, *, tick_step: int = 1,
                   fiscal_start_month: int = 1) -> tuple[AxisInterval, ...]:
    """Return deterministic, clipped Date-only intervals for ``[start, end)``.

    Weeks are ISO-8601 weeks starting Monday.  Labels use the natural bucket
    rather than the clipped interval start, so a partial first week retains the
    ISO week-year that actually owns it.  ``tick_step`` retains every nth
    natural bucket; it never changes the time window or any retained interval.
    """
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise ValueError(_ERROR)
    if (level not in _LEVELS or isinstance(tick_step, bool) or not isinstance(tick_step, int) or tick_step < 1
            or isinstance(fiscal_start_month, bool) or not isinstance(fiscal_start_month, int)
            or not 1 <= fiscal_start_month <= 12):
        raise ValueError(_ERROR)

    bucket_start = _bucket_start(start, level, fiscal_start_month)
    result: list[AxisInterval] = []
    index = 0
    while bucket_start < end:
        bucket_end = _next_bucket_start(bucket_start, level, fiscal_start_month)
        if index % tick_step == 0:
            result.append(AxisInterval(
                start=max(start, bucket_start),
                end=min(end, bucket_end),
                level=level,
                label=_label(bucket_start, level, fiscal_start_month),
                index=index,
                natural_start=bucket_start,
                natural_end=bucket_end,
            ))
        bucket_start = bucket_end
        index += 1
    return tuple(result)


def _shift_months(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _bucket_start(value: date, level: AxisLevel, fiscal_start_month: int = 1) -> date:
    if level == "day":
        return value
    if level == "week":
        return value - timedelta(days=value.weekday())
    if level == "month":
        return value.replace(day=1)
    if level in {"year", "half", "quarter"}:
        month_offset = (value.month - fiscal_start_month) % 12
        size = {"year": 12, "half": 6, "quarter": 3}[level]
        return _shift_months(value.replace(day=1), -(month_offset % size))
    raise ValueError(_ERROR)


def _next_bucket_start(value: date, level: AxisLevel, fiscal_start_month: int = 1) -> date:
    if level == "day":
        return value + timedelta(days=1)
    if level == "week":
        return value + timedelta(days=7)
    if level == "month":
        return _shift_months(value, 1)
    if level in {"year", "half", "quarter"}:
        return _shift_months(value, {"year": 12, "half": 6, "quarter": 3}[level])
    raise ValueError(_ERROR)


def _label(natural_start: date, level: AxisLevel, fiscal_start_month: int = 1) -> str:
    if level == "day":
        return natural_start.isoformat()
    if level == "week":
        iso_year, iso_week, _ = natural_start.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if level == "month":
        return f"{natural_start:%Y-%m}"
    if level == "year":
        return str(_fiscal_year(natural_start, fiscal_start_month))
    if level == "half":
        return f"{_fiscal_year(natural_start, fiscal_start_month)}-H{((natural_start.month - fiscal_start_month) % 12) // 6 + 1}"
    return f"{_fiscal_year(natural_start, fiscal_start_month)}-Q{((natural_start.month - fiscal_start_month) % 12) // 3 + 1}"


def _fiscal_year(value: date, fiscal_start_month: int) -> int:
    return value.year if fiscal_start_month == 1 or value.month >= fiscal_start_month else value.year - 1


def axis_band_placement_id(tier_index: int, interval_index: int) -> str:
    """The completed band identity; paint and geometry use the same key."""
    return f"axis-band-rect:{tier_index}:{interval_index}"
