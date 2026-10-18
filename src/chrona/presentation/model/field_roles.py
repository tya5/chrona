"""Project-owned semantic bindings for View references to object fields."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class FieldDescriptor:
    """Typed source-local declaration for one Project object field.

    This is a detached snapshot of already-validated metadata. It does not
    inspect or infer a declaration from an object's current value.
    """

    name: str
    kind: str
    cardinality: str = "one"
    enum_values: tuple[str, ...] = ()
    default: Any = None
    has_default: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "enum_values", tuple(self.enum_values))


@dataclass(frozen=True)
class FieldRead:
    """One source-local field lookup, keeping absence distinct from null."""

    field_name: str | None
    present: bool
    value: Any
    descriptor: FieldDescriptor | None = None
    defaulted: bool = False  # the value is the declared profile default of an absent field (#1682)


@dataclass(frozen=True)
class FieldRoleBindings:
    """Immutable role-to-object-field bindings from one source Project.

    Resource validation owns the finite role vocabulary and mapping shape. This
    model object only carries the already-validated bindings so each projected
    source can resolve roles against its own Project without rewriting fields.
    """

    bindings: tuple[tuple[str, str], ...] = ()
    object_descriptors: tuple[tuple[str, tuple[FieldDescriptor, ...]], ...] = ()
    _descriptor_lookup: Mapping[str, Mapping[str, FieldDescriptor]] = field(
        init=False, repr=False, compare=False,
    )

    def __post_init__(self) -> None:
        # Snapshot collection inputs so even direct construction cannot retain
        # mutable binding/descriptor containers.
        object.__setattr__(self, "bindings", tuple(tuple(pair) for pair in self.bindings))
        raw = self.object_descriptors
        entries = raw.items() if isinstance(raw, Mapping) else raw
        frozen_entries = []
        object_ids: set[str] = set()
        for object_id, descriptors in entries:
            if object_id in object_ids:
                raise ValueError(f"duplicate object descriptor set for {object_id!r}")
            object_ids.add(object_id)
            frozen_descriptors = tuple(
                descriptor if isinstance(descriptor, FieldDescriptor)
                else FieldDescriptor(*descriptor)
                for descriptor in descriptors
            )
            names = [descriptor.name for descriptor in frozen_descriptors]
            if len(set(names)) != len(names):
                raise ValueError(f"duplicate field descriptor for object {object_id!r}")
            frozen_entries.append((object_id, frozen_descriptors))
        object.__setattr__(self, "object_descriptors", tuple(frozen_entries))
        lookup = {
            object_id: MappingProxyType({descriptor.name: descriptor for descriptor in descriptors})
            for object_id, descriptors in frozen_entries
        }
        object.__setattr__(self, "_descriptor_lookup", MappingProxyType(lookup))

    @classmethod
    def from_project(
        cls,
        project: Mapping[str, Any],
        *,
        object_descriptors: Mapping[str, Any] | tuple[tuple[str, Any], ...] = (),
    ) -> "FieldRoleBindings":
        """Capture a Project's optional ``fieldRoles`` mapping immutably."""
        declared = project.get("fieldRoles", {})
        if not isinstance(declared, Mapping):
            return cls(object_descriptors=object_descriptors)
        pairs = tuple(sorted(
            (role, field_name)
            for role, field_name in declared.items()
            if isinstance(role, str) and isinstance(field_name, str)
        ))
        return cls(pairs, object_descriptors)

    def field_for(self, role: str) -> str | None:
        """Return the declared object-field key for ``role``, if any."""
        return next((field_name for declared_role, field_name in self.bindings
                     if declared_role == role), None)

    def read(self, fields: Mapping[str, Any] | None,
             source: Mapping[str, Any]) -> Any:
        """Read a direct-field or semantic-role source without changing fields.

        An undeclared role and a declared field whose value is absent both read
        as ``None``; callers needing that distinction should use
        :meth:`read_result`.
        """
        return self.read_result(fields, source).value

    def read_result(self, fields: Mapping[str, Any] | None,
                    source: Mapping[str, Any], *,
                    object_id: str | None = None) -> FieldRead:
        """Resolve and read one direct field or role, preserving presence.

        ``field_name`` is ``None`` when a role is undeclared or the source does
        not identify a field. Otherwise ``present`` distinguishes a missing key
        from a key explicitly mapped to ``None``; ``value`` is the raw value.
        """
        if "field" in source:
            field_name = source.get("field")
        elif "fieldRole" in source:
            role = source.get("fieldRole")
            field_name = self.field_for(role) if isinstance(role, str) else None
        else:
            field_name = None
        if not isinstance(field_name, str):
            return FieldRead(None, False, None)
        present = fields is not None and field_name in fields
        descriptor = self.descriptor_for(object_id, field_name)
        if not present and descriptor is not None and descriptor.has_default:
            # The one fill path: an absent declared field reads its profile default, for every consumer of this source.
            return FieldRead(field_name, True, descriptor.default, descriptor, True)
        return FieldRead(field_name, present, fields[field_name] if present else None,
                         descriptor)

    def descriptor_for(self, object_id: str | None,
                       field_name: str) -> FieldDescriptor | None:
        """Return the declaration for this exact object and resolved field."""
        if object_id is None:
            return None
        return self._descriptor_lookup.get(object_id, {}).get(field_name)

    def descriptors_for(self, object_id: str | None) -> tuple[FieldDescriptor, ...]:
        """Return declared fields for one exact source object in declaration order."""
        if object_id is None:
            return ()
        return tuple(self._descriptor_lookup.get(object_id, {}).values())
