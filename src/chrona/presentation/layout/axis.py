"""Renderer-neutral Date-only axis intervals for presentation scenes.

This module deliberately returns temporal facts only.  Coordinate projection,
font choice and SVG emission remain later Scene/adapter responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal


AxisLevel = Literal["year", "quarter", "month", "week", "day"]
_LEVELS = frozenset({"year", "quarter", "month", "week", "day"})
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
                natural_start=bucket_start,
                natural_end=bucket_end,
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
    if level == "year":
        return date(value.year, 1, 1)
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


def _next_bucket_start(value: date, level: AxisLevel) -> date:
    if level == "day":
        return value + timedelta(days=1)
    if level == "week":
        return value + timedelta(days=7)
    if level == "month":
        return date(value.year + 1, 1, 1) if value.month == 12 else date(value.year, value.month + 1, 1)
    if level == "year":
        return date(value.year + 1, 1, 1)
    return date(value.year + 1, 1, 1) if value.month == 10 else date(value.year, value.month + 3, 1)


def _label(natural_start: date, level: AxisLevel) -> str:
    if level == "day":
        return natural_start.isoformat()
    if level == "week":
        iso_year, iso_week, _ = natural_start.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if level == "month":
        return f"{natural_start:%Y-%m}"
    if level == "year":
        return str(natural_start.year)
    return f"{natural_start.year}-Q{(natural_start.month - 1) // 3 + 1}"


_SHORT_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_LONG_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def format_axis_label(interval: AxisInterval, formatting: dict, locale: str) -> str:
    """Format one natural bucket without consulting the process locale."""
    value, level = interval.natural_start, interval.level
    language = locale.split("-", 1)[0].lower()
    if level == "year":
        return str(value.year)
    if level == "quarter":
        quarter = f"Q{(value.month - 1) // 3 + 1}"
        style = formatting["quarter"]
        if style == "quarter":
            return quarter
        if style == "year-quarter":
            return f"{value.year}年{quarter}" if language == "ja" else f"{value.year} {quarter}"
        if style == "quarter-year":
            return f"{quarter} {value.year}年" if language == "ja" else f"{quarter} {value.year}"
        raise ValueError("E_PRESENTATION_AXIS_FORMAT")
    if level == "month":
        style = formatting["month"]
        if language == "ja":
            month = f"{value.month}月"
            return month if style in {"short-month", "long-month", "numeric-month"} else f"{value.year}年{month}"
        short, long = _SHORT_MONTHS[value.month - 1], _LONG_MONTHS[value.month - 1]
        return {
            "short-month-year": f"{short} {value.year}",
            "long-month-year": f"{long} {value.year}",
            "numeric-year-month": f"{value.year}-{value.month:02d}",
            "short-month": short,
            "long-month": long,
            "numeric-month": f"{value.month:02d}",
        }[style]
    if level == "day" and formatting["date"] == "localized-date":
        if language == "ja":
            return f"{value.year}/{value.month:02d}/{value.day:02d}"
        return f"{_SHORT_MONTHS[value.month - 1]} {value.day}, {value.year}"
    return interval.label


def fitting_axis(*, requested: str, start: date, end: date, inline_size: float,
                 font_size: float, font_metrics: Any) -> tuple[AxisInterval, ...]:
    """Choose the first requested axis level whose labels fit natural buckets."""
    levels = (requested,) if requested != "auto" else ("day", "week", "month", "quarter", "year")
    for level in levels:
        intervals = axis_intervals(start, end, level)
        if all(float(font_metrics.width(item.label, font_size)) <=
               (item.natural_end - item.natural_start).days * inline_size / max(1, (end - start).days)
               for item in intervals):
            return intervals
    raise ValueError("E_PRESENTATION_AXIS_OVERFLOW")


def axis_label_fits(*, content: str, available_inline: float, font_size: float,
                    font_metrics: Any) -> bool:
    """Return whether a selected axis label fits its clipped interval."""
    return float(font_metrics.width(content, font_size)) <= available_inline
