"""Derived, target-independent scene data for presentation adapters."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping



@dataclass(frozen=True)
class Scene:
    """A deterministic projection of canonical Project and schedule data."""

    title: str
    placements: dict[str, dict[str, date]]
    labels: dict[str, str]
    relations: tuple[dict[str, Any], ...]
    description: str


@dataclass(frozen=True)
class FederatedSceneInput:
    """Display-only child summary data, kept outside the canonical Project."""

    nodes: dict[str, dict[str, Any]]


def scene_from_schedule(project: dict[str, Any], placements: Mapping[str, Mapping[str, date]]) -> Scene:
    """Build a Scene without retaining authority to change Project semantics."""
    if not placements:
        raise ValueError("Cannot build a scene without resolved placements")
    title = str(project.get("project", {}).get("title") or project.get("project", {}).get("id", "Chrona timeline"))
    return Scene(
        title=title,
        placements=deepcopy(dict(placements)),
        labels={object_id: str(project.get("objects", {}).get(object_id, {}).get("title") or object_id) for object_id in placements},
        relations=tuple(deepcopy(project.get("relations", []))),
        description="Timeline rendered from Chrona semantic project data.",
    )


def federated_scene_input(plan: dict[str, Any], resolved_exports: dict[str, dict[str, Any]]) -> FederatedSceneInput:
    """Namespace published child objects for Scene consumption only."""
    nodes: dict[str, dict[str, Any]] = {}
    for entry in plan.get("exports", []):
        federation_id = entry["id"]
        namespace = entry["presentation"]["namespace"]
        export = resolved_exports.get(federation_id)
        if export is None:
            continue
        for item in export.get("objects", []):
            node_id = f"{namespace}:{item['id']}"
            nodes[node_id] = {
                "sceneId": f"federation:{federation_id}:{item['id']}",
                "title": item.get("title", item["id"]),
                "schedule": deepcopy(item.get("schedule", {})),
                "progress": item.get("progress"),
                "aggregation": deepcopy(export.get("progressAggregation", {})),
            }
    return FederatedSceneInput(nodes)
