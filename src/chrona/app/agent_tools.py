"""The SDK-free agent tools: a registry of read-only tools over the use cases, and their result contract.

Four tools front the use cases an agent needs to plan and draw a schedule:
``validate_project``, ``schedule_project``, ``render_draft`` and ``list_presets``
(tool set ``chrona/agent-tools/v0.2``, Spec 66). A tool is a use case with a typed
envelope: ``call_tool(scope, name, arguments)`` validates the arguments against the
tool's input schema, runs the use case on files inside a ``WorkspaceScope`` and returns a
``ToolResult`` whose ``structured`` mapping is the envelope (``status``, ``diagnostics``)
plus the tool's own fields. A transport adapter (the MCP binding) only moves that result.

This module imports no SDK, prints nothing and writes no file. Failures reach the caller
as typed diagnostics through ``usecases.failure_report``, never as a traceback, and every
mapping it returns is sorted so a result is a pure function of the workspace bytes and the
arguments.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
from dataclasses import dataclass, replace
from functools import cache
from typing import Any, Callable, Mapping, Sequence

from jsonschema.exceptions import best_match

from chrona.app.agent_workspace import WorkspaceScope
from chrona.resources import validator_for_schema
from chrona.usecases.draft_render import DEFAULT_VIEWPORT, DraftRenderRequest, render_draft, warning_payloads
from chrona.usecases.failure_report import FailureReport, StableFailure, collapse_records, rejection_report, report_failure
from chrona.usecases.preset_library import list_builtin_presets
from chrona.usecases.project_checks import schedule_project_file, validate_project_file

TOOL_SET_VERSION = "chrona/agent-tools/v0.2"
DEFAULT_PRESET_ID = "chrona-default-draft"
MAX_DIAGNOSTICS = 50
MAX_INLINE_SVG_BYTES = 1024 * 1024
MAX_INLINE_PNG_BYTES = 1536 * 1024
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

    def document(self) -> dict[str, Any]:
        """The tool as a registry entry: schemas and the read-only annotations a host uses to skip approval prompts."""
        return {
            "name": self.name, "title": self.title, "description": self.description,
            "inputSchema": copy.deepcopy(self.input_schema), "outputSchema": copy.deepcopy(self.output_schema),
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True,
                            "openWorldHint": False},
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


def _list_presets(call: _Call, arguments: dict[str, Any]) -> ToolResult:
    return ToolResult(call.ok(presets=list_builtin_presets(), default=DEFAULT_PRESET_ID))


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


def call_tool(scope: WorkspaceScope, name: str, arguments: object = None) -> ToolResult:
    """Run one tool. Unknown names and malformed arguments raise (protocol errors); everything else is a result."""
    spec = _BY_NAME.get(name)
    if spec is None:
        raise UnknownToolError(name)
    checked = _check_arguments(spec, {} if arguments is None else arguments)
    call = _Call(scope)
    try:
        return spec.handler(call, checked)
    except InvalidArgumentsError:
        raise
    except Exception as error:  # every other failure is typed by the shared failure report
        return call.failure(error)
