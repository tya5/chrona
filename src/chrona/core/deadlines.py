"""The deadline promise: a stored target compared with the planned finish (#792, #822).

A deadline is not a scheduling bound (Spec 04 Section 10, Q-SCHED-2). Nothing here runs
inside the scheduler: these functions read placements the scheduler already produced and
name each object planned to finish after its deadline. They never move a placement,
change a verdict, or reject a plan.

``deadline_statuses`` is the one place the lateness rule lives. The ``W_DEADLINE`` warning
and a View's deadline mark are both derived from it, so they cannot disagree.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.temporal import as_date


@dataclass(frozen=True)
class DeadlineStatus:
    """One object's promise against its planned finish.

    ``endpoint`` is ``at`` for a point and ``end`` for a span; ``days_late`` is the signed calendar days
    ``finish - deadline`` (positive when the promise is missed, zero when kept on the day, negative slack).
    """

    object_id: str
    deadline: date
    finish: date
    endpoint: str
    days_late: int

    @property
    def slipped(self) -> bool:
        """A finish strictly after the deadline; a finish equal to it keeps the promise."""
        return self.days_late > 0


def deadline_statuses(project: dict[str, Any], placements: dict[str, dict[str, date]]) -> tuple[DeadlineStatus, ...]:
    """One status per object that has a ``deadline`` and a placement, in Project order.

    The finish of a point is ``at``; the finish of a span is ``end``, the stored value that
    ``constraints.end.max`` also compares. An object with no deadline or no placement is skipped.
    """
    statuses = []
    for object_id, item in project.get("objects", {}).items():
        deadline = item.get("deadline")
        placement = placements.get(object_id)
        if deadline is None or not placement:
            continue
        endpoint = "at" if "at" in placement else "end"
        if endpoint not in placement:
            continue
        finish, promised = placement[endpoint], as_date(deadline)
        statuses.append(DeadlineStatus(object_id, promised, finish, endpoint, (finish - promised).days))
    return tuple(statuses)


def deadline_warnings(project: dict[str, Any], placements: dict[str, dict[str, date]]) -> tuple[Diagnostic, ...]:
    """One ``W_DEADLINE`` per object whose planned finish is strictly after its ``deadline``.

    A finish equal to the deadline keeps the promise. Objects come in Project order.
    """
    return tuple(
        Diagnostic(
            "W_DEADLINE",
            f"{status.object_id} finishes {status.finish.isoformat()}, {status.days_late} day{'' if status.days_late == 1 else 's'} "
            f"after its deadline {status.deadline.isoformat()}",
            f"/objects/{status.object_id}/deadline",
            details={"object": status.object_id, "endpoint": status.endpoint, "finish": status.finish.isoformat(),
                     "deadline": status.deadline.isoformat(), "daysLate": status.days_late},
        )
        for status in deadline_statuses(project, placements) if status.slipped)
