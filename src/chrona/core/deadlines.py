"""The deadline promise: a stored target compared with the selected finish.

A deadline is not a scheduling bound (Spec 04 Section 10, Q-SCHED-2). Nothing here runs
inside the scheduler: these functions read completed planned/forecast placements and
name each object selected to finish after its deadline. They never move a placement,
change a verdict, or reject a plan.

``deadline_statuses`` is the one place the lateness rule lives. The ``W_DEADLINE`` warning
and a View's deadline mark are both derived from it, so they cannot disagree.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from chrona.core.diagnostics import Diagnostic
from chrona.core.temporal import as_date


@dataclass(frozen=True)
class DeadlineStatus:
    """One object's promise against its selected finish.

    ``finish`` is the inclusive final occupied date: ``at`` for a point and
    ``end - 1 day`` for a positive span. A zero-extent rollup uses its shared
    start/end boundary as its point-like date. ``days_late`` is the signed
    calendar-day difference between that finish and the deadline.
    """

    object_id: str
    deadline: date
    finish: date
    endpoint: str
    days_late: int
    finish_basis: Literal["planned", "forecast"] = "planned"

    @property
    def slipped(self) -> bool:
        """An inclusive finish strictly after the deadline."""
        return self.days_late > 0

    @property
    def deadline_boundary(self) -> int:
        """Ordinal boundary after the inclusive deadline day (may be date.max + 1)."""
        return self.deadline.toordinal() + 1

    @property
    def finish_boundary(self) -> int:
        """Ordinal boundary after the inclusive finish day (may be date.max + 1)."""
        return self.finish.toordinal() + 1


def deadline_statuses(project: dict[str, Any], placements: dict[str, dict[str, date]],
                      forecast_placements: dict[str, dict[str, date]] | None = None) -> tuple[DeadlineStatus, ...]:
    """One status per object that has a ``deadline`` and a placement, in Project order.

    The inclusive finish of a point is ``at``; for a positive span it is the
    stored exclusive ``end`` minus one calendar day. A zero-extent rollup is
    point-like and uses its shared start/end date. An object with no deadline
    or no placement is skipped. This does not change the scheduler's endpoints.
    When supplied, ``forecast_placements`` selectively overrides the planned placement for
    the named objects; all other objects retain their planned finish.
    """
    statuses = []
    for object_id, item in project.get("objects", {}).items():
        deadline = item.get("deadline")
        forecast_placement = (forecast_placements or {}).get(object_id)
        placement = forecast_placement if forecast_placement is not None else placements.get(object_id)
        if deadline is None or not placement:
            continue
        endpoint = "at" if "at" in placement else "end"
        if endpoint not in placement:
            continue
        finish, promised = placement[endpoint], as_date(deadline)
        if endpoint == "end":
            item_schedule = item.get("schedule", {})
            zero_extent_rollup = (item_schedule.get("mode") == "rollup"
                                  and placement.get("start") == finish)
            if not zero_extent_rollup:
                finish -= timedelta(days=1)
        statuses.append(DeadlineStatus(object_id, promised, finish, endpoint, (finish - promised).days,
                                       "forecast" if forecast_placement is not None else "planned"))
    return tuple(statuses)


def deadline_warnings_from_statuses(statuses: tuple[DeadlineStatus, ...], *,
                                    forecast_mode: bool = False) -> tuple[Diagnostic, ...]:
    """Format the slipped completed statuses, optionally naming each selected basis.

    The ordinary wrapper omits the forecast basis field and text.
    Explicit forecast mode records the selected basis even for a planned fallback.
    """
    return tuple(
        Diagnostic(
            "W_DEADLINE",
            f"{status.object_id} {status.finish_basis + ' ' if forecast_mode else ''}finishes "
            f"{status.finish.isoformat()}, {status.days_late} day{'' if status.days_late == 1 else 's'} "
            f"after its deadline {status.deadline.isoformat()}",
            f"/objects/{status.object_id}/deadline",
            details={"object": status.object_id, "endpoint": status.endpoint, "finish": status.finish.isoformat(),
                     "deadline": status.deadline.isoformat(), "daysLate": status.days_late,
                     **({"finishBasis": status.finish_basis} if forecast_mode else {})},
        )
        for status in statuses if status.slipped)


def deadline_warnings(project: dict[str, Any], placements: dict[str, dict[str, date]]) -> tuple[Diagnostic, ...]:
    """One ``W_DEADLINE`` per object whose inclusive planned finish is after its ``deadline``.

    A finish equal to the deadline keeps the promise. Objects come in Project order.
    """
    return deadline_warnings_from_statuses(deadline_statuses(project, placements))
