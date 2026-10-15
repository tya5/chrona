"""Project-owned semantic bindings for View references to object fields."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


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
        as ``None``; callers can use :meth:`field_for` to distinguish them.
        """
        if fields is None:
            return None
        if "field" in source:
            key = source.get("field")
        elif "fieldRole" in source:
            role = source.get("fieldRole")
            key = self.field_for(role) if isinstance(role, str) else None
        else:
            return None
        return fields.get(key) if isinstance(key, str) else None
