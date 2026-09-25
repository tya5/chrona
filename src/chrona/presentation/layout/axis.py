"""Renderer-neutral Date-only axis intervals for presentation scenes.

This module deliberately returns temporal facts only.  Coordinate projection,
font choice and SVG emission remain later Scene/adapter responsibilities.
"""
from __future__ import annotations

from chrona.presentation.layout.text import measure_text_width

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal


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


@dataclass(frozen=True)
class AxisThinningSchedule:
    """Deterministic retained positions for one measured label sequence."""

    stride: int
    phase: int
    retained_positions: tuple[int, ...]


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


def thinning_schedule(label_fits: tuple[bool, ...]) -> AxisThinningSchedule:
    """Select the least periodic schedule containing only measured-fitting labels."""
    for stride in range(1, len(label_fits) + 1):
        for phase in range(stride):
            retained = tuple(index for index in range(phase, len(label_fits), stride))
            if retained and all(label_fits[index] for index in retained):
                return AxisThinningSchedule(stride, phase, retained)
    raise ValueError("E_PRESENTATION_AXIS_OVERFLOW")


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


_SHORT_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_LONG_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def format_axis_label(interval: AxisInterval, formatting: dict, locale: str) -> str:
    """Format one natural bucket without consulting the process locale."""
    value, level = interval.natural_start, interval.level
    language = locale.split("-", 1)[0].lower()
    if level == "year":
        return interval.label
    if level == "quarter":
        quarter = interval.label.rsplit("-", 1)[-1]
        style = formatting["quarter"]
        if style == "quarter":
            return quarter
        if style == "year-quarter":
            return f"{interval.label.split('-', 1)[0]}年{quarter}" if language == "ja" else f"{interval.label.split('-', 1)[0]} {quarter}"
        if style == "quarter-year":
            return f"{quarter} {interval.label.split('-', 1)[0]}年" if language == "ja" else f"{quarter} {interval.label.split('-', 1)[0]}"
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


def format_axis_tier_label(interval: AxisInterval, form: str, locale: str) -> str:
    """Format one selected tier without a cross-tier formatting map."""
    if interval.level == "half":
        return interval.label if form == "half-year" else _raise_format()
    if interval.level == "week":
        return interval.label if form == "iso-week" else _raise_format()
    if interval.level == "year":
        return interval.label if form == "year" else _raise_format()
    if interval.level == "day":
        return format_axis_label(interval, {"date": form}, locale)
    if interval.level == "month":
        return format_axis_label(interval, {"month": form}, locale)
    return format_axis_label(interval, {"quarter": form}, locale)


def _raise_format() -> str:
    raise ValueError("E_PRESENTATION_AXIS_FORMAT")


def axis_label_fits(*, content: str, available_inline: float, font_size: float,
                    font_metrics: Any, letter_spacing: float = 0.0,
                    text_transform: str = "none") -> bool:
    """Return whether a selected axis label fits its clipped interval."""
    return measure_text_width(content, font_size=font_size, font_metrics=font_metrics,
                              letter_spacing=letter_spacing, text_transform=text_transform) <= available_inline
