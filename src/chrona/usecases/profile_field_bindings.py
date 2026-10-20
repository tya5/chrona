"""Adapt one source Project's resolved extension declarations to presentation facts."""
from __future__ import annotations

from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.extensions.profiles import (
    reference_constraint_for_field,
    resolve_profile_field_catalogue_with_owners,
)
from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings


def resolve_source_field_bindings(
    project: dict[str, Any], manifests: dict[str, dict[str, Any]],
) -> tuple[FieldRoleBindings, tuple[Diagnostic, ...]]:
    """Keep declaration interpretation in extensions and identity in the source.

    Values are never inspected to infer a descriptor. Optional declarations
    therefore remain available even when every current object value is absent.
    The caller resolves manifests through that source's immutable closure.
    """
    catalogue, owners, diagnostics = resolve_profile_field_catalogue_with_owners(project, manifests)
    descriptors = {}
    for object_id, item in project.get("objects", {}).items():
        definitions = catalogue.get(item.get("type"))
        if definitions is None:
            continue
        profile_id = item.get("type")
        owner_package_id = owners.get(profile_id, "")
        descriptors[object_id] = tuple(
            _field_descriptor(owner_package_id, profile_id, name, definition)
            for name, definition in definitions.items()
        )
    return FieldRoleBindings.from_project(project, object_descriptors=descriptors), tuple(diagnostics)


def _field_descriptor(
    owner_package_id: str,
    profile_id: str,
    name: str,
    definition: dict[str, Any],
) -> FieldDescriptor:
    constraint = reference_constraint_for_field(owner_package_id, profile_id, name, definition)
    return FieldDescriptor(
        name,
        definition["type"],
        definition.get("cardinality", "one"),
        tuple(definition.get("enumValues", ())),
        definition.get("default"),
        "default" in definition,
        constraint.target_profiles,
        constraint.target_namespaces,
    )
