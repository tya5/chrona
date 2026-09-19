from datetime import UTC, datetime

import pytest

from chrona.temporal_datetime import DateTimeTemporalError, add_calendar_period, add_exact_duration, generate_recurrence, resolve_datetime


def test_dst_fold_requires_policy_and_selects_distinct_instants():
    local = {"local": "2027-10-31T01:30:00", "zone": "Europe/London"}
    earlier = resolve_datetime(local | {"disambiguation": "earlier"})
    later = resolve_datetime(local | {"disambiguation": "later"})
    assert earlier.instant < later.instant and earlier.local().hour == later.local().hour == 1
    with pytest.raises(DateTimeTemporalError, match="E_TEMPORAL_AMBIGUOUS_LOCAL_TIME"):
        resolve_datetime(local | {"disambiguation": "reject"})


def test_dst_gap_rejects_and_duration_remains_instant_arithmetic():
    with pytest.raises(DateTimeTemporalError, match="E_TEMPORAL_NONEXISTENT_LOCAL_TIME"):
        resolve_datetime({"local": "2027-03-28T01:30:00", "zone": "Europe/London", "disambiguation": "reject"})
    source = resolve_datetime({"instant": "2027-03-27T12:00:00Z", "zone": "Europe/London"})
    assert add_exact_duration(source, "PT24H").instant == datetime(2027, 3, 28, 12, tzinfo=UTC)


def test_calendar_period_and_recurrence_preserve_declared_zone_and_policy():
    source = resolve_datetime({"instant": "2027-10-30T00:30:00Z", "zone": "Europe/London"})
    assert add_calendar_period(source, "1d", "later").local().date().isoformat() == "2027-10-31"
    occurrences = generate_recurrence({"localStart": "2027-10-31T01:30:00", "zone": "Europe/London", "frequency": "weekly", "interval": 1, "count": 2, "disambiguation": "later"})
    assert len(occurrences) == 2 and occurrences[0].instant < occurrences[1].instant


def test_recurrence_until_is_inclusive_and_requires_one_terminal_bound():
    recurrence = {"localStart": "2027-01-01T09:00:00", "zone": "UTC", "frequency": "daily", "interval": 1, "disambiguation": "reject"}
    until = {"instant": "2027-01-02T09:00:00Z", "zone": "UTC"}
    assert len(generate_recurrence(recurrence | {"until": until})) == 2
    with pytest.raises(DateTimeTemporalError, match="E_RECURRENCE"):
        generate_recurrence(recurrence)
