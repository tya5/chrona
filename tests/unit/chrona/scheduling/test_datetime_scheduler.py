from chrona.scheduling.datetime_scheduler import schedule_datetime


def _instant(value: str, zone: str = "UTC"):
    return {"instant": value, "zone": zone}


def _project(objects, relations=()):
    return {"version": "timeline/v0.2", "temporalProfile": "datetime-v0.2", "project": {"id": "p"}, "objects": objects, "relations": list(relations)}


def test_datetime_scheduler_keeps_v0_1_separate_and_places_exact_duration():
    project = _project({
        "source": {"type": "milestone", "schedule": {"mode": "fixed", "at": _instant("2027-03-27T10:00:00Z")}},
        "target": {"type": "task", "schedule": {"mode": "scheduled", "amount": {"kind": "exactDuration", "value": "PT2H"}, "anchor": {"start": _instant("2027-03-27T11:00:00Z")}}},
    }, [{"type": "dependency", "from": {"object": "source", "endpoint": "at"}, "to": {"object": "target", "endpoint": "start"}, "lag": {"kind": "exactDuration", "value": "PT1H"}}])
    result = schedule_datetime(project)
    assert result.ok and result.placements["target"]["end"].instant.isoformat() == "2027-03-27T13:00:00+00:00"


def test_datetime_scheduler_reverses_end_anchor_and_rejects_recurrence_endpoint():
    project = _project({
        "source": {"type": "milestone", "schedule": {"mode": "fixed", "at": _instant("2027-03-27T10:00:00Z")}},
        "target": {"type": "task", "schedule": {"mode": "scheduled", "amount": {"kind": "exactDuration", "value": "PT2H"}, "anchor": {"end": _instant("2027-03-27T13:00:00Z")}}},
    }, [{"type": "dependency", "from": {"object": "source", "endpoint": "at"}, "to": {"object": "target", "endpoint": "end"}, "lag": {"kind": "exactDuration", "value": "PT1H"}}])
    result = schedule_datetime(project)
    assert result.ok and result.placements["target"]["start"].instant.isoformat() == "2027-03-27T11:00:00+00:00"
    project["objects"]["repeat"] = {"type": "milestone", "schedule": {"mode": "recurrence", "recurrence": {"localStart": "2027-01-01T09:00", "zone": "UTC", "frequency": "daily", "interval": 1, "count": 1, "disambiguation": "reject"}}}
    project["relations"][0]["from"] = {"object": "repeat", "endpoint": "at"}
    assert {item.id for item in schedule_datetime(project).diagnostics} == {"E_DATETIME_ENDPOINT"}
