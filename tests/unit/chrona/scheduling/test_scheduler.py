from datetime import date

from chrona.scheduling.scheduler import schedule


def _project(objects, relations=()):
    return {
        "version": "timeline/v0.3",
        "project": {"id": "demo"},
        "objects": objects,
        "relations": list(relations),
    }


def test_fs_zero_lag_places_successor_at_predecessor_end():
    project = _project(
        {
            "A": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-10"}},
            "B": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5d"}},
        },
        [{"type": "dependency", "from": {"object": "A", "endpoint": "end"}, "to": {"object": "B", "endpoint": "start"}, "lag": "0d"}],
    )
    result = schedule(project)
    assert result.ok
    assert result.placements["B"] == {"start": date(2026, 10, 10), "end": date(2026, 10, 15)}


def test_fixed_target_violation_is_not_repaired_by_moving_target():
    project = _project(
        {
            "A": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-10"}},
            "B": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-10", "end": "2026-10-11"}},
        },
        [{"type": "dependency", "from": {"object": "A", "endpoint": "end"}, "to": {"object": "B", "endpoint": "start"}, "lag": "2d"}],
    )
    result = schedule(project)
    assert "E_FIXED_TARGET_VIOLATION" in {item.id for item in result.diagnostics}


def test_scheduler_derives_total_float_and_critical_chain_per_component():
    project = _project(
        {
            "start": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-02"}},
            "critical": {"type": "task", "schedule": {"mode": "scheduled", "amount": "4d"}},
            "slack": {"type": "task", "schedule": {"mode": "scheduled", "amount": "2d"}},
            "finish": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
        },
        [
            {"type": "dependency", "from": {"object": "start", "endpoint": "end"}, "to": {"object": "critical", "endpoint": "start"}},
            {"type": "dependency", "from": {"object": "start", "endpoint": "end"}, "to": {"object": "slack", "endpoint": "start"}},
            {"type": "dependency", "from": {"object": "critical", "endpoint": "end"}, "to": {"object": "finish", "endpoint": "start"}},
            {"type": "dependency", "from": {"object": "slack", "endpoint": "end"}, "to": {"object": "finish", "endpoint": "start"}},
        ],
    )
    result = schedule(project)
    assert result.ok and result.analysis is not None
    assert result.analysis.total_float == {"start": 0, "critical": 0, "slack": 2, "finish": 0}
    assert result.analysis.critical == frozenset({"start", "critical", "finish"})


def test_scheduler_marks_disconnected_singletons_critical():
    result = schedule(_project({
        "a": {"type": "task", "schedule": {"mode": "fixed", "at": "2026-10-01"}},
        "b": {"type": "task", "schedule": {"mode": "fixed", "at": "2026-10-10"}},
    }))
    assert result.ok and result.analysis is not None
    assert result.analysis.critical == frozenset({"a", "b"})


def test_scheduler_counts_float_in_the_objects_working_calendar():
    project = _project(
        {
            "start": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-02", "end": "2026-10-03"}},
            "critical": {"type": "task", "schedule": {"mode": "scheduled", "amount": "4wd"}},
            "slack": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1wd"}},
            "finish": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1wd"}},
        },
        [
            {"type": "dependency", "from": {"object": "start", "endpoint": "end"}, "to": {"object": "critical", "endpoint": "start"}},
            {"type": "dependency", "from": {"object": "start", "endpoint": "end"}, "to": {"object": "slack", "endpoint": "start"}},
            {"type": "dependency", "from": {"object": "critical", "endpoint": "end"}, "to": {"object": "finish", "endpoint": "start"}},
            {"type": "dependency", "from": {"object": "slack", "endpoint": "end"}, "to": {"object": "finish", "endpoint": "start"}},
        ],
    )
    project["project"]["calendar"] = "weekdays"
    project["calendars"] = {"weekdays": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    result = schedule(project)
    assert result.ok and result.analysis is not None
    assert result.analysis.total_float["slack"] == 3
    assert result.analysis.critical == frozenset({"start", "critical", "finish"})


def test_scheduler_with_diagnostics_exposes_no_partial_analysis():
    result = schedule(_project({
        "a": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
        "b": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
    }, [
        {"type": "dependency", "from": {"object": "a", "endpoint": "start"}, "to": {"object": "b", "endpoint": "start"}, "lag": "0d"},
        {"type": "dependency", "from": {"object": "b", "endpoint": "start"}, "to": {"object": "a", "endpoint": "start"}, "lag": "0d"},
    ]))
    assert not result.ok and result.analysis is None
