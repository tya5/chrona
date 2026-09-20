from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from calendar import monthrange
import re


_PART = re.compile(r"(-?\d+)(wd|mo|y|w|d)")
_WEEKDAY = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class TemporalError(ValueError):
    pass


@dataclass(frozen=True)
class Calendar:
    working_days: frozenset[str]
    exceptions: dict[date, bool]

    @classmethod
    def from_mapping(cls, value: dict) -> "Calendar":
        if not value["working_days"]:
            raise TemporalError("Calendar requires at least one working day")
        return cls(
            frozenset(value["working_days"]),
            {as_date(item["date"]): item["working"] for item in value.get("exceptions", [])},
        )

    def is_working(self, value: date) -> bool:
        return self.exceptions.get(value, _WEEKDAY[value.weekday()] in self.working_days)

    def next_working(self, value: date) -> date:
        while not self.is_working(value):
            value += timedelta(days=1)
        return value


def as_date(value: str | date) -> date:
    if isinstance(value, datetime):
        raise TemporalError(f"Expected Date, got DateTime {value!r}")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise TemporalError(f"Expected ISO Date, got {value!r}") from exc


def parse_amount(value: str) -> list[tuple[int, str]]:
    """Parse a Core amount. Parts are applied left-to-right (largest first)."""
    parts = _PART.findall(value)
    if not parts or " ".join(f"{n}{unit}" for n, unit in parts) != value:
        raise TemporalError(f"Invalid temporal amount: {value!r}")
    return [(int(n), unit) for n, unit in parts]


def is_scheduled_amount(value: str) -> bool:
    return bool(re.fullmatch(r"[1-9]\d*(?:d|w|wd)", value))


def requires_working_calendar(value: str) -> bool:
    """Return whether any parsed amount component uses working days."""
    return any(unit == "wd" for _, unit in parse_amount(value))


def _clamp_month(value: date, months: int) -> date:
    total = value.year * 12 + (value.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def advance(value: date, amount: str, calendar: Calendar | None = None) -> date:
    out = as_date(value)
    for number, unit in parse_amount(amount):
        if unit == "y":
            out = _clamp_month(out, number * 12)
        elif unit == "mo":
            out = _clamp_month(out, number)
        elif unit == "w":
            out += timedelta(days=number * 7)
        elif unit == "d":
            out += timedelta(days=number)
        else:
            if calendar is None:
                raise TemporalError("WorkPeriod requires a calendar")
            out = _advance_work(out, number, calendar)
    return out


def retreat(value: date, amount: str, calendar: Calendar | None = None) -> date:
    inverse = " ".join(f"{-number}{unit}" for number, unit in parse_amount(amount))
    return advance(value, inverse, calendar)


def _advance_work(value: date, count: int, calendar: Calendar) -> date:
    if count == 0:
        return value
    step = 1 if count > 0 else -1
    remaining, out = abs(count), value
    while remaining:
        out += timedelta(days=step)
        if calendar.is_working(out):
            remaining -= 1
    return out
