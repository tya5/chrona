"""Read-only interactive projection and SceneDelta reconciliation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InteractiveScene:
    evaluation_fingerprint: str
    generation: int
    nodes: dict[str, dict[str, Any]]
    tokens: dict[str, Any]
    viewport: dict[str, Any]


@dataclass(frozen=True)
class DeltaResult:
    status: str
    scene: InteractiveScene
    diagnostics: tuple[str, ...]


def plan_actual_review(placements: dict[str, dict[str, Any]], actual_set: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    """Derive comparison facets without inventing missing actual dates or forecasts."""
    rows: dict[str, dict[str, Any]] = {}
    diagnostics: list[str] = []
    for observation in actual_set.get("observations", []):
        object_id = observation.get("projectObjectId")
        if not object_id or object_id not in placements:
            diagnostics.append("E_ACTUAL_UNMATCHED")
            continue
        actual = deepcopy(observation.get("actual", {}))
        rows[object_id] = {"planned": deepcopy(placements[object_id]), "actual": actual, "variance": "known" if actual else "unknown"}
    return rows, tuple(sorted(set(diagnostics)))


def accessible_scene_summary(scene: InteractiveScene) -> str:
    """Text alternative for a completed, derived Scene projection."""
    labels = [str(node.get("title") or scene_id) for scene_id, node in sorted(scene.nodes.items())]
    return f"Interactive timeline with {len(labels)} items: " + ", ".join(labels)


def apply_scene_delta(scene: InteractiveScene, delta: dict[str, Any]) -> DeltaResult:
    """Atomically reconcile derived interactive state; never accepts Project data."""
    if delta.get("baseEvaluationFingerprint") != scene.evaluation_fingerprint or delta.get("baseGeneration") != scene.generation:
        return DeltaResult("resync-required", scene, ("E_SCENE_DELTA_BASE_MISMATCH",))
    if delta.get("replaceScope") == "scene" and delta.get("reason") not in {"viewport-reflow", "scale-change"}:
        return DeltaResult("rejected", scene, ("E_SCENE_DELTA_SCOPE",))
    nodes, tokens, viewport = deepcopy(scene.nodes), deepcopy(scene.tokens), deepcopy(scene.viewport)
    for operation in delta.get("operations", []):
        op, scene_id = operation.get("op"), operation.get("sceneId")
        if op == "upsert":
            nodes[scene_id] = deepcopy(operation["node"])
        elif op == "remove":
            nodes.pop(scene_id, None)
        elif op == "tokenUpdate":
            tokens[operation["token"]] = deepcopy(operation.get("value"))
        elif op == "viewportUpdate":
            viewport = deepcopy(operation["viewport"])
        elif op == "reorder":
            if scene_id in nodes:
                nodes[scene_id]["order"] = operation["order"]
        else:
            return DeltaResult("rejected", scene, ("E_SCENE_DELTA_OPERATION",))
    return DeltaResult("applied", InteractiveScene(delta["targetEvaluationFingerprint"], delta["targetGeneration"], nodes, tokens, viewport), ())
