from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

import yaml

from chrona.usecases.review_projects import review_projects
from chrona.core.diagnostics import Diagnostic
from chrona.core.validation import load_yaml, validate_project
from chrona.presentation.model.closure import ClosureError, RenderClosure, resolve_draft_render, resolve_guided_draft_render, resolve_render_context
from chrona.presentation.contracts import TypesetterIdentity
from chrona.usecases.render_review import RenderFailed, RenderRejected, RenderRequest, RenderedReview, render_review
from chrona.presentation.renderers.registry import renderer_for
from chrona.scheduling.scheduler import ReferenceScheduler, schedule
from chrona.storage.loader import load_project
from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError
from chrona.operational.baselines import compare_baseline
from chrona.operational.store_config import load_store_config
from chrona.operational.command_engine import apply_actual_command, check_command
from chrona.usecases.authoring_commands import apply_authoring_command, parse_authoring_command
from chrona.operational.authoring_commands import cas_write_authoring_aggregate, cas_write_authoring_workspace, read_authoring_workspace
from chrona.operational.resources import parse_document
from chrona.usecases.materialize import materialize
from chrona.usecases.local_authoring import discover_store_configuration, initialize_project


@dataclass(frozen=True)
class CliFailure(Exception):
    code: str
    message: str
    component: str = "cli"
    source_ref: str = "/"
    exit_code: int = 1


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CliFailure("E_COMMAND_SYNTAX", message, exit_code=2)


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def _diagnostic(
    code: str, message: str, component: str, source_ref: str = "/",
    revision_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code, "severity": "error", "component": component,
        "sourceRef": source_ref, "revisionRefs": revision_refs or [], "message": message,
    }


def _emit_failure(failure: CliFailure) -> NoReturn:
    payload = {
        "status": "rejected" if failure.exit_code == 1 else "failed",
        "diagnostics": [_diagnostic(
            failure.code, failure.message, failure.component, failure.source_ref
        )],
    }
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(failure.exit_code)


def _reject(diagnostics: list[Diagnostic], component: str = "core") -> NoReturn:
    payload = {
        "status": "rejected",
        "diagnostics": [
            _diagnostic(item.id, item.message, component, item.path) for item in diagnostics
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(1)


def _reject_codes(codes: list[str] | tuple[str, ...], component: str) -> NoReturn:
    payload = {
        "status": "rejected",
        "diagnostics": [
            _diagnostic(code, code, component) for code in codes
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(1)


def _add_snapshot_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("project", nargs="?", help="raw Draft Project path")
    command.add_argument("--snapshot-reference", help="immutable Project resource-reference YAML")
    command.add_argument("--snapshot-root", help="local snapshot adapter root")
    command.add_argument("--store-identity", help="expected local snapshot store identity")
    command.add_argument("--require-content-identity", action="store_true", help="reject snapshot references without an exact content identity")


def _add_draft_target_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--format", choices=("svg", "png", "pdf", "typst", "tikz"), default="svg")
    command.add_argument("--typesetter-engine", help="required with --format typst or tikz")
    command.add_argument("--typesetter-version", help="required exact engine version with --format typst or tikz")
    command.add_argument("--typesetter-adapter-grammar", help="required adapter grammar with --format typst or tikz")


def _draft_typesetter_identity(args: argparse.Namespace) -> TypesetterIdentity | None:
    values = (args.typesetter_engine, args.typesetter_version, args.typesetter_adapter_grammar)
    is_typeset = args.format in {"typst", "tikz"}
    if is_typeset and not all(values):
        raise CliFailure(
            "E_RENDER_TYPESETTER_DESCRIPTOR",
            "typeset Draft targets require --typesetter-engine, --typesetter-version, and --typesetter-adapter-grammar",
            "cli", "/typesetter", 2,
        )
    if not is_typeset and any(values):
        raise CliFailure(
            "E_RENDER_TYPESETTER_DESCRIPTOR",
            "typesetter descriptor is valid only with --format typst or tikz",
            "cli", "/typesetter", 2,
        )
    return TypesetterIdentity(*values) if is_typeset else None


def _load_primary_project(args: argparse.Namespace) -> dict[str, Any]:
    snapshot_values = (args.snapshot_reference, args.snapshot_root, args.store_identity)
    if any(snapshot_values):
        if not all(snapshot_values) or args.project:
            raise CliFailure(
                "E_COMMAND_SYNTAX",
                "snapshot mode requires --snapshot-reference, --snapshot-root, and --store-identity without a raw project",
                exit_code=2,
            )
        reference = load_yaml(args.snapshot_reference)
        return load_project(reference, LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=args.require_content_identity))
    if not args.project:
        raise CliFailure("E_COMMAND_SYNTAX", "a raw project or complete snapshot mode is required", exit_code=2)
    return load_yaml(args.project)


def _parser() -> JsonArgumentParser:
    parser = JsonArgumentParser(prog="chrona")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=JsonArgumentParser)
    commands = {
        "validate": "validate a raw Draft or immutable Project snapshot",
        "schedule": "derive a Date-only schedule from a raw Draft or immutable snapshot",
    }
    for name, help_text in commands.items():
        command = sub.add_parser(name, help=help_text, description=help_text)
        _add_snapshot_arguments(command)
    command = sub.add_parser("render", help="render a draft review surface (not reproducible evidence)",
                              description="render a draft review surface (not reproducible evidence)")
    command.add_argument("project", help="Draft Project YAML path")
    command.add_argument("--view", required=True, help="View YAML path")
    command.add_argument("--theme", required=True, help="Theme YAML path")
    command.add_argument("--scheme", required=True, help="Color Scheme YAML path")
    command.add_argument("--layout", required=True, help="Layout Profile YAML path")
    command.add_argument("--actual", help="Actual Set YAML path")
    command.add_argument("--summary", help="Summary Profile YAML path")
    command.add_argument("--detail", help="Review Detail Profile YAML path")
    command.add_argument("--viewport", default="1600x900", help="viewport WIDTHxHEIGHT (default: 1600x900)")
    command.add_argument("--locale", default="en-US", help="render locale (default: en-US)")
    _add_draft_target_arguments(command)
    command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("authoring-command-apply", help="apply one revision-bound guided workspace command")
    command.add_argument("--workspace", required=True)
    command.add_argument("--command", dest="authoring_command", required=True)
    command.add_argument("--result", required=True)

    command = sub.add_parser("materialize-presentation-preset", help="apply one revision-bound Stage-3 materialization command")
    command.add_argument("--workspace", required=True)
    command.add_argument("--command", dest="authoring_command", required=True)
    command.add_argument("--result", required=True)

    command = sub.add_parser("render-workspace", help="render a guided authoring workspace Draft (not reproducible evidence)")
    command.add_argument("workspace", help="guided authoring workspace YAML path")
    command.add_argument("--viewport", default="1600x900", help="viewport WIDTHxHEIGHT (default: 1600x900)")
    command.add_argument("--locale", default="en-US", help="render locale (default: en-US)")
    _add_draft_target_arguments(command)
    command.add_argument("--provenance", help="write non-Scene guided closure provenance JSON")
    command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("render-review", help="render an immutable Render Context v0.8", description="render an immutable Render Context v0.8")
    command.add_argument("--context-reference", required=True, help="immutable Render Context resource-reference YAML")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--require-content-identity", action="store_true", help="reject Context closure references without an exact content identity")
    command.add_argument("--reject-unused-closure-inputs", action="store_true", help="reject a render whose Context declares inputs the render never reads")
    command.add_argument("--format", choices=("svg", "png", "pdf", "typst", "tikz"), help="assert the Context target format")
    command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("materialize", help="materialize one declared immutable example Context")
    command.add_argument("manifest", help="example materializer manifest")
    command.add_argument("--slide", required=True, help="declared slide identifier")
    command.add_argument("--output", "-o", required=True, help="empty output directory")
    command.add_argument("--write", action="store_true", help="replace the manifest-declared generated artifact")

    command = sub.add_parser("init", help="create a non-overwriting local Chrona project")
    command.add_argument("directory", nargs="?", default=".")
    command.add_argument("--example", default="halcyon-1", choices=("halcyon-1",))

    command = sub.add_parser("render-review-gallery", help="render deterministic Color Scheme comparison gallery")
    command.add_argument("--context-reference", required=True, action="append", help="immutable Render Context v0.8 resource-reference YAML; repeat for each scheme")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--require-content-identity", action="store_true", help="reject Context closure references without an exact content identity")
    command.add_argument("--output-directory", required=True)

    command = sub.add_parser("review", help="compare two immutable Project snapshots", description="compare two immutable Project snapshots")
    command.add_argument("before_reference")
    command.add_argument("candidate_reference")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--require-content-identity", action="store_true", help="reject Project references without an exact content identity")

    command = sub.add_parser("baseline-compare", help="compare a named baseline and immutable candidate")
    command.add_argument("--baseline-reference", required=True)
    command.add_argument("--candidate-reference", required=True)
    command.add_argument("--store-config")
    command.add_argument("--result", required=True)

    for name in ("command-check", "command-apply", "actual-intake", "actual-resolve", "baseline-capture"):
        command = sub.add_parser(name, help=f"run M26 {name} command")
        command.add_argument("--command", dest="command_path", required=True)
        command.add_argument("--store-config")
        command.add_argument("--result", required=True)

    return parser



def _render_review(closure: RenderClosure, args: argparse.Namespace, *, asset_root: Path | None = None) -> RenderedReview:
    """Adapt one resolved closure to the render use case and its diagnostics."""
    request = RenderRequest(
        closure=closure, snapshot_root=Path(getattr(args, "snapshot_root", ".")),
        scheduler=ReferenceScheduler(), renderer=renderer_for(
            {"kind": closure.context.target.kind, "capabilities": list(closure.context.target.capabilities)},
            closure.context.environment.renderer_environment(),
        ),
        require_all_inputs_read=getattr(args, "reject_unused_closure_inputs", False),
        asset_root=asset_root,
    )
    try:
        return render_review(request)
    except RenderRejected as error:
        _reject(error.diagnostics, error.component)
    except RenderFailed as error:
        raise CliFailure(error.code, error.message, error.component) from error


def _run_render_review(args: argparse.Namespace) -> None:
    reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=args.require_content_identity)
    closure = resolve_render_context(load_yaml(args.context_reference), reader)
    _assert_context_format(closure, args.format)
    rendered = _render_review(closure, args)
    Path(args.output).write_bytes(rendered.artifact.content)


def _store_reader(args: argparse.Namespace):
    explicit = Path(args.store_config) if getattr(args, "store_config", None) else None
    return load_store_config(str(discover_store_configuration(explicit=explicit).path))


def _run_materialize(args: argparse.Namespace) -> None:
    materialize(Path(args.manifest), args.slide, Path(args.output), write=args.write)


def _run_init(args: argparse.Namespace) -> None:
    initialize_project(Path(args.directory), example=args.example)


def _assert_context_format(closure: RenderClosure, format_name: str | None) -> None:
    if format_name and format_name != closure.context.target.kind:
        raise CliFailure("E_RENDER_FORMAT_CONTEXT", "--format must match the Context target", "cli", "/format", 2)


def _run_draft_render(args: argparse.Namespace) -> None:
    closure = resolve_draft_render(
        project_path=Path(args.project), view_path=Path(args.view), theme_path=Path(args.theme),
        scheme_path=Path(args.scheme), layout_path=Path(args.layout),
        actual_path=Path(args.actual) if args.actual else None,
        summary_path=Path(args.summary) if args.summary else None,
        detail_path=Path(args.detail) if args.detail else None,
        viewport=_parse_viewport(args.viewport), locale=args.locale, target_kind=args.format,
        typesetter=_draft_typesetter_identity(args),
    )
    rendered = _render_review(closure.closure, args, asset_root=closure.asset_root)
    Path(args.output).write_bytes(rendered.artifact.content)


def _run_guided_draft_render(args: argparse.Namespace) -> None:
    draft = resolve_guided_draft_render(
        workspace_path=Path(args.workspace), viewport=_parse_viewport(args.viewport),
        locale=args.locale, target_kind=args.format, typesetter=_draft_typesetter_identity(args),
    )
    rendered = _render_review(draft.closure, args, asset_root=draft.asset_root)
    Path(args.output).write_bytes(rendered.artifact.content)
    if args.provenance:
        provenance = draft.closure.guided_provenance
        if provenance is None:  # defensive: this route must never become an explicit Draft alias
            raise CliFailure("E_AUTHORING_PROVENANCE", "guided closure provenance is required", "authoring")
        destination = Path(args.provenance)
        if destination.exists():
            raise CliFailure("E_AUTHORING_PROVENANCE_OUTPUT", "provenance destination already exists", "authoring", exit_code=2)
        destination.write_text(json.dumps({
            "origin": "draft", "workspaceContentIdentity": provenance.workspace_identity,
            "presetContentIdentity": provenance.preset_identity, "bindingContentIdentity": provenance.binding_identity,
            "normalizerVersion": provenance.normalizer_version,
        }, sort_keys=True) + "\n", encoding="utf-8")


def _run_authoring_command(args: argparse.Namespace) -> None:
    result = apply_authoring_command(Path(args.workspace), parse_authoring_command(Path(args.authoring_command)),
                                     read_workspace=read_authoring_workspace, cas_write=cas_write_authoring_workspace,
                                     cas_write_aggregate=cas_write_authoring_aggregate)
    _write_result(Path(args.result), result)
    if result["status"] != "accepted":
        raise SystemExit(2)


def _parse_viewport(value: str) -> tuple[int, int]:
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise CliFailure("E_COMMAND_VIEWPORT", "viewport must be WIDTHxHEIGHT", "cli", "/viewport", 2)
    try:
        width, height = (int(part) for part in parts)
    except ValueError as error:
        raise CliFailure("E_COMMAND_VIEWPORT", "viewport must be WIDTHxHEIGHT", "cli", "/viewport", 2) from error
    if width <= 0 or height <= 0:
        raise CliFailure("E_COMMAND_VIEWPORT", "viewport dimensions must be positive", "cli", "/viewport", 2)
    return width, height


def _run_render_review_gallery(args: argparse.Namespace) -> None:
    if len(args.context_reference) < 2:
        raise CliFailure("E_SCHEME_GALLERY_INPUT", "at least two Context references are required", "gallery")
    destination = Path(args.output_directory)
    if destination.exists() and any(destination.iterdir()):
        raise CliFailure("E_SCHEME_GALLERY_OUTPUT", "output directory must be empty", "gallery")
    reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=args.require_content_identity)
    entries = []
    for reference_path in args.context_reference:
        closure = resolve_render_context(load_yaml(reference_path), reader)
        scheme = closure.resource("color-scheme")
        if scheme is None:
            raise CliFailure("E_CONTEXT_COLOR_SCHEME", "Color Scheme closure is missing", "gallery")
        entries.append((scheme.id, scheme.content_identity, closure.context.identity.id, reference_path, closure))
    if len({entry[1] for entry in entries}) != len(entries):
        raise CliFailure("E_SCHEME_GALLERY_DUPLICATE", "Color Scheme content identity is duplicated", "gallery")
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    if len({entry[0] for entry in entries}) != len(entries):
        raise CliFailure("E_SCHEME_GALLERY_DUPLICATE", "Color Scheme IDs must be unique in one gallery", "gallery")
    destination.mkdir(parents=True, exist_ok=True)
    outputs = []
    for scheme_id, identity, context_id, _reference, closure in entries:
        output = destination / f"{scheme_id}.svg"
        output.write_bytes(_render_review(closure, args).artifact.content)
        outputs.append({"contextId": context_id, "colorScheme": {"id": scheme_id, "contentIdentity": identity}, "output": output.name})
    (destination / "gallery.json").write_text(json.dumps({"results": outputs}, indent=2) + "\n", encoding="utf-8")


def _run(args: argparse.Namespace) -> None:
    if args.command in {"command-check", "command-apply", "actual-intake", "actual-resolve", "baseline-capture"}:
        try:
            command = parse_document(Path(args.command_path).read_text(encoding="utf-8"), "command-request-v0.2.schema.yaml")
            reader = _store_reader(args)
        except OSError as error:
            raise CliFailure("E_AUTOMATION_RESULT_IO", str(error), "automation", exit_code=3) from error
        required_type = {"actual-intake": "applyActualIntakeBatch", "actual-resolve": "resolveActualObservation", "baseline-capture": "captureSnapshot"}.get(args.command)
        if required_type and command["type"] != required_type:
            result = {"version": "chrona/automation-result/v0.1", "operation": args.command, "status": "rejected", "requestContentIdentity": "sha256:" + "0" * 64, "inputs": [command["target"]], "diagnostics": [{"code": "E_AUTOMATION_OPERATION_UNSUPPORTED"}], "artifacts": []}
        else:
            result = check_command(reader, command) if args.command == "command-check" else apply_actual_command(reader, command)
            result["operation"] = args.command
        _write_result(Path(args.result), result)
        if result["status"] != "accepted":
            raise SystemExit(2)
        return
    if args.command == "baseline-compare":
        try:
            reader = _store_reader(args)
            baseline_reference = load_yaml(args.baseline_reference)
            candidate_reference = load_yaml(args.candidate_reference)
        except OSError as error:
            raise CliFailure("E_AUTOMATION_RESULT_IO", str(error), "automation", exit_code=3) from error
        result = compare_baseline(reader, baseline_reference, reader, candidate_reference)
        _write_result(Path(args.result), result)
        if result["status"] != "accepted":
            raise SystemExit(2)
        return
    if args.command == "render-review":
        _run_render_review(args)
        return
    if args.command == "materialize":
        _run_materialize(args)
        return
    if args.command == "init":
        _run_init(args)
        return
    if args.command == "render":
        _run_draft_render(args)
        return
    if args.command == "render-workspace":
        _run_guided_draft_render(args)
        return
    if args.command == "authoring-command-apply":
        _run_authoring_command(args)
        return
    if args.command == "materialize-presentation-preset":
        _run_authoring_command(args)
        return
    if args.command == "render-review-gallery":
        _run_render_review_gallery(args)
        return
    if args.command == "review":
        reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=args.require_content_identity)
        before = load_project(load_yaml(args.before_reference), reader)
        candidate = load_project(load_yaml(args.candidate_reference), reader)
        output = review_projects(before, candidate)
        if output["status"] != "accepted":
            payload = {
                "status": "rejected",
                "diagnostics": [
                    _diagnostic(item["id"], item["message"], "core", item["path"])
                    for item in output["diagnostics"]
                ],
            }
            print(json.dumps(payload, ensure_ascii=False))
            raise SystemExit(1)
        print(json.dumps(output, indent=2, default=_json_default))
        return
    project = _load_primary_project(args)
    if args.command == "validate":
        diagnostics = validate_project(project)
        if diagnostics:
            _reject(diagnostics)
        print("[]")
        return
    result = schedule(project)
    if not result.ok:
        _reject(result.diagnostics)
    print(json.dumps(_schedule_payload(project, result), indent=2, default=_json_default))


def _schedule_payload(project: dict[str, Any], result: Any) -> dict[str, Any]:
    """Serialize a completed Scheduler result without deriving analysis again."""
    analysis = result.analysis
    payload = {"placements": result.placements, "diagnostics": []}
    if analysis is not None:
        object_order = tuple(project.get("objects", {}))
        payload["analysis"] = {
            "criticalObjectIds": [object_id for object_id in object_order if object_id in analysis.critical],
            "totalFloat": analysis.total_float,
        }
    return payload


def _write_result(destination: Path, result: dict[str, Any]) -> None:
    """Create one result artifact without replacing an existing result."""
    if destination.exists():
        raise CliFailure("E_AUTOMATION_OUTPUT_EXISTS", "result destination already exists", "automation", exit_code=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(json.dumps(result, sort_keys=True, default=_json_default).encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    except FileExistsError as error:
        raise CliFailure("E_AUTOMATION_OUTPUT_EXISTS", "result destination already exists", "automation", exit_code=2) from error
    except OSError as error:
        raise CliFailure("E_AUTOMATION_RESULT_IO", str(error), "automation", exit_code=3) from error
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    try:
        args = _parser().parse_args()
        _run(args)
    except CliFailure as error:
        _emit_failure(error)
    except (SnapshotReadError, ClosureError) as error:
        message = error.detail if isinstance(error, ClosureError) and error.detail else str(error)
        source_ref = error.source_ref if isinstance(error, ClosureError) else "/"
        _emit_failure(CliFailure(error.diagnostic_id, message, "closure", source_ref))
    except json.JSONDecodeError as error:
        _emit_failure(CliFailure("E_INPUT_JSON", str(error), exit_code=2))
    except yaml.YAMLError as error:
        _emit_failure(CliFailure("E_INPUT_YAML", str(error), exit_code=2))
    except OSError as error:
        _emit_failure(CliFailure("E_INPUT_IO", str(error), exit_code=2))
    except ValueError as error:
        code = str(error) if str(error).startswith("E_") else "E_PRESENTATION_REJECTED"
        _emit_failure(CliFailure(code, str(error), "presentation"))
    except SystemExit:
        raise
    except Exception as error:  # pragma: no cover - last-resort CLI boundary
        _emit_failure(CliFailure("E_TOOL_FAILURE", str(error), exit_code=2))
