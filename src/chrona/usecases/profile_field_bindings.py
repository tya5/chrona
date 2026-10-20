"""Adapt one source Project's resolved extension declarations to presentation facts."""
from __future__ import annotations

from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.extensions.profiles import resolve_profile_field_catalogue
from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings


def resolve_source_field_bindings(
    project: dict[str, Any], manifests: dict[str, dict[str, Any]],
) -> tuple[FieldRoleBindings, tuple[Diagnostic, ...]]:
    """Keep declaration interpretation in extensions and identity in the source.

    Values are never inspected to infer a descriptor. Optional declarations
    therefore remain available even when every current object value is absent.
    The caller resolves manifests through that source's immutable closure.
    """
    catalogue, diagnostics = resolve_profile_field_catalogue(project, manifests)
    descriptors = {}
    for object_id, item in project.get("objects", {}).items():
        definitions = catalogue.get(item.get("type"))
        if definitions is None:
            continue
        descriptors[object_id] = tuple(
            FieldDescriptor(name, definition["type"], definition.get("cardinality", "one"),
                            tuple(definition.get("enumValues", ())),
                            definition.get("default"), "default" in definition,
                            tuple(definition.get("targetProfiles", ())))
            for name, definition in definitions.items()
        )
    return FieldRoleBindings.from_project(project, object_descriptors=descriptors), tuple(diagnostics)
