"""Opt-in DateTime/DST temporal successor; Date-only APIs remain separate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
import re
from typing import Any

from chrona.core.temporal import advance, parse_amount


class DateTimeTemporalError(ValueError):
    def __init__(self, diagnostic: str):
        super().__init__(diagnostic)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class ZonedInstant:
    instant: datetime
    zone: str

    def local(self) -> datetime:
        return self.instant.astimezone(ZoneInfo(self.zone))


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:
        raise DateTimeTemporalError("E_TEMPORAL_ZONE") from exc


def _parse_instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DateTimeTemporalError("E_TEMPORAL_DATETIME") from exc
    if parsed.tzinfo is None:
        raise DateTimeTemporalError("E_TEMPORAL_DATETIME")
    return parsed.astimezone(UTC)


def resolve_datetime(value: dict[str, Any]) -> ZonedInstant:
    """Resolve an authoritative instant or an explicitly disambiguated local time."""
    zone_name = value.get("zone", "")
    zone = _zone(zone_name)
    if "instant" in value:
        return ZonedInstant(_parse_instant(str(value["instant"])), zone_name)
    if not {"local", "disambiguation"} <= set(value):
        raise DateTimeTemporalError("E_TEMPORAL_DATETIME")
    try:
        local = datetime.fromisoformat(str(value["local"]))
    except ValueError as exc:
        raise DateTimeTemporalError("E_TEMPORAL_DATETIME") from exc
    if local.tzinfo is not None:
        raise DateTimeTemporalError("E_TEMPORAL_DATETIME")
    candidates: list[datetime] = []
    for fold in (0, 1):
        aware = local.replace(tzinfo=zone, fold=fold)
        instant = aware.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == local and instant not in candidates:
            candidates.append(instant)
    if not candidates:
        raise DateTimeTemporalError("E_TEMPORAL_NONEXISTENT_LOCAL_TIME")
    if len(candidates) == 2:
        policy = value["disambiguation"]
        if policy == "reject":
            raise DateTimeTemporalError("E_TEMPORAL_AMBIGUOUS_LOCAL_TIME")
        if policy not in {"earlier", "later"}:
            raise DateTimeTemporalError("E_TEMPORAL_DATETIME")
        return ZonedInstant(min(candidates) if policy == "earlier" else max(candidates), zone_name)
    return ZonedInstant(candidates[0], zone_name)


_DURATION = re.compile(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$")


def add_exact_duration(value: ZonedInstant, duration: str) -> ZonedInstant:
    match = _DURATION.fullmatch(duration)
    if not match:
        raise DateTimeTemporalError("E_TEMPORAL_DURATION")
    parts = {name: int(number or 0) for name, number in match.groupdict().items()}
    return ZonedInstant(value.instant + timedelta(**parts), value.zone)


def add_calendar_period(value: ZonedInstant, amount: str, disambiguation: str) -> ZonedInstant:
    local = value.local()
    try:
        target_date = advance(local.date(), amount)
    except Exception as exc:
        raise DateTimeTemporalError("E_TEMPORAL_CALENDAR_PERIOD") from exc
    return resolve_datetime({"local": datetime.combine(target_date, local.timetz().replace(tzinfo=None)).isoformat(timespec="seconds"), "zone": value.zone, "disambiguation": disambiguation})


def subtract_calendar_period(value: ZonedInstant, amount: str, disambiguation: str) -> ZonedInstant:
    """Inverse CalendarPeriod arithmetic with the same local DST policy."""
    try:
        inverse = " ".join(f"{-number}{unit}" for number, unit in parse_amount(amount))
    except Exception as exc:
        raise DateTimeTemporalError("E_TEMPORAL_CALENDAR_PERIOD") from exc
    return add_calendar_period(value, inverse, disambiguation)


def generate_recurrence(recurrence: dict[str, Any]) -> tuple[ZonedInstant, ...]:
    frequency = recurrence.get("frequency")
    unit = {"daily": "d", "weekly": "w", "monthly": "mo"}.get(frequency)
    if unit is None or not isinstance(recurrence.get("interval"), int) or recurrence["interval"] < 1:
        raise DateTimeTemporalError("E_RECURRENCE")
    count = recurrence.get("count")
    until = recurrence.get("until")
    if (count is None) == (until is None):
        raise DateTimeTemporalError("E_RECURRENCE")
    if count is not None and (not isinstance(count, int) or count < 1):
        raise DateTimeTemporalError("E_RECURRENCE")
    try:
        local = datetime.fromisoformat(str(recurrence["localStart"]))
        if local.tzinfo is not None:
            raise ValueError("localStart must be local")
        until_value = resolve_datetime(until) if until is not None else None
    except (KeyError, TypeError, ValueError, DateTimeTemporalError) as exc:
        raise DateTimeTemporalError("E_RECURRENCE") from exc
    values = []
    index = 0
    while count is None or index < count:
        date_value = advance(local.date(), f"{index * recurrence['interval']}{unit}")
        occurrence = resolve_datetime({"local": datetime.combine(date_value, local.time()).isoformat(timespec="seconds"), "zone": recurrence["zone"], "disambiguation": recurrence["disambiguation"]})
        if until_value is not None and occurrence.instant > until_value.instant:
            break
        values.append(occurrence)
        index += 1
    return tuple(values)
