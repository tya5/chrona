"""Project-owned semantic bindings for View references to object fields."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldRead:
    """One source-local field lookup, keeping absence distinct from null."""

    field_name: str | None
    present: bool
    value: Any


@dataclass(frozen=True)
class FieldRoleBindings:
    """Immutable role-to-object-field bindings from one source Project.

    Resource validation owns the finite role vocabulary and mapping shape. This
    model object only carries the already-validated bindings so each projected
    source can resolve roles against its own Project without rewriting fields.
    """

    bindings: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_project(cls, project: Mapping[str, Any]) -> "FieldRoleBindings":
        """Capture a Project's optional ``fieldRoles`` mapping immutably."""
        declared = project.get("fieldRoles", {})
        if not isinstance(declared, Mapping):
            return cls()
        pairs = tuple(sorted(
            (role, field_name)
            for role, field_name in declared.items()
            if isinstance(role, str) and isinstance(field_name, str)
        ))
        return cls(pairs)

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
                    source: Mapping[str, Any]) -> FieldRead:
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
        return FieldRead(field_name, present, fields[field_name] if present else None)
