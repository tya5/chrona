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
