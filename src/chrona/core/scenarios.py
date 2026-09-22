"""Pure resolution of Project-owned what-if scenarios."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.core.validation import validate_project


@dataclass(frozen=True)
class ScenarioProvenance:
    scenario_id: str
    title: str | None
    content_identity: str


@dataclass(frozen=True)
class ResolvedScenario:
    project: dict[str, Any]
    provenance: ScenarioProvenance


class ScenarioError(ValueError):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.id)
        self.diagnostic = diagnostic


def resolve_scenario(project: Mapping[str, Any], scenario_id: str) -> ResolvedScenario:
    """Resolve one named hypothesis without mutating the authored Project."""
    scenarios = project.get("scenarios", {})
    scenario = scenarios.get(scenario_id) if isinstance(scenarios, Mapping) else None
    if not isinstance(scenario, Mapping):
        raise ScenarioError(Diagnostic("E_SCENARIO_NOT_FOUND", "Unknown scenario", f"/scenarios/{scenario_id}"))
    derived = deepcopy(dict(project))
    derived.pop("scenarios", None)
    objects = derived.setdefault("objects", {})
    for object_id, override in scenario.get("objects", {}).items():
        path = f"/scenarios/{scenario_id}/objects/{object_id}"
        if override is None:
            if object_id not in objects:
                raise ScenarioError(Diagnostic("E_SCENARIO_OBJECT_NOT_FOUND", "Removed object does not exist", path))
            del objects[object_id]
        elif object_id in objects:
            objects[object_id] = _merge(objects[object_id], override)
        else:
            objects[object_id] = deepcopy(override)
    relations = list(derived.get("relations", []))
    operations = scenario.get("relations", {})
    remove = operations.get("remove", []) if isinstance(operations, Mapping) else []
    known = {item.get("id") for item in relations}
    for relation_id in remove:
        if relation_id not in known:
            raise ScenarioError(Diagnostic("E_SCENARIO_RELATION_NOT_FOUND", "Removed relation does not exist", f"/scenarios/{scenario_id}/relations/remove"))
    relations = [item for item in relations if item.get("id") not in set(remove)]
    for index, relation in enumerate(operations.get("add", []) if isinstance(operations, Mapping) else []):
        relation_id = relation.get("id") if isinstance(relation, Mapping) else None
        if relation_id in {item.get("id") for item in relations}:
            raise ScenarioError(Diagnostic("E_SCENARIO_RELATION_DUPLICATE", "Scenario relation id is duplicate", f"/scenarios/{scenario_id}/relations/add/{index}/id"))
        relations.append(deepcopy(relation))
    derived["relations"] = relations
    diagnostics = validate_project(derived)
    if diagnostics:
        first = diagnostics[0]
        raise ScenarioError(Diagnostic("E_SCENARIO_INVALID", first.message, f"/scenarios/{scenario_id}{first.path}"))
    payload = json.dumps(_json_value(derived), sort_keys=True, separators=(",", ":")).encode()
    return ResolvedScenario(derived, ScenarioProvenance(scenario_id, scenario.get("title"), "sha256:" + sha256(payload).hexdigest()))


def _merge(base: Any, override: Any) -> Any:
    if not isinstance(base, Mapping) or not isinstance(override, Mapping):
        return deepcopy(override)
    output = deepcopy(dict(base))
    for key, value in override.items():
        if value is None:
            output.pop(key, None)
        elif key in output:
            output[key] = _merge(output[key], value)
        else:
            output[key] = deepcopy(value)
    return output


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value
