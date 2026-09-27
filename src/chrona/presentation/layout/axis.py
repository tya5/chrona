"""Renderer-neutral Date-only axis intervals for presentation scenes.

This module deliberately returns temporal facts only.  Coordinate projection,
font choice and SVG emission remain later Scene/adapter responsibilities.
"""
from __future__ import annotations

from chrona.presentation.layout.text import measure_text_width
from chrona.presentation.model.axis_names import AxisNameTable

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
    """Deterministic retained/thinned positions for one measured label sequence."""

    retained_positions: tuple[int, ...]
    thinned_positions: tuple[int, ...]


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
    """Retain exactly the candidates whose own measured label fits.

    Each candidate's fit is measured against its own clipped interval and does
    not depend on any other candidate's disposition, so a fitting candidate is
    never thinned to keep a uniform pattern, and a non-fitting candidate is
    always thinned.  Thinning may not remove every candidate; a tier with no
    fitting candidate at all diagnoses instead, as before.
    """
    retained = tuple(index for index, fits in enumerate(label_fits) if fits)
    if not retained:
        raise ValueError("E_PRESENTATION_AXIS_OVERFLOW")
    thinned = tuple(index for index, fits in enumerate(label_fits) if not fits)
    return AxisThinningSchedule(retained, thinned)


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


_FORMS_BY_LEVEL = {
    "year": frozenset({"year"}),
    "half": frozenset({"half-year"}),
    "quarter": frozenset({"quarter", "year-quarter", "quarter-year"}),
    "month": frozenset({"short-month", "long-month", "numeric-month", "short-month-year",
                        "long-month-year", "numeric-year-month"}),
    "week": frozenset({"iso-week"}),
    "day": frozenset({"localized-date"}),
}


def format_axis_tier_label(interval: AxisInterval, form: str, table: AxisNameTable) -> str:
    """Format a natural bucket from a selected table, never from a locale code."""
    if form not in _FORMS_BY_LEVEL[interval.level]:
        raise ValueError("E_PRESENTATION_AXIS_FORMAT")
    value = interval.natural_start
    iso_year, iso_week, _ = value.isocalendar()
    fiscal_year = int(interval.label.split("-", 1)[0])
    components = {
        "year": value.year, "fiscalYear": fiscal_year,
        "half": interval.label.rsplit("H", 1)[-1] if interval.level == "half" else "",
        "quarter": interval.label.rsplit("Q", 1)[-1] if interval.level == "quarter" else "",
        "monthShort": table.month_short[value.month - 1],
        "monthLong": table.month_long[value.month - 1],
        "monthNumber": value.month, "monthNumeric": f"{value.month:02d}",
        "day": value.day, "dayNumeric": f"{value.day:02d}",
        "isoYear": iso_year, "isoWeek": f"{iso_week:02d}",
    }
    return table.format(form, components)


def axis_label_fits(*, content: str, available_inline: float, font_size: float,
                    font_metrics: Any, letter_spacing: float = 0.0,
                    text_transform: str = "none", numeric_spacing: str = "proportional",
                    orientation: str = "horizontal", line_height: float = 1.2) -> bool:
    """Return whether a selected axis label fits its clipped interval."""
    width = measure_text_width(content, font_size=font_size, font_metrics=font_metrics,
                               letter_spacing=letter_spacing, text_transform=text_transform,
                               numeric_spacing=numeric_spacing)
    if orientation == "horizontal":
        occupied_inline = width
    elif orientation in {"rotate-cw", "rotate-ccw"}:
        occupied_inline = font_size * line_height
    else:
        raise ValueError("E_PRESENTATION_TEXT_ORIENTATION")
    return occupied_inline <= available_inline
