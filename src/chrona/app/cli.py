from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

import yaml

from chrona.app.review import review_projects
from chrona.core.diagnostics import Diagnostic
from chrona.core.validation import load_yaml, validate_project
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.model.closure import ClosureError, ClosureResource, resolve_render_context
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.sources import SourceInput, measure_sources
from chrona.presentation.model.font_metrics import resolve_font_metrics
from chrona.presentation.renderers.generic import render_svg
from chrona.presentation.review.svg import render_table_timeline_svg
from chrona.presentation.scene.schedule import scene_from_schedule
from chrona.scheduling.scheduler import schedule
from chrona.storage.loader import load_project
from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError
from chrona.operational.baselines import compare_baseline
from chrona.operational.store_config import load_store_config
from chrona.operational.command_engine import apply_actual_command, check_command
from chrona.operational.resources import parse_document


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
        "render": "render the minimal schedule scene",
    }
    for name, help_text in commands.items():
        command = sub.add_parser(name, help=help_text, description=help_text)
        _add_snapshot_arguments(command)
        if name == "render":
            command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("render-review", help="render an immutable Render Context v0.5", description="render an immutable Render Context v0.5")
    command.add_argument("--context-reference", required=True, help="immutable Render Context resource-reference YAML")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("render-review-gallery", help="render deterministic Color Scheme comparison gallery")
    command.add_argument("--context-reference", required=True, action="append", help="immutable Render Context v0.5 resource-reference YAML; repeat for each scheme")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--output-directory", required=True)

    command = sub.add_parser("review", help="compare two immutable Project snapshots", description="compare two immutable Project snapshots")
    command.add_argument("before_reference")
    command.add_argument("candidate_reference")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)

    command = sub.add_parser("baseline-compare", help="compare a named baseline and immutable candidate")
    command.add_argument("--baseline-reference", required=True)
    command.add_argument("--candidate-reference", required=True)
    command.add_argument("--store-config", required=True)
    command.add_argument("--result", required=True)

    for name in ("command-check", "command-apply", "actual-intake", "actual-resolve"):
        command = sub.add_parser(name, help=f"run M26 {name} command")
        command.add_argument("--command", dest="command_path", required=True)
        command.add_argument("--store-config", required=True)
        command.add_argument("--result", required=True)

    return parser


def _resource(resources: tuple[ClosureResource, ...], kind: str) -> dict[str, Any] | None:
    return next((item.value for item in resources if item.kind == kind), None)


def _run_render_review(args: argparse.Namespace) -> None:
    reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity)
    context, resources = resolve_render_context(load_yaml(args.context_reference), reader)
    project = _resource(resources, "project")
    view = _resource(resources, "view")
    theme = context.get("resolvedTheme")
    layout = _resource(resources, "layout-profile")
    if project is None or view is None or theme is None or layout is None:
        raise CliFailure("E_CLOSURE_REQUIRED", "Render Context closure is incomplete", "closure")
    manifests = {
        item.value["packageId"]: item.value
        for item in resources if item.kind == "profile-package"
    }
    result = schedule(project, extension_diagnostics=validate_profiles(project, manifests))
    if not result.ok:
        _reject(result.diagnostics)
    actual = _resource(resources, "actual-set")
    projection = build_review_projection(project, result.placements, view, actual)
    source_inputs = {
        "title": SourceInput((project["project"].get("title", "Chrona"),)),
        "table": SourceInput(tuple(item.title for item in projection.items), len(projection.items), len(view.get("body", {}).get("tableColumns", ())) or 1),
        "timeline": SourceInput(item_count=len(projection.items), span_days=max(1, (projection.window[1] - projection.window[0]).days)),
        "timeline-axis": SourceInput(span_days=max(1, (projection.window[1] - projection.window[0]).days)),
        "summary": SourceInput(("summary",)), "legend": SourceInput(("legend",)),
        "group-details": SourceInput(("group details",)), "observations": SourceInput(("observations",)),
        "milestones": SourceInput(("milestones",)), "annotations": SourceInput(("annotations",)),
        "notes": SourceInput(tuple(str(item.get("text", "")) for item in project.get("annotations", {}).values()) or ("notes",)),
    }
    environment = context["body"]["environment"]
    theme_body = theme["body"]
    family_token = theme_body.get("roles", {}).get("text", {}).get("fontFamily")
    family = theme_body.get("values", {}).get(family_token, {}).get("value")
    if not isinstance(family, str):
        raise CliFailure("E_THEME_ROLE_REQUIRED", "text.fontFamily is required", "theme")
    revision = context["body"]["theme"]["revision"]["token"]
    font_metrics = resolve_font_metrics(family, environment["fontMetrics"], asset_root=Path(args.snapshot_root) / revision)
    measured = measure_sources(source_inputs, theme, font_metrics=font_metrics)
    resolved_layout = resolve_layout_profile(layout, available_sources=set(source_inputs), theme=theme)
    node_measurements = {}
    def bind(node: dict[str, Any]) -> None:
        if node["kind"] == "slot":
            node_measurements[node["id"]] = measured.measurements[node["source"]]
        for child in node.get("children", ()):
            bind(child)
    bind(resolved_layout.profile["root"])
    viewport = environment["viewport"]
    manifest = solve_layout(resolved_layout, viewport_inline=viewport["inlineSize"], viewport_block=viewport["blockSize"], measurements=node_measurements)
    from chrona.presentation.scene.review import SlotRect
    slots = {
        item.source: SlotRect(float(item.bounds.inline), float(item.bounds.block), float(item.bounds.inline_size), float(item.bounds.block_size))
        for item in manifest.decisions if item.source is not None
    }
    capabilities = set(context["body"]["target"]["capabilities"])
    svg = render_table_timeline_svg(
        project["project"].get("title", "Chrona"), projection, project, view, theme,
        capabilities, {}, slots=slots, viewport=(float(viewport["inlineSize"]), float(viewport["blockSize"])), metric_values=dict(measured.metric_values), font_metrics=font_metrics,
    )
    Path(args.output).write_text(svg, encoding="utf-8")


def _run_render_review_gallery(args: argparse.Namespace) -> None:
    if len(args.context_reference) < 2:
        raise CliFailure("E_SCHEME_GALLERY_INPUT", "at least two Context references are required", "gallery")
    destination = Path(args.output_directory)
    if destination.exists() and any(destination.iterdir()):
        raise CliFailure("E_SCHEME_GALLERY_OUTPUT", "output directory must be empty", "gallery")
    reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity)
    entries = []
    for reference_path in args.context_reference:
        context, resources = resolve_render_context(load_yaml(reference_path), reader)
        scheme = next((item for item in resources if item.kind == "color-scheme"), None)
        if scheme is None:
            raise CliFailure("E_CONTEXT_COLOR_SCHEME", "Color Scheme closure is missing", "gallery")
        entries.append((scheme.id, scheme.content_identity, context["id"], reference_path))
    if len({entry[1] for entry in entries}) != len(entries):
        raise CliFailure("E_SCHEME_GALLERY_DUPLICATE", "Color Scheme content identity is duplicated", "gallery")
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    if len({entry[0] for entry in entries}) != len(entries):
        raise CliFailure("E_SCHEME_GALLERY_DUPLICATE", "Color Scheme IDs must be unique in one gallery", "gallery")
    destination.mkdir(parents=True, exist_ok=True)
    outputs = []
    for scheme_id, identity, context_id, reference_path in entries:
        output = destination / f"{scheme_id}.svg"
        rendered_args = argparse.Namespace(**vars(args), context_reference=reference_path, output=str(output))
        _run_render_review(rendered_args)
        outputs.append({"contextId": context_id, "colorScheme": {"id": scheme_id, "contentIdentity": identity}, "output": output.name})
    (destination / "gallery.json").write_text(json.dumps({"results": outputs}, indent=2) + "\n", encoding="utf-8")


def _run(args: argparse.Namespace) -> None:
    if args.command in {"command-check", "command-apply", "actual-intake", "actual-resolve"}:
        command = parse_document(Path(args.command_path).read_text(encoding="utf-8"), "command-request-v0.2.schema.yaml")
        required_type = {"actual-intake": "applyActualIntakeBatch", "actual-resolve": "resolveActualObservation"}.get(args.command)
        if required_type and command["type"] != required_type:
            result = {"version": "chrona/automation-result/v0.1", "operation": args.command, "status": "rejected", "requestContentIdentity": "sha256:" + "0" * 64, "inputs": [command["target"]], "diagnostics": [{"code": "E_AUTOMATION_OPERATION_UNSUPPORTED"}], "artifacts": []}
        else:
            reader = load_store_config(args.store_config)
            result = check_command(reader, command) if args.command == "command-check" else apply_actual_command(reader, command)
            result["operation"] = args.command
        _write_result(Path(args.result), result)
        if result["status"] != "accepted":
            raise SystemExit(2)
        return
    if args.command == "baseline-compare":
        reader = load_store_config(args.store_config)
        result = compare_baseline(reader, load_yaml(args.baseline_reference), reader, load_yaml(args.candidate_reference))
        _write_result(Path(args.result), result)
        if result["status"] != "accepted":
            raise SystemExit(2)
        return
    if args.command == "render-review":
        _run_render_review(args)
        return
    if args.command == "render-review-gallery":
        _run_render_review_gallery(args)
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
        svg = render_svg(scene, {"marker", "metadata", "text-alternative"})
        Path(args.output).write_text(svg, encoding="utf-8")
        return
    print(json.dumps({"placements": result.placements, "diagnostics": []}, indent=2, default=_json_default))


def _write_result(destination: Path, result: dict[str, Any]) -> None:
    """Create one result artifact without replacing an existing result."""
    if destination.exists():
        raise CliFailure("E_AUTOMATION_OUTPUT_EXISTS", "result destination already exists", "automation", exit_code=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(json.dumps(result, sort_keys=True, default=_json_default).encode("utf-8"))
        os.link(temporary, destination)
    except FileExistsError as error:
        raise CliFailure("E_AUTOMATION_OUTPUT_EXISTS", "result destination already exists", "automation", exit_code=2) from error
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    try:
        args = _parser().parse_args()
        _run(args)
    except CliFailure as error:
        _emit_failure(error)
    except (SnapshotReadError, ClosureError) as error:
        _emit_failure(CliFailure(error.diagnostic_id, str(error), "closure"))
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
