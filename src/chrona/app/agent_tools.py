"""The SDK-free agent tools: a registry of tools over the use cases, and their result contract.

Four read-only tools front the use cases an agent needs to plan and draw a schedule:
``validate_project``, ``schedule_project``, ``render_draft`` and ``list_presets``; two read-only tools read a
Store, ``render_review`` and ``compare_baseline`` (#812); two tools front the revision-bound Store commands,
``check_command`` (read-only) and ``apply_command`` (writes, only when the caller passes ``allow_write``; #813).
Tool set ``chrona/agent-tools/v0.4``, Spec 66. A tool is a use case
with a typed envelope: ``call_tool(scope, name, arguments)`` validates the arguments against the
tool's input schema, runs the use case on files inside a ``WorkspaceScope`` and returns a
``ToolResult`` whose ``structured`` mapping is the envelope (``status``, ``diagnostics``)
plus the tool's own fields. A transport adapter (the MCP binding) only moves that result.

This module imports no SDK and prints nothing. The one tool that writes, ``apply_command``, writes only
through the shared dispatch of the Store commands (``operational.store_commands``) into Store roots that lie
inside the workspace; every other tool writes nothing. The Store tools reach a Store through that module's
``open_store_reader`` and ``operational.store_reads`` (the two operational modules a tool may import), and a Store
root outside the workspace is refused before anything is read from it.
Failures reach the caller as typed diagnostics through ``usecases.failure_report``, never as a traceback,
and every mapping it returns is sorted so a result is a pure function of the workspace bytes and the
arguments.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
from dataclasses import dataclass, replace
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jsonschema.exceptions import best_match

from chrona.app.agent_workspace import WorkspaceScope
from chrona.operational.store_commands import (
    StoreRootOutsideWorkspace, open_store_reader, parse_command_request, run_store_command,
)
from chrona.operational.store_reads import compare_store_baseline, load_reference, snapshot_reader_for
from chrona.resources import validator_for_schema
from chrona.usecases.context_review import render_context_closure, resolve_context_closure
from chrona.usecases.draft_render import DEFAULT_VIEWPORT, DraftRenderRequest, render_draft, warning_payloads
from chrona.usecases.failure_report import (
    FailureReport, StableFailure, collapse_records, diagnostic_record, rejection_report, report_failure,
)
from chrona.usecases.preset_library import DEFAULT_PRESET_ID, list_builtin_presets
from chrona.usecases.project_checks import schedule_project_file, validate_project_file

TOOL_SET_VERSION = "chrona/agent-tools/v0.4"
COMMAND_TYPES = frozenset({"applyActualIntakeBatch", "captureSnapshot"})
"""The command types the command tools accept in this release (#813); anything else is rejected before a Store is opened."""
DEFAULT_STORE_CONFIG = ".chrona/store.yaml"
WRITE_DISABLED = "E_MCP_WRITE_DISABLED"
MAX_DIAGNOSTICS = 50
MAX_INLINE_SVG_BYTES = 1024 * 1024
MAX_INLINE_PNG_BYTES = 1536 * 1024
MAX_COMPARISON_BYTES = 1024 * 1024
"""A ``compare_baseline`` Automation Result that serializes to more than this is ``E_MCP_RESULT_TOO_LARGE`` (#812)."""
RASTERIZER_UNAVAILABLE = "E_RENDER_RASTERIZER_UNAVAILABLE"

_LOG = logging.getLogger("chrona.agent")
_VIEWPORT = re.compile(r"[1-9][0-9]{2,4}x(?:[1-9][0-9]{2,4}|auto)")
_PRESET_PATH_SUFFIXES = (".yaml", ".yml")


class UnknownToolError(LookupError):
    """The tool name is not in the registry (a protocol error, never an envelope)."""


class InvalidArgumentsError(ValueError):
    """The arguments do not satisfy the tool's input schema (a protocol error, never an envelope)."""


@dataclass(frozen=True)
class Attachment:
    """A binary or text payload that travels beside the structured result.

    ``kind`` is ``image`` (PNG bytes) or ``svg`` (UTF-8 SVG text with a ``chrona://render/...`` ``uri``).
    """

    kind: str
    media_type: str
    data: bytes
    uri: str | None = None


@dataclass(frozen=True)
class ToolResult:
    structured: dict[str, Any]
    attachments: tuple[Attachment, ...] = ()

    @property
    def is_error(self) -> bool:
        """True only for ``failed``: a ``rejected`` plan is a result the tool delivered, not a tool failure."""
        return self.structured["status"] == "failed"

    def text(self) -> str:
        """The structured result as compact JSON, the text content block a client that ignores structure reads."""
        return json.dumps(self.structured, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[["_Call", dict[str, Any]], ToolResult]
    mutating: bool = False

    def document(self) -> dict[str, Any]:
        """The tool as a registry entry: schemas and annotations that say truthfully whether it can write.

        A read-only tool is ``readOnlyHint`` true (a host may skip its approval prompt); a mutating tool is
        ``readOnlyHint`` false and ``destructiveHint`` true whatever it overwrites, because the metadata must not
        understate it. ``idempotentHint`` is true for both: repeating a call is a no-op (the replay ledger).
        """
        return {
            "name": self.name, "title": self.title, "description": self.description,
            "inputSchema": copy.deepcopy(self.input_schema), "outputSchema": copy.deepcopy(self.output_schema),
            "annotations": {"readOnlyHint": not self.mutating, "destructiveHint": self.mutating,
                            "idempotentHint": True, "openWorldHint": False},
        }


# --- schemas -------------------------------------------------------------------------------------------------

_WORKSPACE_PATH_PROPERTY = {
    "type": "string", "minLength": 1, "maxLength": 512,
    "description": "A '/'-separated path relative to the workspace root. No drive, no leading '/', no '..', "
                   "no backslash or colon. The file must already exist inside the workspace.",
}

_DIAGNOSTIC = {
    "type": "object", "required": ["code", "severity", "component", "sourceRef", "message"],
    "additionalProperties": False,
    "properties": {
        "code": {"type": "string", "pattern": "^[EWI]_[A-Z0-9_]+$"},
        "severity": {"enum": ["error", "warning", "info"]},
        "component": {"type": "string"},
        "sourceRef": {"type": "string",
                      "description": "RFC 6901 JSON pointer into the named document, or '/' for the whole input."},
        "message": {"type": "string", "minLength": 1,
                    "description": "What is wrong; never empty and never only the code."},
        "count": {"type": "integer", "minimum": 2,
                  "description": "Present only when equal findings were merged into this row; absent means once."},
        "occurrences": {"type": "array", "items": {"type": "string"}, "maxItems": 20,
                        "description": "Warnings only: the identities of the merged findings, first occurrence first."},
        "revisionRefs": {"type": "array", "items": {"type": "string"}},
        "resourceKind": {"type": "string"}, "resourceIdentity": {"type": "string"},
        "phase": {"type": "string"}, "rule": {"type": "string"},
        "detail": {"type": "object", "description": "The remaining ledger fields of a warning or info, verbatim."},
    },
}
_SHA256 = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
_STATUS = {"enum": ["ok", "rejected", "failed"]}


def _input_schema(properties: dict[str, Any], required: Sequence[str] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = list(required)
    return schema


def _output_schema(properties: dict[str, Any] | None = None) -> dict[str, Any]:
    """The envelope plus a tool's own fields, present when the status is ``ok``; every output is a closed object."""
    return {
        "type": "object", "additionalProperties": False,
        "required": ["status", "diagnostics"],
        "properties": {
            "status": _STATUS,
            "diagnostics": {"type": "array", "items": {"$ref": "#/$defs/diagnostic"}, "maxItems": MAX_DIAGNOSTICS},
            "omittedDiagnostics": {"type": "integer", "minimum": 1},
            **(properties or {}),
        },
        "$defs": {"diagnostic": copy.deepcopy(_DIAGNOSTIC), "sha256": copy.deepcopy(_SHA256)},
    }


def _command_input_schema() -> dict[str, Any]:
    return _input_schema({
        "command": {**_WORKSPACE_PATH_PROPERTY, "description": "A '/'-separated workspace path to a Command Request "
                    "document (chrona/command/v0.3, Spec 10), as chrona command-apply --command takes. The file must "
                    "already exist inside the workspace."},
        "storeConfig": {**_WORKSPACE_PATH_PROPERTY, "description": "A '/'-separated workspace path to a Store configuration "
                        f"(chrona/store-config/v0.1). Omitted means {DEFAULT_STORE_CONFIG}. Every Store root in it must lie "
                        "strictly inside the workspace."},
    }, ["command"])


def _command_output_schema() -> dict[str, Any]:
    return _output_schema({"automationResult": {
        "type": "object",
        "description": "The Automation Result (chrona/automation-result/v0.2) exactly as the command line writes it to "
                       "--result: operation, status accepted or rejected, requestContentIdentity, inputs, diagnostics, "
                       "resultTarget when accepted, replayed true for a replay. Present when the engine produced one.",
    }})


_STORE_CONFIG_PROPERTY = {
    **_WORKSPACE_PATH_PROPERTY,
    "description": "A '/'-separated workspace path to a Store configuration (chrona/store-config/v0.1). Omitted means "
                   f"{DEFAULT_STORE_CONFIG}. Every Store root in it must lie strictly inside the workspace, and its "
                   "integrity setting applies: a tool input cannot lower it.",
}


def _reference_property(what: str) -> dict[str, Any]:
    return {**_WORKSPACE_PATH_PROPERTY, "description": f"A '/'-separated workspace path to {what}: a YAML "
            "resource reference (id, kind, store, address, revision, contentIdentity). The file must already exist "
            "inside the workspace."}


def _render_review_input_schema() -> dict[str, Any]:
    return _input_schema({
        "contextReference": _reference_property("the immutable Render Context to render, as chrona render-review "
                                                "--context-reference takes"),
        "storeConfig": copy.deepcopy(_STORE_CONFIG_PROPERTY),
        "inline": {"enum": ["none", "artifact"], "default": "artifact",
                   "description": "'artifact' carries an SVG target as SVG text and a PNG target as an image; any other "
                                  "target, or 'none', carries only the structured result."},
    }, ["contextReference"])


def _compare_baseline_input_schema() -> dict[str, Any]:
    return _input_schema({
        "baselineReference": _reference_property("the named baseline (a snapshot-ref), as chrona baseline-compare "
                                                 "--baseline-reference takes"),
        "candidateReference": _reference_property("the candidate Project, as chrona baseline-compare "
                                                  "--candidate-reference takes"),
        "storeConfig": copy.deepcopy(_STORE_CONFIG_PROPERTY),
    }, ["baselineReference", "candidateReference"])


# --- result construction -------------------------------------------------------------------------------------

_DIAGNOSTIC_ORDER = ("code", "severity", "component", "sourceRef", "message")
_OPTIONAL_DIAGNOSTIC_FIELDS = ("revisionRefs", "resourceKind", "resourceIdentity", "phase", "rule", "count")


def _sorted_value(value: Any) -> Any:
    """Recursively order every mapping by key, so a ledger's insertion order cannot reach a result."""
    if isinstance(value, Mapping):
        return {key: _sorted_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_sorted_value(item) for item in value]
    return value


def _diagnostic(scope: WorkspaceScope, record: Mapping[str, Any]) -> dict[str, Any]:
    item = {key: record[key] for key in _DIAGNOSTIC_ORDER}
    item["message"] = scope.scrub(str(item["message"]))
    for key in _OPTIONAL_DIAGNOSTIC_FIELDS:
        if record.get(key):
            item[key] = scope.scrub_value(record[key])
    return item


def _envelope(scope: WorkspaceScope, status: str, diagnostics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Scrub, merge rows that scrubbing made equal (counts add up) and cap the list.

    The use case already merged equal rows (``collapse_records``); scrubbing a host path can make two
    different rows equal, so the same function runs again here.
    """
    kept = collapse_records(_diagnostic(scope, record) for record in diagnostics)
    envelope: dict[str, Any] = {"status": status, "diagnostics": list(kept[:MAX_DIAGNOSTICS])}
    if len(kept) > MAX_DIAGNOSTICS:
        envelope["omittedDiagnostics"] = len(kept) - MAX_DIAGNOSTICS
    return envelope


def _warning(scope: WorkspaceScope, payload: Mapping[str, Any]) -> dict[str, Any]:
    """A render warning or info record as a diagnostic; its remaining ledger fields are kept verbatim in ``detail``."""
    merged = payload.get("severity") != "info"  # an info record's own ``count`` is a number of labels, not a merge count
    known = {"code", "severity", "component", "sourceRef", "message"} | ({"count", "occurrences"} if merged else set())
    item: dict[str, Any] = {
        "code": str(payload["code"]), "severity": str(payload.get("severity", "warning")),
        "component": str(payload.get("component", "render")), "sourceRef": str(payload.get("sourceRef", "/")),
        "message": scope.scrub(str(payload["message"])),
    }
    if merged and "count" in payload:
        item["count"] = int(payload["count"])
        item["occurrences"] = [scope.scrub(str(entry)) for entry in payload.get("occurrences", ())]
    item["detail"] = _sorted_value(scope.scrub_value({key: value for key, value in payload.items() if key not in known}))
    return item


class _Call:
    """One tool call: its scope, and the fields a failure keeps because the call had already produced them."""

    def __init__(self, scope: WorkspaceScope):
        self.scope = scope
        self.carried: dict[str, Any] = {}

    def ok(self, **fields: Any) -> dict[str, Any]:
        return {"status": "ok", "diagnostics": [], **fields}

    def rejected(self, report: FailureReport) -> ToolResult:
        return ToolResult({**_envelope(self.scope, report.status, report.diagnostics), **self.carried})

    def failure(self, error: Exception) -> ToolResult:
        report = report_failure(error)
        diagnostics = report.diagnostics
        status = report.status
        if diagnostics and diagnostics[0]["code"] == "E_TOOL_FAILURE":
            _LOG.error("internal error in an agent tool", exc_info=error)
            diagnostics = (dict(diagnostics[0], message=f"internal error: {type(error).__name__}"),)
        elif any(item["code"] == RASTERIZER_UNAVAILABLE for item in diagnostics):
            # The environment lacks the `render` extra: nothing is wrong with the plan, so this is a failure.
            status = "failed"
        return ToolResult({**_envelope(self.scope, status, diagnostics), **self.carried})


def _identity(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


# --- handlers ------------------------------------------------------------------------------------------------

def _validate_project(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    path = call.scope.resolve_path(arguments["project"], "/project")
    call.carried["projectIdentity"] = _identity(path.read_bytes())
    outcome = validate_project_file(path)
    if not outcome.ok:
        return call.rejected(rejection_report(outcome.diagnostics))
    return ToolResult(call.ok(projectIdentity=call.carried["projectIdentity"]))


def _placement(placement: Mapping[str, Any]) -> dict[str, str]:
    """A placement as ISO dates in a fixed key order: ``start`` then ``end``, or ``at``."""
    return {key: placement[key].isoformat() for key in ("start", "end", "at") if key in placement}


def _schedule_project(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    outcome = schedule_project_file(call.scope.resolve_path(arguments["project"], "/project"))
    if not outcome.ok:
        return call.rejected(rejection_report(outcome.diagnostics))
    fields: dict[str, Any] = {"placements": {key: _placement(outcome.placements[key]) for key in sorted(outcome.placements)}}
    fields["warnings"] = [
        _warning(call.scope, {"code": item.id, "severity": "warning", "component": "core", "sourceRef": item.path,
                              "message": item.message, **(item.details or {})})
        for item in outcome.warnings
    ]
    if outcome.analysis is not None:
        fields["analysis"] = {
            "criticalObjectIds": list(outcome.analysis["criticalObjectIds"]),
            # Spec 66 section 3: every mapping is sorted by key, whatever order the use case gives (it follows the
            # Project object order since #789), so this tool's bytes do not depend on a scheduler detail.
            "totalFloat": {key: outcome.analysis["totalFloat"][key] for key in sorted(outcome.analysis["totalFloat"])},
        }
    return ToolResult(call.ok(**fields))


def _preset_argument(call: _Call, value: str | None) -> str | None:
    """A builtin id passes through; a value naming a file must be a workspace path ending ``.yaml`` or ``.yml``."""
    if value is None or not ("/" in value or value.endswith(_PRESET_PATH_SUFFIXES)):
        return value
    if not value.endswith(_PRESET_PATH_SUFFIXES):
        raise StableFailure(
            "E_MCP_PATH_SYNTAX",
            "a preset path must end in .yaml or .yml; a builtin preset id has no '/' (see list_presets)",
            "mcp", "/preset", 2,
        )
    return str(call.scope.resolve_path(value, "/preset"))


def _optional_path(call: _Call, arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    return None if value is None else str(call.scope.resolve_path(value, f"/{key}"))


def _rasterizer_importable() -> bool:
    try:
        import resvg_py  # noqa: F401  (probe only; the renderer owns the import it uses)
    except ImportError:
        return False
    return True


def _render_draft(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    viewport = arguments.get("viewport", DEFAULT_VIEWPORT)
    if not _VIEWPORT.fullmatch(viewport):
        raise InvalidArgumentsError("viewport must match WIDTHxHEIGHT or WIDTHxauto (3 to 5 digits, no leading zero)")
    fmt = arguments.get("format", "svg")
    inline = arguments.get("inline", "image")
    request = DraftRenderRequest(
        project=call.scope.resolve_path(arguments["project"], "/project"), target_kind=fmt,
        preset=_preset_argument(call, arguments.get("preset")),
        view=_optional_path(call, arguments, "view"), theme=_optional_path(call, arguments, "theme"),
        scheme=_optional_path(call, arguments, "scheme"), layout=_optional_path(call, arguments, "layout"),
        actual=_optional_path(call, arguments, "actual"),
        viewport=viewport, locale=arguments.get("locale", "en-US"),
    )
    rendered = render_draft(request)
    artifact = rendered.artifact
    artifacts: dict[str, Any] = {fmt: artifact}

    def artifact_of(kind: str) -> Any:
        if kind not in artifacts:
            artifacts[kind] = render_draft(replace(request, target_kind=kind)).artifact
        return artifacts[kind]

    attachments: list[Attachment] = []
    png_available: bool | None = True if fmt == "png" else None  # None: not yet known
    if inline == "image":
        try:
            image = artifact_of("png")
        except Exception as error:  # only the missing rasterizer is an expected, reported absence
            if RASTERIZER_UNAVAILABLE not in {item["code"] for item in report_failure(error).diagnostics}:
                raise
            png_available = False
        else:
            png_available = True
            if len(image.content) > MAX_INLINE_PNG_BYTES:
                raise _too_large("PNG", MAX_INLINE_PNG_BYTES)
            attachments.append(Attachment("image", image.media_type, image.content))
    elif inline == "svg":
        svg = artifact_of("svg")
        if len(svg.content) > MAX_INLINE_SVG_BYTES:
            raise _too_large("SVG", MAX_INLINE_SVG_BYTES)
        attachments.append(Attachment("svg", svg.media_type, svg.content, f"chrona://render/{_identity(svg.content)}.svg"))
    if png_available is None:
        png_available = _rasterizer_importable()
    fields = call.ok(
        format=fmt, contentIdentity=_identity(artifact.content), byteLength=len(artifact.content),
        pngAvailable=png_available,
        warnings=[_warning(call.scope, payload) for payload in warning_payloads(rendered.rendered)],
    )
    return ToolResult(fields, tuple(attachments))


def _too_large(kind: str, limit: int) -> StableFailure:
    return StableFailure(
        "E_MCP_RESULT_TOO_LARGE",
        f"the inline {kind} is larger than {limit} bytes; lower the viewport, use inline 'none', "
        "or render to a file with the chrona command line, which has no size cap",
        "mcp", "/inline", 2,
    )


def _too_large_review(kind: str, limit: int) -> StableFailure:
    """An immutable Context fixes its own viewport, so the advice is ``inline: none`` or the command line only."""
    return StableFailure(
        "E_MCP_RESULT_TOO_LARGE",
        f"the inline {kind} is larger than {limit} bytes; use inline 'none' (the identity and length still describe "
        "it) or render to a file with chrona render-review, which has no size cap",
        "mcp", "/inline", 2,
    )


def _list_presets(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    return ToolResult(call.ok(presets=list_builtin_presets(), default=DEFAULT_PRESET_ID))


# The JSON pointer into the Command Request each code of the command engine is about. The message of a row is the
# engine's own (every Automation Result row carries one since #829), so the tool and the command line say the same.
_COMMAND_SOURCE_REFS = {"E_AUTOMATION_BASE_REVISION": "/baseRevision", "E_AUTOMATION_OPERATION_UNSUPPORTED": "/type"}


def _open_contained_store(call: _Call, config_path: Path) -> Any:
    """Open the Store configuration; every Store root in it must lie strictly inside the workspace (Spec 66 section 4).

    The one entry for every tool that reaches a Store: a root outside the workspace is ``E_MCP_PATH_CONTAINMENT`` before
    any file is read from or written to a root.
    """
    try:
        return open_store_reader(config_path, contained_in=call.scope.root)
    except StoreRootOutsideWorkspace as error:
        raise StableFailure(
            "E_MCP_PATH_CONTAINMENT",
            "a Store root in the configuration resolves outside the workspace; every Store root must lie inside it",
            "mcp", "/storeConfig", 2,
        ) from error


def _iso_date(item: object) -> str:
    if isinstance(item, date):
        return item.isoformat()
    raise TypeError(f"Not JSON serializable: {type(item)!r}")


def _render_review(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    context_path = call.scope.resolve_path(arguments["contextReference"], "/contextReference")
    config_path = call.scope.resolve_path(arguments.get("storeConfig", DEFAULT_STORE_CONFIG), "/storeConfig")
    reference = load_reference(context_path)
    config = _open_contained_store(call, config_path)
    reader, root = snapshot_reader_for(config, reference)
    closure = resolve_context_closure(reference, reader)
    rendered = render_context_closure(closure, root)
    artifact, kind = rendered.artifact, closure.context.target.kind
    attachments: list[Attachment] = []
    if arguments.get("inline", "artifact") == "artifact":
        if kind == "svg":
            if len(artifact.content) > MAX_INLINE_SVG_BYTES:
                raise _too_large_review("SVG", MAX_INLINE_SVG_BYTES)
            attachments.append(Attachment("svg", artifact.media_type, artifact.content,
                                          f"chrona://render/{_identity(artifact.content)}.svg"))
        elif kind == "png":
            if len(artifact.content) > MAX_INLINE_PNG_BYTES:
                raise _too_large_review("PNG", MAX_INLINE_PNG_BYTES)
            attachments.append(Attachment("image", artifact.media_type, artifact.content))
    fields = call.ok(
        format=kind, contentIdentity=_identity(artifact.content), byteLength=len(artifact.content),
        inlined=bool(attachments),
        warnings=[_warning(call.scope, payload) for payload in warning_payloads(rendered)],
    )
    return ToolResult(fields, tuple(attachments))


def _compare_baseline(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    baseline_path = call.scope.resolve_path(arguments["baselineReference"], "/baselineReference")
    candidate_path = call.scope.resolve_path(arguments["candidateReference"], "/candidateReference")
    config_path = call.scope.resolve_path(arguments.get("storeConfig", DEFAULT_STORE_CONFIG), "/storeConfig")
    baseline, candidate = load_reference(baseline_path), load_reference(candidate_path)
    config = _open_contained_store(call, config_path)
    # The command line writes the result with a date as ISO text (cli._json_default); the same round trip keeps the bytes equal.
    result = json.loads(json.dumps(compare_store_baseline(config, baseline, candidate), default=_iso_date))
    if len(json.dumps(result, sort_keys=True).encode("utf-8")) > MAX_COMPARISON_BYTES:
        raise StableFailure(
            "E_MCP_RESULT_TOO_LARGE",
            f"the comparison result is larger than {MAX_COMPARISON_BYTES} bytes; use chrona baseline-compare, "
            "which writes it to a file with no size cap",
            "mcp", "/", 2,
        )
    result = call.scope.scrub_value(result)
    if result["status"] == "accepted":
        return ToolResult(call.ok(automationResult=result))
    call.carried["automationResult"] = result
    # One row per code of the result, with the engine's message; the whole input is the source (a code such as
    # E_BASELINE_REFERENCE covers the baseline, its project and the candidate alike).
    rows = [diagnostic_record(item["code"], item.get("message", ""), "operational") for item in result["diagnostics"]]
    return call.rejected(FailureReport("rejected", collapse_records(rows), 1))


def _command_tool(operation: str) -> Callable[[_Call, dict[str, Any]], ToolResult]:
    def handle(call: _Call, arguments: dict[str, Any]) -> ToolResult:
        command_path = call.scope.resolve_path(arguments["command"], "/command")
        config_path = call.scope.resolve_path(arguments.get("storeConfig", DEFAULT_STORE_CONFIG), "/storeConfig")
        command = parse_command_request(command_path.read_text(encoding="utf-8"))
        reader = _open_contained_store(call, config_path)
        result = call.scope.scrub_value(run_store_command(operation, command, reader, allowed_types=COMMAND_TYPES))
        if result["status"] == "accepted":
            return ToolResult(call.ok(automationResult=result))
        call.carried["automationResult"] = result
        rows = [diagnostic_record(item["code"], item.get("message", ""), "operational",
                                  _COMMAND_SOURCE_REFS.get(item["code"], "/")) for item in result["diagnostics"]]
        return call.rejected(FailureReport("rejected", collapse_records(rows), 1))

    return handle


# --- registry ------------------------------------------------------------------------------------------------

_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "validate_project", "Validate a Project",
        "Validate a Project YAML file in the workspace against the Project schema and the Core rules. Returns "
        "status 'ok' with no diagnostics, or status 'rejected' with typed diagnostics (code, sourceRef, message). "
        "A rejected plan is a normal result, not a tool error. A dependency cycle is rejected here, naming the "
        "objects on it. This tool computes no dates, so a fixed date that contradicts its dependencies is found "
        "only by schedule_project: run it to read dates.",
        _input_schema({"project": _WORKSPACE_PATH_PROPERTY}, ["project"]),
        _output_schema({"projectIdentity": {"$ref": "#/$defs/sha256"}}),
        _validate_project,
    ),
    ToolSpec(
        "schedule_project", "Compute a Project's schedule",
        "Compute the schedule of a Project YAML file in the workspace. On 'ok' returns placements per object id "
        "({start, end} or {at}, ISO dates, end exclusive) and the analysis (critical object ids, total float in "
        "calendar days). A fixed date that contradicts its dependencies, or a bound that cannot be met, is rejected "
        "here and not by validate_project (a dependency cycle is rejected by both). 'warnings' lists W_DEADLINE for each object planned to finish after its deadline "
        "(the plan is still scheduled; the deadline is a promise, not a bound). Read dates from this result; never compute a date by hand.",
        _input_schema({"project": _WORKSPACE_PATH_PROPERTY}, ["project"]),
        _output_schema({
            "placements": {"type": "object", "additionalProperties": {
                "type": "object", "additionalProperties": False,
                "properties": {key: {"type": "string", "format": "date"} for key in ("start", "end", "at")}}},
            "analysis": {"type": "object", "additionalProperties": False,
                         "required": ["criticalObjectIds", "totalFloat"],
                         "properties": {"criticalObjectIds": {"type": "array", "items": {"type": "string"}},
                                        "totalFloat": {"type": "object",
                                                       "additionalProperties": {"type": "integer", "minimum": 0}}}},
            "warnings": {"type": "array", "items": {"$ref": "#/$defs/diagnostic"}},
        }),
        _schedule_project,
    ),
    ToolSpec(
        "render_draft", "Render a draft picture of a Project",
        "Render a Project YAML file in the workspace to a deterministic draft picture. By default the result "
        "carries a PNG preview image (inline 'image'); inline 'svg' carries the SVG text; 'none' carries only the "
        "structured result. 'format' chooses the artifact that contentIdentity and byteLength describe. 'preset' "
        "is a builtin id from list_presets or a workspace .yaml path; omitted means chrona-default-draft. "
        "The tool writes no file, and a draft render is not reproducible evidence. PNG needs the render extra "
        "(pngAvailable says whether it is installed). Read 'status' and 'warnings', not only isError: a rejected "
        "plan is a result, and a warning means something was clipped, suppressed or substituted.",
        _input_schema({
            "project": _WORKSPACE_PATH_PROPERTY,
            "actual": {**_WORKSPACE_PATH_PROPERTY, "description": "Actual Set YAML to draw progress over the plan."},
            "preset": {"type": "string", "minLength": 1, "maxLength": 512,
                       "description": "A builtin preset id (see list_presets) or a workspace path ending .yaml or .yml."},
            "view": _WORKSPACE_PATH_PROPERTY, "theme": _WORKSPACE_PATH_PROPERTY,
            "scheme": _WORKSPACE_PATH_PROPERTY, "layout": _WORKSPACE_PATH_PROPERTY,
            "viewport": {"type": "string", "pattern": "^[1-9][0-9]{2,4}x([1-9][0-9]{2,4}|auto)$",
                         "default": DEFAULT_VIEWPORT},
            "locale": {"enum": ["en-US", "ja-JP"], "default": "en-US"},
            "format": {"enum": ["svg", "png"], "default": "svg"},
            "inline": {"enum": ["none", "image", "svg"], "default": "image"},
        }, ["project"]),
        _output_schema({
            "format": {"enum": ["svg", "png"]}, "contentIdentity": {"$ref": "#/$defs/sha256"},
            "byteLength": {"type": "integer", "minimum": 0}, "pngAvailable": {"type": "boolean"},
            "warnings": {"type": "array", "items": {"$ref": "#/$defs/diagnostic"}},
        }),
        _render_draft,
    ),
    ToolSpec(
        "list_presets", "List builtin presets",
        "List the builtin preset ids that render_draft accepts as 'preset', with the gallery set of each, and the "
        "preset used when none is named.",
        _input_schema({}),
        _output_schema({
            "presets": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["id", "gallerySet"],
                "properties": {"id": {"type": "string"}, "gallerySet": {"type": "string"}}}},
            "default": {"type": "string"},
        }),
        _list_presets,
    ),
    ToolSpec(
        "render_review", "Render pinned evidence from a Store",
        "Render an immutable Render Context from a Store: the same render as chrona render-review with --store-config, "
        "not a draft. 'contextReference' is a workspace path to the Context's resource reference; 'storeConfig' is a "
        "workspace path to the Store configuration (default .chrona/store.yaml) and every Store root in it must lie "
        "inside the workspace. The Context fixes its own format and viewport, so none is an argument. Every reference "
        "is verified against its pinned contentIdentity, and the Store's integrity setting applies; no argument lowers "
        "it. Returns the target 'format', the artifact's contentIdentity and byteLength, 'warnings', and with inline "
        "'artifact' the SVG text or PNG image. The tool is read-only, works without --allow-write, and writes no file.",
        _render_review_input_schema(),
        _output_schema({
            "format": {"enum": ["svg", "png", "pdf", "typst", "tikz"]}, "contentIdentity": {"$ref": "#/$defs/sha256"},
            "byteLength": {"type": "integer", "minimum": 0}, "inlined": {"type": "boolean"},
            "warnings": {"type": "array", "items": {"$ref": "#/$defs/diagnostic"}},
        }),
        _render_review,
    ),
    ToolSpec(
        "compare_baseline", "Compare a named baseline with a candidate",
        "Compare a named baseline (a snapshot-ref) with a candidate Project in a Store: the same comparison as chrona "
        "baseline-compare. Both references are workspace paths; 'storeConfig' is a workspace path to the Store "
        "configuration (default .chrona/store.yaml) and every Store root in it must lie inside the workspace. Both "
        "closures are verified against their pinned contentIdentity; no argument lowers the Store's integrity. Returns "
        "status 'ok' with automationResult (the Automation Result the command line writes: the changed objects and both "
        "schedules), or 'rejected' with typed diagnostics. The tool is read-only, works without --allow-write, and "
        "writes no file.",
        _compare_baseline_input_schema(),
        _output_schema({"automationResult": {
            "type": "object",
            "description": "The Automation Result (chrona/automation-result/v0.2) exactly as chrona baseline-compare "
                           "writes it to --result: operation baseline-compare, status accepted or rejected, "
                           "requestContentIdentity, inputs, diagnostics and, when accepted, comparison (changes, "
                           "beforeSchedule, afterSchedule). Present when the comparison produced one.",
        }}),
        _compare_baseline,
    ),
    ToolSpec(
        "check_command", "Preview a Store command",
        "Check a Command Request file in the workspace against its Store without writing anything: the same check "
        "as chrona command-check. The request must be applyActualIntakeBatch (an Actual intake batch) or captureSnapshot "
        "(a named baseline); any other type is rejected with E_AUTOMATION_OPERATION_UNSUPPORTED. 'storeConfig' is a "
        "workspace path to a Store configuration and defaults to .chrona/store.yaml; every Store root in it must lie "
        "inside the workspace. Returns status 'ok' with automationResult (the Automation Result the command line writes), "
        "or 'rejected' with typed diagnostics, for example a stale baseRevision. A preview is not a precondition of "
        "apply_command, and it works whether or not writes are enabled.",
        _command_input_schema(), _command_output_schema(), _command_tool("command-check"),
    ),
    ToolSpec(
        "apply_command", "Apply a Store command",
        "Apply a Command Request file in the workspace to its Store: the same work as chrona command-apply. It "
        "executes directly. There is no approval step and no confirm token, and the proposal and decision exchange of "
        "Spec 10 section 9.1 is not implemented. It writes only when the server was started with --allow-write; "
        "otherwise it is refused with E_MCP_WRITE_DISABLED and writes nothing. The request must be "
        "applyActualIntakeBatch or captureSnapshot. Safeguards that are not approvals: a stale baseRevision is "
        "rejected (compare-and-set), the same commandId with the same request is a no-op that returns the first result "
        "(replayed: true), a baseline name or an observation with different facts is never overwritten, and every write "
        "is a new immutable Store revision, so an earlier one can be inspected and restored. Store roots must lie "
        "inside the workspace. Returns status 'ok' with automationResult, or 'rejected' with typed diagnostics.",
        _command_input_schema(), _command_output_schema(), _command_tool("command-apply"), mutating=True,
    ),
)
_BY_NAME = {spec.name: spec for spec in _TOOLS}
assert len(_BY_NAME) == len(_TOOLS)


def tool_specs() -> tuple[ToolSpec, ...]:
    """The registry, in declaration order."""
    return _TOOLS


def registry_document() -> dict[str, Any]:
    """The tool set as one JSON document (what ``tools/list`` serves and ``chrona mcp --list-tools`` prints)."""
    return {"toolSet": TOOL_SET_VERSION, "tools": [spec.document() for spec in _TOOLS]}


@cache
def _input_validator(name: str):
    """The validator of one tool's input schema, from the one shared factory (a guard test forbids another)."""
    return validator_for_schema(_BY_NAME[name].input_schema)


def _check_arguments(spec: ToolSpec, arguments: object) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise InvalidArgumentsError(f"{spec.name}: arguments must be an object")
    error = best_match(_input_validator(spec.name).iter_errors(arguments))
    if error is not None:
        where = "/".join(str(part) for part in error.absolute_path)
        message = error.message if len(error.message) <= 200 else error.message[:200] + "..."
        raise InvalidArgumentsError(f"{spec.name}: {where + ': ' if where else ''}{message}")
    return arguments


def call_tool(scope: WorkspaceScope, name: str, arguments: object = None, *, allow_write: bool = False) -> ToolResult:
    """Run one tool. Unknown names and malformed arguments raise (protocol errors); everything else is a result.

    A mutating tool runs only when ``allow_write`` is true (a server start option, never an argument); otherwise the
    result is ``failed`` with ``E_MCP_WRITE_DISABLED`` before any file is opened.
    """
    spec = _BY_NAME.get(name)
    if spec is None:
        raise UnknownToolError(name)
    checked = _check_arguments(spec, {} if arguments is None else arguments)
    call = _Call(scope)
    if spec.mutating and not allow_write:
        return call.failure(StableFailure(
            WRITE_DISABLED,
            f"{spec.name} writes, and this server was started without --allow-write; restart it with "
            "'chrona mcp --allow-write' to enable writes. Nothing was read or written.",
            "mcp", "/", 2,
        ))
    try:
        return spec.handler(call, checked)
    except InvalidArgumentsError:
        raise
    except Exception as error:  # every other failure is typed by the shared failure report
        return call.failure(error)
