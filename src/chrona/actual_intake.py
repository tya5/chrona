"""External Actual intake without schedule or implicit-alignment authority.

The adapter converts already-parsed source facts into the independently versioned
``actual-set`` body defined by the Presentation Format.  A source fact is matched
only when its caller supplies a stable Project object ID that belongs to the named
Project.  Titles and all other descriptive fields are deliberately ignored.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class IntakeResult:
    """A review handoff; it is not a Project mutation or a scheduling result."""

    observations: tuple[dict[str, Any], ...]
    resolved: tuple[str, ...]
    unmatched: tuple[str, ...]
    diagnostics: tuple[str, ...]


def intake_actual_observations(
    source_system: str,
    records: Iterable[Mapping[str, Any]],
    project_object_ids: Iterable[str],
) -> IntakeResult:
    """Create resolved or explicitly-unmatched Actual observations.

    Every record must carry a source-stable ``externalKey`` and a non-empty
    ``actual`` mapping.  ``projectObjectId`` is optional.  It is honored only when
    it identifies one of ``project_object_ids``; otherwise the record remains
    unmatched for a later ``resolveActualObservation`` Command.
    """
    if not isinstance(source_system, str) or not source_system:
        raise ValueError("source_system must be a non-empty string")

    known_ids = frozenset(project_object_ids)
    observations: list[dict[str, Any]] = []
    resolved: list[str] = []
    unmatched: list[str] = []
    diagnostics: list[str] = []
    seen: set[tuple[str, str | int]] = set()

    for sequence, record in enumerate(records, start=1):
        key = record.get("externalKey")
        actual = record.get("actual")
        if not isinstance(key, (str, int)) or isinstance(key, bool) or not isinstance(actual, Mapping) or not actual:
            raise ValueError("record requires externalKey and non-empty actual")
        identity = (source_system, key)
        if identity in seen:
            raise ValueError("duplicate external identity")
        seen.add(identity)

        observation_id = f"{source_system}:{key}"
        object_id = record.get("projectObjectId")
        observation: dict[str, Any] = {
            "id": observation_id,
            "sequence": sequence,
            "actual": deepcopy(dict(actual)),
        }
        if isinstance(object_id, str) and object_id in known_ids:
            observation["projectObjectId"] = object_id
            resolved.append(observation_id)
        else:
            observation["externalIdentity"] = {"system": source_system, "key": key}
            observation["alignment"] = "unmatched"
            unmatched.append(observation_id)
            diagnostics.append("E_ACTUAL_UNMATCHED")
        observations.append(observation)

    return IntakeResult(
        observations=tuple(observations),
        resolved=tuple(resolved),
        unmatched=tuple(unmatched),
        diagnostics=tuple(sorted(set(diagnostics))),
    )
