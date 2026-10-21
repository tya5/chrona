"""Validate one resource document by its kind: the check ``chrona validate`` and the MCP ``validate_project`` share.

A Theme, Color Scheme, Layout Profile, View, Style, Actual Set, Summary Profile or Review Detail Profile is checked
against its own schema and contract (#1630, #1854); a Project is the default and is checked by
``usecases.project_checks``. Nothing here reads arguments, prints or exits: a caller gets typed diagnostics.
"""
from __future__ import annotations

import re
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.validation import load_yaml

VALIDATE_RESOURCE_KINDS = ("theme", "color-scheme", "layout-profile", "view", "style", "actual-set",
                           "summary-profile", "review-detail-profile")


def read_document(path: Any) -> Any:
    """The YAML document at ``path`` (the library's own error for a file that cannot be read or parsed)."""
    return load_yaml(path)


def document_kind(value: Any) -> str | None:
    """The kind of a document, or None for a Project; an unknown kind is returned as written (see ``unknown_kind``).

    The ``kind`` member decides; a document without one (a Layout profile, an Actual Set or Detail profile written
    without it) is told by its ``version`` (``chrona/<kind>/vN``). A Project has neither.
    """
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    if kind is None:
        match = re.fullmatch(r"chrona/([a-z][a-z-]*)/v[0-9.]+", str(value.get("version", "")))
        kind = match.group(1) if match else None
    return None if kind is None or kind == "project" else str(kind)


def unknown_kind(kind: str, *, use: str = "") -> Diagnostic | None:
    """``E_CLOSURE_KIND`` naming the accepted kinds when ``kind`` is not one validate checks, else None."""
    if kind in VALIDATE_RESOURCE_KINDS:
        return None
    accepted = ", ".join(("project",) + VALIDATE_RESOURCE_KINDS)
    return Diagnostic("E_CLOSURE_KIND", f"validate does not check a document of kind {kind!r}; "
                      f"the accepted kinds are {accepted}{use}", "/kind")


def validate_resource_mapping(kind: str, value: dict[str, Any], layout_defaults: Any = None) -> tuple[Diagnostic, ...]:
    """That kind's schema and contract findings; a View first takes the Layout profile's ``viewDefaults`` under it."""
    from chrona.presentation.contracts.resources import (
        ClosureIdentity, ContractError, explain_schema_errors, parse_contract,
    )
    identity = ClosureIdentity(kind, str(value.get("id", kind)), "", "")
    if kind == "view" and isinstance(layout_defaults, dict):
        from chrona.presentation.contracts.view_defaults import merge_view_defaults
        value = merge_view_defaults(value, layout_defaults)
    try:
        violations = explain_schema_errors(identity, value)
        if violations:
            return tuple(Diagnostic("E_SCHEMA", item.message, item.pointer) for item in violations)
        parse_contract(identity, value)
    except ContractError as error:
        violation = getattr(error, "violation", None)
        code = "E_SCHEMA" if violation is not None else str(error.diagnostic_id).split(":")[0]
        message = violation.message if violation is not None else (error.detail or str(error.diagnostic_id))
        return (Diagnostic(code, message, error.source_ref),)
    return ()
