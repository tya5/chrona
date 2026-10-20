"""Source-local resolution for declarative object references (#344)."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class ObjectReferenceTarget:
    """Detached identity and display fact for one addressable source target."""

    identity: tuple[str, str, str]
    display_title: str
    profile_id: str | None


class ObjectReferenceError(ValueError):
    """A bare reference did not select exactly one permitted target."""

    def __init__(self, reason: str, value: object):
        self.reason = reason
        self.value = value
        super().__init__(f"object reference {value!r} is {reason}")


@dataclass(frozen=True)
class ObjectReferenceCatalog:
    """Immutable target snapshot for a single logical Project source.

    The catalogue retains only canonical IDs, namespaces, profiles, and display
    titles. It deliberately does not retain the input Project mapping.
    """

    logical_project_id: str
    targets: tuple[ObjectReferenceTarget, ...]
    _by_id: Mapping[str, tuple[ObjectReferenceTarget, ...]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Freeze the public collection and build the lookup once per source.
        targets = tuple(self.targets)
        by_id: dict[str, list[ObjectReferenceTarget]] = {}
        for target in targets:
            by_id.setdefault(target.identity[2], []).append(target)
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "_by_id", MappingProxyType({key: tuple(items) for key, items in by_id.items()}))

    @classmethod
    def from_project(cls, project: Mapping[str, Any]) -> ObjectReferenceCatalog:
        project_header = project.get("project")
        logical_project_id = project_header.get("id") if isinstance(project_header, Mapping) else None
        if not isinstance(logical_project_id, str) or not logical_project_id:
            raise ValueError("Project must have a logical project ID before resolving object references")

        targets: list[ObjectReferenceTarget] = []
        for namespace in ("entities", "objects"):
            members = project.get(namespace, {})
            if not isinstance(members, Mapping):
                continue
            for target_id, member in members.items():
                if not isinstance(target_id, str) or not isinstance(member, Mapping):
                    continue
                profile_id = member.get("type")
                profile_id = profile_id if isinstance(profile_id, str) else None
                title = member.get("title")
                display_title = title if isinstance(title, str) and title.strip() else target_id
                targets.append(ObjectReferenceTarget(
                    identity=(logical_project_id, namespace, target_id),
                    display_title=display_title,
                    profile_id=profile_id,
                ))
        return cls(logical_project_id, tuple(targets))

    def resolve(
        self,
        value: object,
        *,
        target_profiles: tuple[str, ...] | list[str] = (),
    ) -> ObjectReferenceTarget:
        """Resolve a bare ID, applying its declared profile constraint first."""
        if not isinstance(value, str) or not value:
            raise ObjectReferenceError("invalid", value)
        candidates = self._by_id.get(value, ())
        if not candidates:
            raise ObjectReferenceError("missing", value)

        if target_profiles:
            allowed = frozenset(target_profiles)
            candidates = tuple(target for target in candidates if target.profile_id in allowed)
            if not candidates:
                raise ObjectReferenceError("incompatible", value)

        if len(candidates) != 1:
            raise ObjectReferenceError("ambiguous", value)
        return candidates[0]
