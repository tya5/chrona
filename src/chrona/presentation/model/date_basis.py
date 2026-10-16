"""Source-local date semantics for presentation; Core dates remain half-open."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from chrona.core.temporal import Calendar, requires_working_calendar


@dataclass(frozen=True)
class ItemDateBasis:
    work_period: bool = False
    calendar: Calendar | None = None

    @classmethod
    def from_project(cls, project: Mapping[str, Any], object_id: str) -> ItemDateBasis:
        item = project["objects"][object_id]
        amount = item.get("schedule", {}).get("amount")
        calendar_id = item.get("calendar") or project.get("project", {}).get("calendar")
        raw_calendar = project.get("calendars", {}).get(calendar_id)
        return cls(isinstance(amount, str) and requires_working_calendar(amount),
                   Calendar.from_mapping(raw_calendar) if raw_calendar is not None else None)


def inclusive_end(end: date, basis: ItemDateBasis = ItemDateBasis()) -> date:
    """Close a scheduled endpoint, using workdays only for WorkPeriod spans."""
    result = end - timedelta(days=1)
    if basis.work_period and basis.calendar is not None:
        while not basis.calendar.is_working(result):
            result -= timedelta(days=1)
    return result


def endpoint_distance(planned: date, actual: date, basis: ItemDateBasis = ItemDateBasis(),
                      delta_unit: str = "calendar-days") -> int:
    """Signed half-open endpoint distance; absent calendar means all days work."""
    if delta_unit != "working-days" or basis.calendar is None:
        return (actual - planned).days
    start, end = sorted((planned, actual))
    days = 0
    while start < end:
        days += basis.calendar.is_working(start)
        start += timedelta(days=1)
    return days if actual >= planned else -days


@dataclass(frozen=True)
class DisplayDateRange:
    """Closed display endpoints, already resolved before Layout measures text."""
    start: date
    end: date


def date_range_display(value: Any, *, basis: ItemDateBasis = ItemDateBasis(),
                       end_display: str = "exclusive") -> Any:
    if end_display != "inclusive" or not isinstance(value, Mapping):
        return value
    start, end = value.get("start"), value.get("end", value.get("finish"))
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        return value
    return DisplayDateRange(start, inclusive_end(end, basis))
