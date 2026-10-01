"""Turn a failure into the one diagnostics payload every adapter reports.

The command-line adapter used to own this ladder in ``main()``; it lives here so a
second adapter reports a failure with the same codes, messages, component names and
key order. Nothing here prints, reads arguments or exits: ``report_failure`` maps an
exception to a ``FailureReport`` and the adapter decides how to deliver it.

Exit codes keep their CLI meaning: ``1`` is a rejected input (status ``rejected``),
``2`` a failed invocation or environment (status ``failed``), ``3`` an unreadable
automation result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

import yaml

from chrona.core.diagnostics import Diagnostic
from chrona.core.ports import SnapshotReadError
from chrona.presentation.contracts import PresentationIngressRejected
from chrona.presentation.fonts.importer import FontImportError
from chrona.presentation.icons.importer import IconImportError
from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderFailed, RenderRejected


@dataclass(frozen=True)
class StableFailure(Exception):
    """One failure with a stable code, raised by an adapter or a use case."""

    code: str
    message: str
    component: str = "cli"
    source_ref: str = "/"
    exit_code: int = 1


@dataclass(frozen=True)
class FailureReport:
    """A failure as the payload an adapter prints or returns, and its exit code."""

    status: str
    diagnostics: tuple[dict[str, Any], ...]
    exit_code: int

    def payload(self) -> dict[str, Any]:
        return {"status": self.status, "diagnostics": list(self.diagnostics)}


def diagnostic_record(
    code: str, message: str, component: str, source_ref: str = "/",
    revision_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code, "severity": "error", "component": component,
        "sourceRef": source_ref, "revisionRefs": revision_refs or [], "message": message,
    }


def version_message(detail: str) -> str:
    """Give an unprovenanced stale resource a safe, non-automatic next action."""
    return detail + "; see the current resource schema and migration notes before re-applying edits"


def rejection_report(diagnostics: Sequence[Diagnostic], component: str = "core") -> FailureReport:
    """Report Core diagnostics (a rejected Project or schedule) as one rejected payload."""
    return FailureReport(
        "rejected", tuple(diagnostic_record(item.id, item.message, component, item.path) for item in diagnostics), 1,
    )


def _stable_report(failure: StableFailure) -> FailureReport:
    return FailureReport(
        "rejected" if failure.exit_code == 1 else "failed",
        (diagnostic_record(failure.code, failure.message, failure.component, failure.source_ref),),
        failure.exit_code,
    )


def _presentation_rejection_report(error: PresentationIngressRejected) -> FailureReport:
    """Transport aggregate ingress findings without changing legacy one-error JSON."""
    multiple = len(error.diagnostics) > 1
    diagnostics = []
    for item in error.diagnostics:
        code = f"E_{item.resource_kind.upper().replace('-', '_')}_SCHEMA" if item.code == "E_RESOURCE_SCHEMA" else item.code
        message = version_message(item.message) if code == "E_RESOURCE_VERSION_UNSUPPORTED" else item.message
        diagnostic = diagnostic_record(code, message, "closure", item.pointer)
        if multiple:
            diagnostic |= {"resourceKind": item.resource_kind, "resourceIdentity": item.resource_identity,
                           "phase": item.phase, **({"rule": item.rule} if item.rule is not None else {})}
        diagnostics.append(diagnostic)
    return FailureReport("rejected", tuple(diagnostics), 1)


def report_failure(error: Exception) -> FailureReport:
    """Map an exception raised by a use case or an adapter to its diagnostics payload.

    The order of the checks is the order of the CLI ladder it replaces: several of these
    types share ``ValueError``, so a more specific one must be tested first.
    """
    if isinstance(error, StableFailure):
        return _stable_report(error)
    if isinstance(error, RenderRejected):
        return rejection_report(error.diagnostics, error.component)
    if isinstance(error, RenderFailed):
        return _stable_report(StableFailure(error.code, error.message, error.component, error.source_ref))
    if isinstance(error, PresentationIngressRejected):
        return _presentation_rejection_report(error)
    if isinstance(error, (SnapshotReadError, ClosureError)):
        message = error.detail if error.detail else str(error)
        if isinstance(error, ClosureError) and error.diagnostic_id == "E_RESOURCE_VERSION_UNSUPPORTED":
            message = version_message(message)
        source_ref = error.source_ref if isinstance(error, ClosureError) else "/"
        return _stable_report(StableFailure(error.diagnostic_id, message, "closure", source_ref))
    if isinstance(error, IconImportError):
        return _stable_report(StableFailure(error.code, error.detail, "icon-import", error.source_ref))
    if isinstance(error, FontImportError):
        return _stable_report(StableFailure(error.code, error.detail, "font-import", error.source_ref))
    if isinstance(error, json.JSONDecodeError):
        return _stable_report(StableFailure("E_INPUT_JSON", str(error), exit_code=2))
    if isinstance(error, yaml.YAMLError):
        return _stable_report(StableFailure("E_INPUT_YAML", str(error), exit_code=2))
    if isinstance(error, OSError):
        return _stable_report(StableFailure("E_INPUT_IO", str(error), exit_code=2))
    if isinstance(error, ValueError):
        code = str(error) if str(error).startswith("E_") else "E_PRESENTATION_REJECTED"
        return _stable_report(StableFailure(code, str(error), "presentation"))
    return _stable_report(StableFailure("E_TOOL_FAILURE", str(error), exit_code=2))
