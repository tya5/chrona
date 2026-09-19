"""Derived, target-independent scene data for presentation adapters."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from typing import Any

from .scheduler import ScheduleResult


@dataclass(frozen=True)
class Scene:
    """A deterministic projection of canonical Project and schedule data."""

    title: str
    placements: dict[str, dict[str, date]]
    labels: dict[str, str]
    relations: tuple[dict[str, Any], ...]
    description: str


def scene_from_schedule(project: dict[str, Any], result: ScheduleResult) -> Scene:
    """Build a Scene without retaining authority to change Project semantics."""
    if not result.ok or not result.placements:
        raise ValueError("Cannot build a scene without resolved placements")
    title = str(project.get("project", {}).get("title") or project.get("project", {}).get("id", "Chrona timeline"))
    return Scene(
        title=title,
        placements=deepcopy(result.placements),
        labels={object_id: str(project.get("objects", {}).get(object_id, {}).get("title") or object_id) for object_id in result.placements},
        relations=tuple(deepcopy(project.get("relations", []))),
        description="Timeline rendered from Chrona semantic project data.",
    )
