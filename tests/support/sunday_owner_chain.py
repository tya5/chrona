"""Synthetic owner-lane chain used for Sunday route-search diagnostics."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

from tests.support import synthetic_review as sr


def sunday_owner_chain_project(*, chained: bool = True, owners: int = 9,
                              gap_days: int = 0) -> dict[str, Any]:
    """Build 22 fixed-span tasks with repeated owners and an optional FS chain."""
    if owners < 1:
        raise ValueError("owners must be at least 1")

    first_start = date(2026, 11, 2)
    objects = {
        f"task-{index:02}": sr.span(
            f"task-{index:02}", first_start + timedelta(days=index * (3 + gap_days)), 3,
            owner=f"owner-{index % owners:02}", title=f"Synthetic task {index:02}",
        )
        for index in range(22)
    }
    relations = (
        [
            {
                "id": f"r-{index:02}",
                "type": "dependency",
                "lag": "0d",
                "from": {"object": f"task-{index - 1:02}", "endpoint": "end"},
                "to": {"object": f"task-{index:02}", "endpoint": "start"},
            }
            for index in range(1, 22)
        ]
        if chained else []
    )
    return sr.project(objects, relations)


def sunday_owner_chain_comparisons(
    source: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a two-day-earlier Snapshot and three-observation Actual Set."""
    snapshot = deepcopy(source)
    for item in snapshot["objects"].values():
        schedule = item["schedule"]
        if schedule.get("mode") != "fixed-span":
            raise ValueError("comparison fixture requires fixed-span source tasks")
        schedule["start"] = (date.fromisoformat(schedule["start"]) - timedelta(days=2)).isoformat()
        schedule["end"] = (date.fromisoformat(schedule["end"]) - timedelta(days=2)).isoformat()

    observations = []
    for index in range(3):
        object_id = f"task-{index:02}"
        planned = source["objects"][object_id]["schedule"]
        actual = {"start": planned["start"]}
        if index < 2:
            actual.update(finish=planned["end"], progress=1.0)
        else:
            actual["progress"] = 0.3
        observations.append({
            "id": f"observation-{index:02}",
            "sequence": index + 1,
            "projectObjectId": object_id,
            "actual": actual,
        })
    actual_set = {
        "version": "chrona/actual-set/v0.3",
        "kind": "actual-set",
        "id": "sunday-owner-chain-actuals",
        "body": {"asOf": "2026-11-16", "observations": observations},
    }
    return snapshot, actual_set
