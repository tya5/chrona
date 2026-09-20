"""M11-1 Date-only capacity validation and derived overload reporting."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
import json
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.scheduling.scheduler import schedule
from chrona.core.temporal import as_date


@dataclass(frozen=True)
class CapacityResult:
    diagnostics: tuple[Diagnostic, ...]
    overloads: tuple[dict[str, Any], ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True)
class LevelingResult:
    diagnostics: tuple[Diagnostic, ...]
    proposal: dict[str, Any] | None


def evaluate_capacity(project: dict[str, Any], capacity: dict[str, Any]) -> CapacityResult:
    """Derive daily overloads without changing the Project or schedule."""
    scheduled = schedule(project)
    diagnostics = list(scheduled.diagnostics)
    if diagnostics:
        return CapacityResult(tuple(diagnostics), ())
    resources = {item.get("id"): item for item in capacity.get("resources", [])}
    availability: dict[tuple[str, object], float] = {}
    for index, item in enumerate(capacity.get("availability", [])):
        key = (item.get("resourceId"), item.get("date"))
        if key in availability:
            diagnostics.append(Diagnostic("E_CAPACITY_AVAILABILITY", "Duplicate resource/day availability", f"/availability/{index}"))
            continue
        availability[key] = item.get("amount", 0)
    demand: dict[tuple[str, object], float] = defaultdict(float)
    for index, assignment in enumerate(capacity.get("assignments", [])):
        resource = resources.get(assignment.get("resourceId"))
        object_id = assignment.get("objectId")
        if resource is None or object_id not in scheduled.placements:
            diagnostics.append(Diagnostic("E_REFERENCE", "Assignment reference is unavailable", f"/assignments/{index}")); continue
        if resource.get("unit") != assignment.get("unit"):
            diagnostics.append(Diagnostic("E_RESOURCE_UNIT_MISMATCH", "Assignment and resource units differ", f"/assignments/{index}/unit")); continue
        placement = scheduled.placements[object_id]
        if "start" not in placement or "end" not in placement:
            continue
        day = placement["start"]
        while day < placement["end"]:
            demand[(resource["id"], day)] += assignment["demand"]
            day += timedelta(days=1)
    overloads = tuple({"resourceId": resource_id, "date": day.isoformat(), "demand": amount, "availability": availability.get((resource_id, day.isoformat()), 0)} for (resource_id, day), amount in sorted(demand.items()) if amount > availability.get((resource_id, day.isoformat()), 0))
    if overloads:
        diagnostics.append(Diagnostic("E_CAPACITY_OVERLOAD", "Capacity demand exceeds explicit availability"))
    return CapacityResult(tuple(diagnostics), overloads)


def _fingerprint(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def evaluate_leveling(store: Any, capacity: dict[str, Any], movement_scope: tuple[str, ...], objective: str = "minimize-lateness-then-stable-id") -> LevelingResult:
    """Return a derived, forward-only proposal; this function never writes the store."""
    if objective != "minimize-lateness-then-stable-id":
        return LevelingResult((Diagnostic("E_LEVELING_OBJECTIVE", "Unsupported leveling objective"),), None)
    snapshot = store.read()
    initial = evaluate_capacity(snapshot.project, capacity)
    non_overload = tuple(item for item in initial.diagnostics if item.id != "E_CAPACITY_OVERLOAD")
    if non_overload or not initial.overloads:
        return LevelingResult(non_overload, None)
    candidate = deepcopy(snapshot.project)
    changes: list[dict[str, str]] = []
    for object_id in sorted(movement_scope, key=lambda item: (schedule(candidate).placements.get(item, {}).get("start"), item)):
        raw = candidate.get("objects", {}).get(object_id, {}).get("schedule", {})
        placement = schedule(candidate).placements.get(object_id, {})
        if raw.get("mode") != "scheduled" or raw.get("anchor") or "start" not in placement:
            return LevelingResult((Diagnostic("E_LEVELING_IMMOVABLE", "Proposal would move a fixed or anchored object", f"/objects/{object_id}"),), None)
        start = placement["start"]
        for _ in range(366):
            start += timedelta(days=1)
            trial = deepcopy(candidate)
            trial["objects"][object_id]["schedule"]["anchor"] = {"start": start.isoformat()}
            result = evaluate_capacity(trial, capacity)
            if not result.diagnostics:
                candidate = trial
                changes.append({"objectId": object_id, "start": start.isoformat()})
                break
        else:
            return LevelingResult((Diagnostic("E_CAPACITY_OVERLOAD", "No feasible forward placement exists"),), None)
    final = evaluate_capacity(candidate, capacity)
    if final.diagnostics:
        return LevelingResult((Diagnostic("E_CAPACITY_OVERLOAD", "Movement scope cannot resolve capacity overload"),), None)
    payload = {"baseRevision": snapshot.revision, "baseContentIdentity": snapshot.content_identity, "capacity": capacity, "objective": objective, "movementScope": list(movement_scope), "changes": changes}
    fingerprint = _fingerprint(payload)
    return LevelingResult((), {"id": f"level:sha256:{fingerprint}", "fingerprint": fingerprint, **payload})


def apply_leveling_proposal(store: Any, proposal: dict[str, Any], capacity: dict[str, Any]) -> tuple[str, tuple[Diagnostic, ...]]:
    """Accept only an unaltered proposal at its evaluated Project revision."""
    snapshot = store.read()
    if snapshot.revision != proposal.get("baseRevision"):
        return "rejected", (Diagnostic("E_COMMAND_STALE_BASE_REVISION", "Project revision changed"),)
    payload = {key: proposal.get(key) for key in ("baseRevision", "baseContentIdentity", "capacity", "objective", "movementScope", "changes")}
    if proposal.get("capacity") != capacity or proposal.get("fingerprint") != _fingerprint(payload) or proposal.get("id") != f"level:sha256:{proposal.get('fingerprint')}":
        return "rejected", (Diagnostic("E_LEVELING_PROPOSAL", "Proposal fingerprint does not match"),)
    candidate = deepcopy(snapshot.project)
    scope = set(proposal["movementScope"])
    for change in proposal["changes"]:
        object_id = change.get("objectId")
        raw = candidate.get("objects", {}).get(object_id, {}).get("schedule", {})
        if object_id not in scope or raw.get("mode") != "scheduled" or raw.get("anchor"):
            return "rejected", (Diagnostic("E_LEVELING_IMMOVABLE", "Proposal change is not movable", f"/objects/{object_id}"),)
        raw["anchor"] = {"start": change.get("start")}
    if not schedule(candidate).ok or evaluate_capacity(candidate, capacity).diagnostics:
        return "rejected", (Diagnostic("E_CAPACITY_OVERLOAD", "Proposal no longer yields a valid feasible schedule"),)
    return ("accepted", ()) if store.write(snapshot.revision, candidate) is not None else ("rejected", (Diagnostic("E_COMMAND_STALE_BASE_REVISION", "Project revision changed"),))
