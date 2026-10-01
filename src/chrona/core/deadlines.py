"""The deadline promise: a stored target compared with the planned finish (#792).

A deadline is not a scheduling bound (Spec 04 Section 10, Q-SCHED-2). Nothing here runs
inside the scheduler: this function reads placements the scheduler already produced and
names each object planned to finish after its deadline. It never moves a placement,
changes a verdict, or rejects a plan.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.temporal import as_date


def deadline_warnings(project: dict[str, Any], placements: dict[str, dict[str, date]]) -> tuple[Diagnostic, ...]:
    """One ``W_DEADLINE`` per object whose planned finish is strictly after its ``deadline``.

    The finish of a point is ``at``; the finish of a span is ``end``, the stored value that
    ``constraints.end.max`` also compares. A finish equal to the deadline keeps the promise.
    Objects come in Project order; an object with no deadline or no placement is skipped.
    """
    warnings = []
    for object_id, item in project.get("objects", {}).items():
        deadline = item.get("deadline")
        placement = placements.get(object_id)
        if deadline is None or not placement:
            continue
        endpoint = "at" if "at" in placement else "end"
        if endpoint not in placement:
            continue
        finish, promised = placement[endpoint], as_date(deadline)
        late = (finish - promised).days
        if late <= 0:
            continue
        warnings.append(Diagnostic(
            "W_DEADLINE",
            f"{object_id} finishes {finish.isoformat()}, {late} day{'' if late == 1 else 's'} after its deadline {promised.isoformat()}",
            f"/objects/{object_id}/deadline",
            details={"object": object_id, "endpoint": endpoint, "finish": finish.isoformat(),
                     "deadline": promised.isoformat(), "daysLate": late},
        ))
    return tuple(warnings)
