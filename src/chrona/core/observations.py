"""Neutral selection of already validated Actual observations."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def latest_observations(
    observations: Sequence[Mapping[str, Any]], placements: Mapping[str, object],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    """Select the greatest sequence; keep the first on a tie and unmatched order.

    Validation owns sequence validity. Selection does not parse dates, filter by
    as-of, sort unmatched identities, or change the winning observation.
    """
    latest: dict[str, Mapping[str, Any]] = {}
    unmatched: list[str] = []
    for observation in observations:
        object_id = observation.get("projectObjectId")
        if object_id not in placements:
            unmatched.append(observation["id"])
        elif object_id not in latest or observation["sequence"] > latest[object_id]["sequence"]:
            latest[object_id] = observation
    return latest, unmatched
