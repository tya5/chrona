"""Axis label formatting and Layout-owned fitting over shared calendar facts."""
from __future__ import annotations

from chrona.presentation.layout.text import measure_text_width
from chrona.presentation.model.axis_names import AxisNameTable

from dataclasses import dataclass
from typing import Any


from chrona.presentation.axis_intervals import AxisInterval, AxisLevel, axis_intervals


def _axis_error(code: str, owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"{code}: {owner} " + ", ".join(fields))


@dataclass(frozen=True)
class AxisThinningSchedule:
    """Deterministic retained/thinned positions for one measured label sequence."""

    retained_positions: tuple[int, ...]
    thinned_positions: tuple[int, ...]


def thinning_schedule(label_fits: tuple[bool, ...]) -> AxisThinningSchedule:
    """Choose the smallest phase-zero stride whose candidates all fit.

    Fit remains local to each natural interval; a stride never widens it.
    Empty input or an unfit first candidate has no viable phase-zero subset.
    """
    retained: tuple[int, ...] = ()
    if label_fits and label_fits[0]:
        for stride in range(1, len(label_fits) + 1):
            positions = range(0, len(label_fits), stride)
            if all(label_fits[index] for index in positions):
                retained = tuple(positions)
                break
    retained_set = frozenset(retained)
    return AxisThinningSchedule(retained, tuple(index for index in range(len(label_fits))
                                               if index not in retained_set))


_FORMS_BY_LEVEL = {
    "year": frozenset({"year"}),
    "half": frozenset({"half-year"}),
    "quarter": frozenset({"quarter", "year-quarter", "quarter-year"}),
    "month": frozenset({"short-month", "long-month", "numeric-month", "short-month-year",
                        "long-month-year", "numeric-year-month"}),
    "week": frozenset({"iso-week", "start-day-month", "start-numeric"}),
    "day": frozenset({"localized-date", "day-month", "day-month-year"}),
}


def format_axis_tier_label(interval: AxisInterval, form: str, table: AxisNameTable) -> str:
    """Format a natural bucket from a selected table, never from a locale code."""
    if form not in _FORMS_BY_LEVEL[interval.level]:
        raise _axis_error("E_PRESENTATION_AXIS_FORMAT", "axis interval label",
                          level=interval.level, form=form,
                          allowed_forms=tuple(sorted(_FORMS_BY_LEVEL[interval.level])))
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
        raise _axis_error("E_PRESENTATION_TEXT_ORIENTATION", "axis label measurement",
                          orientation=orientation, available_inline=available_inline,
                          font_size=font_size)
    return occupied_inline <= available_inline
