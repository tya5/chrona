"""Validate one resource document by its kind: the check ``chrona validate`` and the MCP ``validate_project`` share.

A Theme, Color Scheme, Layout Profile, View, Style, Actual Set, Summary Profile or Review Detail Profile is checked
against its own schema and contract (#1630, #1854); a Project is the default and is checked by
``usecases.project_checks``. Nothing here reads arguments, prints or exits: a caller gets typed diagnostics.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.store_address import StoreAddressError, resolve_store_address
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


# A preset's declared members, in the order their findings are reported: (resources key, kind).
_PRESET_MEMBERS = (("view", "view"), ("style", "style"), ("theme", "theme"), ("colorScheme", "color-scheme"),
                   ("layout", "layout-profile"), ("detailProfile", "review-detail-profile"),
                   ("summaryProfile", "summary-profile"))


def _member_path(root: Path, declaration: Any) -> Path | None:
    if not isinstance(declaration, dict) or not isinstance(declaration.get("path"), str):
        return None
    try:
        return resolve_store_address(root, declaration["path"])
    except StoreAddressError:
        return None


def preset_members(preset_path: Path, preset: Any) -> list[tuple[str, Path, str]]:
    """The (declared path, file, kind) of each member a preset declares, compatible Color Schemes included."""
    if not isinstance(preset, dict) or not isinstance(preset.get("body"), dict):
        return []
    body, found = preset["body"], []
    resources = body.get("resources") if isinstance(body.get("resources"), dict) else {}
    declarations = [(resources.get(key), kind) for key, kind in _PRESET_MEMBERS]
    declarations += [(item, "color-scheme") for item in body.get("compatibleColorSchemes") or () if isinstance(item, dict)]
    for declaration, kind in declarations:
        path = _member_path(preset_path.parent, declaration)
        if path is not None and all(path != item[1] for item in found):
            found.append((declaration["path"], path, kind))
    return found


def preset_layout_defaults(preset_path: Path, preset: Any) -> Any:
    """The ``viewDefaults`` of the Layout profile a preset declares (None without one)."""
    for _, path, kind in preset_members(preset_path, preset):
        if kind == "layout-profile":
            layout = read_document(path)
            return layout.get("viewDefaults") if isinstance(layout, dict) else None
    return None


def sibling_preset_defaults(view_path: Path) -> tuple[Path, Any] | None:
    """The ``preset.yaml`` next to a View that declares it as its view, with that preset's Layout defaults, else None."""
    candidate = view_path.parent / "preset.yaml"
    if not candidate.is_file():
        return None
    try:
        preset = read_document(candidate)
        declared = [path for _, path, kind in preset_members(candidate, preset) if kind == "view"]
        if view_path.resolve() not in [path.resolve() for path in declared]:
            return None
        return candidate, preset_layout_defaults(candidate, preset)
    except Exception:  # an unreadable sibling is not this View's preset; validate the View on its own
        return None


def validate_preset_closure(preset_path: Path, preset: Any) -> tuple[Diagnostic, ...]:
    """The preset's own findings, then every member file's, the View after its Layout's ``viewDefaults`` merge (Spec 06).

    Each member finding names the member file in its message and in its pointer (``view.yaml#/body/markers/0``).
    """
    found = list(validate_resource_mapping("presentation-preset", preset))
    if found:
        return tuple(found)
    defaults = preset_layout_defaults(preset_path, preset)
    for declared, path, kind in preset_members(preset_path, preset):
        document = read_document(path)
        if not isinstance(document, dict):
            found.append(Diagnostic("E_SCHEMA", f"{declared}: expected a mapping document", f"{declared}#/"))
            continue
        for item in validate_resource_mapping(kind, document, defaults if kind == "view" else None):
            found.append(Diagnostic(item.id, f"{declared}: {item.message}", f"{declared}#{item.path or '/'}"))
    return tuple(found)
