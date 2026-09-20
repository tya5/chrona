from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

import yaml

from chrona.app.review import review_projects
from chrona.commands.commands import set_typed_field
from chrona.core.diagnostics import Diagnostic
from chrona.core.validation import load_yaml, validate_project
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.model.closure import ClosureError, ClosureResource, resolve_render_context
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.model.settings import PresentationSettingsError, resolve_presentation_settings
from chrona.presentation.renderers.generic import render_svg
from chrona.presentation.review.surface_content import _surface_content_input
from chrona.presentation.review.svg import render_table_timeline_svg
from chrona.presentation.scene.schedule import scene_from_schedule
from chrona.scheduling.scheduler import schedule
from chrona.storage.loader import load_project
from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError


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
        return load_project(reference, LocalSnapshotReader(Path(args.snapshot_root), args.store_identity))
    if not args.project:
        raise CliFailure("E_COMMAND_SYNTAX", "a raw project or complete snapshot mode is required", exit_code=2)
    return load_yaml(args.project)


def _parser() -> JsonArgumentParser:
    parser = JsonArgumentParser(prog="chrona")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=JsonArgumentParser)
    commands = {
        "validate": "validate a raw Draft or immutable Project snapshot",
        "schedule": "derive a Date-only schedule from a raw Draft or immutable snapshot",
        "render": "render the minimal timeline through v0.2 settings or the diagnostic legacy adapter",
    }
    for name, help_text in commands.items():
        command = sub.add_parser(name, help=help_text, description=help_text)
        _add_snapshot_arguments(command)
        if name == "render":
            command.add_argument("--output", "-o", required=True)
            command.add_argument("--presentation-settings", help="resolved settings or preset for the common v0.2 Scene path")

    command = sub.add_parser("render-review", help="render an immutable Render Context v0.3", description="render an immutable Render Context v0.3")
    command.add_argument("--context-reference", required=True, help="immutable Render Context resource-reference YAML")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("review", help="compare two immutable Project snapshots", description="compare two immutable Project snapshots")
    command.add_argument("before_reference")
    command.add_argument("candidate_reference")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)

    command = sub.add_parser("propose-set", help="propose one typed Project field change without writing the input", description="propose one typed Project field change without writing the input")
    command.add_argument("project")
    command.add_argument("object_id")
    command.add_argument("field")
    values = command.add_mutually_exclusive_group(required=True)
    values.add_argument("--value", dest="literal_value", help="literal string value")
    values.add_argument("--value-json", dest="json_value", help="JSON scalar, array, or object")
    return parser


def _resource(resources: tuple[ClosureResource, ...], kind: str) -> dict[str, Any] | None:
    return next((item.value for item in resources if item.kind == kind), None)


def _run_render_review(args: argparse.Namespace) -> None:
    reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity)
    context, resources = resolve_render_context(load_yaml(args.context_reference), reader)
    project = _resource(resources, "project")
    view = _resource(resources, "view")
    preset = _resource(resources, "presentation-preset")
    if project is None or view is None or preset is None:
        raise CliFailure("E_CLOSURE_REQUIRED", "Render Context closure is incomplete", "closure")
    manifests = {
        item.value["packageId"]: item.value
        for item in resources if item.kind == "profile-package"
    }
    result = schedule(project, extension_diagnostics=validate_profiles(project, manifests))
    if not result.ok:
        _reject(result.diagnostics)
    settings = resolve_presentation_settings(preset)
    actual = _resource(resources, "actual-set")
    summary = _resource(resources, "summary-profile")
    detail = _resource(resources, "review-detail-profile")
    projection = build_review_projection(project, result.placements, view, actual)
    surface_content = _surface_content_input(
        projection, project, view, settings, summary, projection.window[0], detail
    )
    capabilities = set(context["body"]["target"]["capabilities"])
    svg = render_table_timeline_svg(
        project["project"].get("title", "Chrona"), projection, project, view, {},
        capabilities, {}, settings=settings, surface_content=surface_content,
    )
    Path(args.output).write_text(svg, encoding="utf-8")


def _run(args: argparse.Namespace) -> None:
    if args.command == "render-review":
        _run_render_review(args)
        return
    if args.command == "review":
        reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity)
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
    if args.command == "propose-set":
        project = load_yaml(args.project)
        if project.get("extensions"):
            raise CliFailure("E_PACKAGE_RESOLUTION_REQUIRED", "Extensions require immutable package resolution", "extensions", "/extensions")
        value = json.loads(args.json_value) if args.json_value is not None else args.literal_value
        result = set_typed_field(project, None, args.object_id, args.field, value)
        if result.status != "accepted":
            _reject_codes(result.diagnostics, "commands")
        print(json.dumps({"status": result.status, "diagnostics": [], "project": result.project}, default=_json_default))
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
    if args.command == "render":
        scene = scene_from_schedule(project, result)
        settings = resolve_presentation_settings(load_yaml(args.presentation_settings)) if args.presentation_settings else None
        svg = render_svg(scene, {"marker", "metadata", "text-alternative"}, settings)
        Path(args.output).write_text(svg, encoding="utf-8")
        return
    print(json.dumps({"placements": result.placements, "diagnostics": []}, indent=2, default=_json_default))


def main() -> None:
    try:
        args = _parser().parse_args()
        _run(args)
    except CliFailure as error:
        _emit_failure(error)
    except (SnapshotReadError, ClosureError) as error:
        _emit_failure(CliFailure(error.diagnostic_id, str(error), "closure"))
    except PresentationSettingsError as error:
        _emit_failure(CliFailure(str(error), str(error), "presentation-settings"))
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
