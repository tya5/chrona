from __future__ import annotations

import argparse
import copy
from hashlib import sha256
import importlib.util
import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

from chrona.usecases.review_projects import review_projects
from chrona.app.agent_tools import registry_document
from chrona.app.agent_workspace import WorkspaceScope
from chrona.core.diagnostics import Diagnostic
from chrona.core.identity import content_identity, json_value
from chrona.core.source_ranges import attach_ranges
from chrona.core.validation import load_yaml
from chrona.presentation.model.closure import DEFAULT_DRAFT_VIEWPORT, RenderClosure, resolve_guided_draft_render, resolve_render_context
from chrona.presentation.contracts import TypesetterIdentity
from chrona.usecases.draft_render import DraftRenderRequest, parse_viewport, render_draft, typesetter_identity, warning_payloads
from chrona.usecases.failure_report import FailureReport, StableFailure, diagnostic_record, rejection_report, report_failure
from chrona.usecases.project_checks import schedule_project_mapping, validate_project_mapping
from chrona.usecases.render_review import RenderRejected, RenderRequest, RenderedReview, render_review
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.loader import load_project
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.operational.store_config import load_store_config
from chrona.operational.store_commands import OPERATIONS, run_store_command
from chrona.operational.store_reads import compare_store_baseline, load_reference, snapshot_reader_for
from chrona.usecases.context_review import render_context_closure, resolve_context_closure
from chrona.usecases.authoring_commands import apply_authoring_command, parse_authoring_command, workspace_revision
from chrona.operational.authoring_commands import cas_write_authoring_aggregate, cas_write_authoring_workspace, read_authoring_workspace
from chrona.operational.resources import parse_command, parse_document
from chrona.usecases.materialize import MaterializationError, materialize
from chrona.usecases.local_authoring import discover_store_configuration, initialize_project
from chrona.usecases.terse_compile import PlanCompilation, compile_plan, input_unreadable, output_exists, position_findings
from chrona.usecases.preset_library import copy_builtin_preset, list_builtin_presets
from chrona.usecases.skill_library import copy_skill
from chrona.presentation.icons.importer import copy_material_symbols_outline_rounded_catalog, import_iconify, import_theme_assets
from chrona.presentation.fonts.importer import import_font
from chrona.presentation.scene.serialization import SceneSerializationError, serialize_scene
from chrona.resources import example_ids, safe_load


CliFailure = StableFailure


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CliFailure("E_COMMAND_SYNTAX", message, exit_code=2)


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


_diagnostic = diagnostic_record


def _emit_report(report: FailureReport) -> NoReturn:
    print(json.dumps(report.payload(), ensure_ascii=False))
    raise SystemExit(report.exit_code)


def _emit_failure(failure: CliFailure) -> NoReturn:
    _emit_report(report_failure(failure))


def _emit_render_result(rendered: RenderedReview) -> None:
    """One machine-readable success channel; warnings never change exit 0."""
    print(json.dumps({"status": "ok", "diagnostics": [], "warnings": warning_payloads(rendered)},
                     ensure_ascii=False, sort_keys=True))


def _reject(diagnostics: list[Diagnostic], component: str = "core") -> NoReturn:
    if _PLAN_SOURCE is not None:
        # a plan (.chrona) compiled to the Project these findings name: report the line the author edits
        plan, source = _PLAN_SOURCE
        _compile_failure(position_findings(plan, diagnostics, source, component), to_stderr=False)
    _emit_report(rejection_report(diagnostics, component))


# The Core validation findings (src/chrona/core/validation.py): they point at a node of the file. Scheduler findings
# (E_FIXED_TARGET_VIOLATION, E_UNSUPPORTED_CYCLE, E_CONTRADICTORY_BOUNDS, ...) name relations by id and keep the legacy shape.
_RANGED_CODES = frozenset({
    "E_SCHEMA", "E_REFERENCE", "E_PARENT_NOT_FOUND", "E_PARENT_CYCLE", "E_SELF_PARENT", "E_DUPLICATE_WBS_CODE",
    "E_CALENDAR_REQUIRED", "E_INVALID_AMOUNT", "E_INVALID_SPAN", "E_ROLLUP_EMPTY", "E_PROJECT_ATTACH_SELF",
    "E_PROJECT_ATTACH_SOURCE_NOT_POINT", "E_PROJECT_ATTACH_TARGET_NOT_SPAN", "E_PROJECT_ATTACH_TARGET_UNKNOWN",
    "E_PROJECT_PERIOD_OBJECT_UNKNOWN", "E_SCENARIO_INVALID", "E_SCENARIO_NOT_FOUND", "E_SCENARIO_OBJECT_NOT_FOUND",
    "E_SCENARIO_RELATION_DUPLICATE", "E_SCENARIO_RELATION_NOT_FOUND"})


def _with_source_ranges(args: argparse.Namespace, diagnostics: Any) -> Any:
    """The validation findings with the line and column of their node when the input is a raw YAML Project (#1303).

    Scheduler findings keep the legacy shape exactly (Spec 65 section 7)."""
    path = getattr(args, "project", None)
    if not path or _is_plan_path(path) or any((args.snapshot_reference, args.snapshot_root, args.store_identity)):
        return diagnostics
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return diagnostics
    located = iter(attach_ranges([item for item in diagnostics if item.id in _RANGED_CODES], text))
    return [next(located) if item.id in _RANGED_CODES else item for item in diagnostics]


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
    command.add_argument("project", nargs="?", help="raw Draft Project path (YAML, or a terse .chrona plan)")
    command.add_argument("--snapshot-reference", help="immutable Project resource-reference YAML")
    command.add_argument("--snapshot-root", help="local snapshot adapter root")
    command.add_argument("--store-identity", help="expected local snapshot store identity")
    command.add_argument("--allow-missing-content-identity", action="store_true", help="accept references without an exact content identity (explicit opt-out)")


def _add_draft_target_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--format", choices=("svg", "png", "pdf", "typst", "tikz"),
                         help="output target (default: infer from .svg/.png/.pdf/.typ/.tex; SVG without a suffix)")
    command.add_argument("--visual-profile", default=None,
                         choices=("chrona-output/visual/v0.5-baseline", "chrona-output/visual/v0.6-svg", "chrona-output/visual/v0.6-png", "chrona-output/visual/v0.7-svg", "chrona-output/visual/v0.7-png"),
                         help="exact visual capability profile (default: the preset's preferred profile, else baseline)")
    command.add_argument("--typesetter-engine", help="required with --format typst or tikz")
    command.add_argument("--typesetter-version", help="required exact engine version with --format typst or tikz")
    command.add_argument("--typesetter-adapter-grammar", help="required adapter grammar with --format typst or tikz")


_OUTPUT_SUFFIX_TARGETS = {".svg": "svg", ".png": "png", ".pdf": "pdf", ".typ": "typst", ".tex": "tikz"}


def _resolve_output_target(output: str, requested: str | None) -> str:
    """Negotiate a CLI filename against a declared target before rendering."""
    suffix = Path(output).suffix.lower()
    if not suffix:
        return requested or "svg"
    inferred = _OUTPUT_SUFFIX_TARGETS.get(suffix)
    if inferred is None:
        raise CliFailure(
            "E_RENDER_OUTPUT_EXTENSION",
            f"output suffix {suffix} is unknown; use one of {', '.join(_OUTPUT_SUFFIX_TARGETS)} or no suffix",
            "cli", "/output", 2,
        )
    if requested is not None and inferred != requested:
        raise CliFailure(
            "E_RENDER_OUTPUT_FORMAT_MISMATCH",
            f"output suffix {suffix} selects {inferred}, but the target is {requested}",
            "cli", "/output", 2,
        )
    return requested or inferred


def _draft_typesetter_identity(args: argparse.Namespace, target_kind: str) -> TypesetterIdentity | None:
    return typesetter_identity(args.typesetter_engine, args.typesetter_version, args.typesetter_adapter_grammar, target_kind)


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
        return load_project(reference, LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=not args.allow_missing_content_identity))
    if not args.project:
        raise CliFailure("E_COMMAND_SYNTAX", "a raw project or complete snapshot mode is required", exit_code=2)
    if _is_plan_path(args.project):
        plan = _compile_plan_argument(args.project)
        _set_plan_source(plan, args.project)
        return safe_load(plan.yaml)
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
    command.add_argument("project", help="Draft Project YAML path, or a terse .chrona plan")
    command.add_argument("--preset", help="Presentation preset YAML path, or a builtin catalogue id (see `chrona preset list`); omit it to use bundled chrona-default-draft; explicit resource flags override its members")
    command.add_argument("--view", help="View YAML path")
    command.add_argument("--theme", help="Theme YAML path")
    command.add_argument("--scheme", help="Color Scheme YAML path")
    command.add_argument("--layout", help="Layout Profile YAML path")
    command.add_argument("--actual", help="Actual Set YAML path")
    command.add_argument("--summary", help="Summary Profile YAML path")
    command.add_argument("--detail", help="Review Detail Profile YAML path")
    command.add_argument("--icon-catalog", action="append", default=[],
                         help="explicit local icon catalog YAML path; repeatable")
    command.add_argument("--font-metrics", help="declared-metrics-v3 YAML descriptor; paths resolve beside it")
    command.add_argument("--system-fonts", action="store_true", help="require the Theme's exact installed face through fontconfig (installed fonts are always usable; this refuses a fallback)")
    command.add_argument("--viewport", default=f"{DEFAULT_DRAFT_VIEWPORT[0]}xauto", help="Draft viewport WIDTHxHEIGHT or WIDTHxauto (default: 1600xauto)")
    command.add_argument("--locale", choices=("en-US", "ja-JP"), default="en-US",
                         help="render locale: en-US or ja-JP (default: en-US)")
    _add_draft_target_arguments(command)
    command.add_argument("--output", "-o", required=True)
    command.add_argument("--emit-scene", help="write a schema-validated inspection Scene JSON without replacing an existing file")

    icon = sub.add_parser("icon-catalog", help="create a normalized local icon catalog")
    icon_sub = icon.add_subparsers(dest="icon_command", required=True, parser_class=JsonArgumentParser)
    command = icon_sub.add_parser("import", help="import a local Iconify JSON collection or declared Theme assets")
    command.add_argument("source", nargs="?", help="local Iconify JSON collection (omit with --theme-assets)")
    command.add_argument("--theme-assets", help="local chrona/theme-asset-source/v0.2 YAML")
    command.add_argument("--output", required=True, help="new v0.3 icon-only or v0.5 Theme asset catalog YAML")
    command.add_argument("--license-spdx", help="declared upstream SPDX identifier for Iconify input")
    command.add_argument("--notice-file", help="local complete upstream license notice for Iconify input")
    command.add_argument("--set", dest="icon_set", help="canonical set name (defaults to collection prefix)")
    command.add_argument("--alias", action="append", default=[], help="additional set alias; repeatable")
    command.add_argument("--include", help="optional local newline-delimited canonical icon-name manifest")
    command.add_argument("--source-version", help="explicit upstream collection/package version for catalog provenance")
    command = icon_sub.add_parser("material-default", help="copy the bundled Material Symbols Outline Rounded catalog")
    command.add_argument("--output", required=True, help="new explicit local catalog YAML")

    font = sub.add_parser("font", help="create a declared local font closure")
    font_sub = font.add_subparsers(dest="font_command", required=True, parser_class=JsonArgumentParser)
    command = font_sub.add_parser("import", help="import one static, TTC, or instantiated variable font")
    command.add_argument("source", help="local TTF, OTF, or TTC font")
    command.add_argument("--family", required=True, help="declared font family")
    command.add_argument("--weight", required=True, type=int, help="declared CSS-like numeric weight")
    command.add_argument("--output", required=True, help="new or existing local font asset directory")
    command.add_argument("--index", type=int, default=0, help="TTC face index (default: 0)")
    command.add_argument("--axis", action="append", default=[], metavar="TAG=VALUE", help="instantiate one variable-font axis; repeatable")

    workspace = sub.add_parser("workspace", help="inspect a guided authoring workspace")
    workspace_sub = workspace.add_subparsers(dest="workspace_command", required=True, parser_class=JsonArgumentParser)
    command = workspace_sub.add_parser("revision", help="print the current guided workspace revision")
    command.add_argument("workspace", help="guided authoring workspace YAML path")

    identity = sub.add_parser("identity", help="inspect an immutable identity without changing input")
    identity_sub = identity.add_subparsers(dest="identity_kind", required=True, parser_class=JsonArgumentParser)
    command = identity_sub.add_parser("bytes", help="print the SHA-256 identity of exact file bytes")
    command.add_argument("path", help="local file path")
    command = identity_sub.add_parser("document", help="print the canonical identity of one YAML or JSON document")
    command.add_argument("path", help="local YAML or JSON document path")

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
    command.add_argument("--viewport", default=f"{DEFAULT_DRAFT_VIEWPORT[0]}xauto", help="Draft viewport WIDTHxHEIGHT or WIDTHxauto (default: 1600xauto)")
    command.add_argument("--locale", choices=("en-US", "ja-JP"), default="en-US",
                         help="render locale: en-US or ja-JP (default: en-US)")
    _add_draft_target_arguments(command)
    command.add_argument("--provenance", help="write non-Scene guided closure provenance JSON")
    command.add_argument("--output", "-o", required=True)

    command = sub.add_parser("render-review", help="render an immutable Render Context v0.8", description="render an immutable Render Context v0.8")
    command.add_argument("--context-reference", required=True, help="immutable Render Context resource-reference YAML")
    command.add_argument("--store-config", help="Store config YAML (for example .chrona/store.yaml); its integrity setting applies and replaces --snapshot-root/--store-identity")
    command.add_argument("--snapshot-root", help="local snapshot adapter root (required without --store-config)")
    command.add_argument("--store-identity", help="expected local snapshot store identity (required without --store-config)")
    command.add_argument("--allow-missing-content-identity", action="store_true", help="accept references without an exact content identity (explicit opt-out)")
    command.add_argument("--reject-unused-closure-inputs", action="store_true", help="reject a render whose Context declares inputs the render never reads")
    command.add_argument("--format", choices=("svg", "png", "pdf", "typst", "tikz"), help="assert the Context target format")
    command.add_argument("--output", "-o", required=True)
    command.add_argument("--emit-scene", help="write a schema-validated inspection Scene JSON without replacing an existing file")

    command = sub.add_parser("materialize", help="materialize one declared immutable example Context")
    command.add_argument("manifest", help="example materializer manifest")
    command.add_argument("--slide", required=True, help="declared slide identifier")
    command.add_argument("--output", "-o", required=True, help="empty output directory")
    command.add_argument("--write", action="store_true", help="replace the manifest-declared generated artifact")

    command = sub.add_parser("compile", help="compile a terse plan to Project YAML",
                             description="compile a terse plan (.chrona) to Project YAML; the YAML is the authority afterwards")
    command.add_argument("plan", help="terse plan path, or - for standard input")
    command.add_argument("--output", "-o", help="write the Project YAML here and refuse to replace an existing file (default: standard output)")

    command = sub.add_parser("init", help="create a non-overwriting local Chrona project")
    command.add_argument("directory", nargs="?", default=".")
    command.add_argument("--example", choices=example_ids(),
                         help="create a named example instead of the editable minimal starter: halcyon-1 is the full corpus, onboarding the seven numbered tutorial stages")

    skill = sub.add_parser("skill", help="copy the packaged chrona agent skill")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True, parser_class=JsonArgumentParser)
    command = skill_sub.add_parser("copy", help="copy the agent skill into an empty directory")
    command.add_argument("--output", "-o", required=True, help="empty or absent output directory")

    command = sub.add_parser("mcp", help="serve the agent tools over MCP on standard input and output; read-only unless --allow-write",
                             description="serve validate_project, schedule_project, render_draft, list_presets, render_review, compare_baseline, check_command and apply_command to an MCP client; render_review and compare_baseline read a Store inside the workspace; apply_command writes a Store only with --allow-write; needs the optional chrona[mcp] extra")
    command.add_argument("--workspace", help="the only directory the tools may read, and below which a Store may be written (default: the current directory)")
    command.add_argument("--allow-write", action="store_true", help="let apply_command write the Store (configuration, not approval: it has no approval step); without it the server is read-only and the call is refused with E_MCP_WRITE_DISABLED")
    command.add_argument("--list-tools", action="store_true", help="print the tool registry as JSON and exit (needs no MCP SDK)")

    preset = sub.add_parser("preset", help="copy or list a builtin presentation preset")
    preset_sub = preset.add_subparsers(dest="preset_command", required=True, parser_class=JsonArgumentParser)
    command = preset_sub.add_parser("copy", help="copy one named builtin preset")
    command.add_argument("id", help="builtin preset identifier")
    command.add_argument("--output", "-o", required=True, help="empty output directory")
    preset_sub.add_parser("list", help="list every builtin preset id and its gallery set")


    command = sub.add_parser("render-review-gallery", help="render deterministic Color Scheme comparison gallery")
    command.add_argument("--context-reference", required=True, action="append", help="immutable Render Context v0.8 resource-reference YAML; repeat for each scheme")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--allow-missing-content-identity", action="store_true", help="accept references without an exact content identity (explicit opt-out)")
    command.add_argument("--output-directory", required=True)

    command = sub.add_parser("review", help="compare two immutable Project snapshots", description="compare two immutable Project snapshots")
    command.add_argument("before_reference")
    command.add_argument("candidate_reference")
    command.add_argument("--snapshot-root", required=True)
    command.add_argument("--store-identity", required=True)
    command.add_argument("--allow-missing-content-identity", action="store_true", help="accept references without an exact content identity (explicit opt-out)")

    command = sub.add_parser("baseline-compare", help="compare a named baseline and immutable candidate")
    command.add_argument("--baseline-reference", required=True)
    command.add_argument("--candidate-reference", required=True)
    command.add_argument("--store-config")
    command.add_argument("--result", required=True)

    for name in OPERATIONS:
        command = sub.add_parser(name, help=f"run M26 {name} command")
        command.add_argument("--command", dest="command_path", required=True)
        command.add_argument("--store-config")
        command.add_argument("--result", required=True)

    return parser



def _render_review(closure: RenderClosure, args: argparse.Namespace, *, asset_root: Path | None = None,
                   draft_font_resolution=None) -> RenderedReview:
    """Adapt one resolved closure to the render use case; its failures are reported by `main`."""
    request = RenderRequest(
        closure=closure, snapshot_root=Path(getattr(args, "snapshot_root", ".")),
        scheduler=ReferenceScheduler(),
        require_all_inputs_read=getattr(args, "reject_unused_closure_inputs", False),
        asset_root=asset_root,
        draft_auto_block=getattr(args, "draft_auto_block", False),
        draft_font_resolution=draft_font_resolution,
    )
    return render_review(request)


def _render_review_reader(args: argparse.Namespace, reference: dict[str, Any]) -> tuple[LocalSnapshotReader, Path]:
    """Reader and snapshot root from explicit flags, or from the Store config entry the Context reference names (its `integrity` applies)."""
    allow_missing = args.allow_missing_content_identity
    if args.store_config is None:
        if args.snapshot_root is None or args.store_identity is None:
            raise CliFailure("E_COMMAND_SYNTAX", "render-review requires --store-config or both --snapshot-root and --store-identity", exit_code=2)
        root = Path(args.snapshot_root)
        return LocalSnapshotReader(root, args.store_identity, require_content_identity=not allow_missing), root
    if args.snapshot_root is not None or args.store_identity is not None:
        raise CliFailure("E_COMMAND_SYNTAX", "--store-config replaces --snapshot-root and --store-identity", exit_code=2)
    try:
        config = load_store_config(str(discover_store_configuration(explicit=Path(args.store_config)).path))
    except (OSError, ValueError) as error:
        raise CliFailure("E_STORE_CONFIG_REQUIRED", f"cannot use Store config {args.store_config}: {error}", "store-config", exit_code=2) from error
    return snapshot_reader_for(config, reference, allow_missing_content_identity=allow_missing)


def _run_render_review(args: argparse.Namespace) -> None:
    reference = load_reference(args.context_reference)
    reader, args.snapshot_root = _render_review_reader(args, reference)
    closure = resolve_context_closure(reference, reader)
    _assert_context_format(closure, args.format)
    _resolve_output_target(args.output, closure.context.target.kind)
    rendered = render_context_closure(closure, Path(args.snapshot_root), reject_unused_inputs=args.reject_unused_closure_inputs)
    _write_render_outputs(rendered, args)
    _emit_render_result(rendered)


def _store_reader(args: argparse.Namespace):
    explicit = Path(args.store_config) if getattr(args, "store_config", None) else None
    return load_store_config(str(discover_store_configuration(explicit=explicit).path))


def _run_materialize(args: argparse.Namespace) -> None:
    try:
        materialize(Path(args.manifest), args.slide, Path(args.output), write=args.write)
    except MaterializationError as error:
        if error.code != "E_MATERIALIZER_MISMATCH":
            raise
        command = f"chrona materialize {args.manifest} --slide {args.slide} --output {args.output} --write"
        raise CliFailure(error.code, f"{error.detail}; review the generated diff, then run `{command}` to refresh intended evidence", "materializer") from error


def _compile_failure(diagnostics: tuple, *, to_stderr: bool, status: str = "rejected", exit_code: int = 1) -> NoReturn:
    """Diagnostics go to the stream that does not carry the YAML, so `compile > project.yaml` is redirect-safe."""
    payload = {"status": status, "diagnostics": [item.as_dict() for item in diagnostics]}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr if to_stderr else sys.stdout)
    raise SystemExit(exit_code)


def _run_compile(args: argparse.Namespace) -> None:
    to_stderr = args.output is None
    try:
        data = sys.stdin.buffer.read() if args.plan == "-" else Path(args.plan).read_bytes()
    except OSError as error:
        _compile_failure((input_unreadable(args.plan, error.strerror or str(error)),), to_stderr=to_stderr, status="failed", exit_code=2)
    result = compile_plan(data, args.plan)
    if result.yaml is None:
        _compile_failure(result.diagnostics, to_stderr=to_stderr, status="failed" if result.defect else "rejected",
                         exit_code=2 if result.defect else 1)
    if args.output is None:
        sys.stdout.buffer.write(result.yaml)
        sys.stdout.buffer.flush()
        return
    from chrona.storage.publication import publish_exclusive
    try:
        publish_exclusive(Path(args.output), result.yaml)
    except FileExistsError:
        _compile_failure((output_exists(args.output),), to_stderr=False, status="failed", exit_code=2)


# The plan (.chrona) behind the Project being checked or rendered, so that scheduler and Core findings are positioned on
# its lines. One command runs per process; `main()` clears it on entry so in-process callers see no leak.
_PLAN_SOURCE: tuple[PlanCompilation, str] | None = None


def _set_plan_source(plan: PlanCompilation, source: str) -> None:
    global _PLAN_SOURCE
    _PLAN_SOURCE = (plan, source)


def _is_plan_path(path: str | None) -> bool:
    """A terse plan is recognised by the suffix of the file argument alone (design 9.5)."""
    return bool(path) and path.lower().endswith(".chrona") and Path(path).suffix != ""


def _compile_plan_argument(path: str) -> PlanCompilation:
    """Compile the plan a `validate`, `schedule` or `render` argument names; a rejected plan never reaches the command."""
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        _compile_failure((input_unreadable(path, error.strerror or str(error)),), to_stderr=False, status="failed", exit_code=2)
    plan = compile_plan(data, path)
    if plan.yaml is None:
        _compile_failure(plan.diagnostics, to_stderr=False, status="failed" if plan.defect else "rejected",
                         exit_code=2 if plan.defect else 1)
    return plan


def _run_draft_render_of_plan(args: argparse.Namespace) -> None:
    """Render a `.chrona` plan through a temporary Project file, as `--preset <id>` does for a builtin preset.

    The closure then holds the compiler's bytes as the Project, so the render equals compile-then-render by
    construction; the temporary directory is removed on every exit path.
    """
    plan = _compile_plan_argument(args.project)
    _set_plan_source(plan, args.project)
    tmp = tempfile.TemporaryDirectory(prefix="chrona-plan-")
    try:
        project_path = Path(tmp.name) / "project.yaml"
        project_path.write_bytes(plan.yaml)
        rendered_args = copy.copy(args)
        rendered_args.project = str(project_path)
        _run_draft_render(rendered_args)
    except RenderRejected as error:  # the scheduler's findings name the compiled Project: report them on the plan's lines
        _reject(error.diagnostics, error.component)
    finally:
        tmp.cleanup()


def _run_init(args: argparse.Namespace) -> None:
    initialize_project(Path(args.directory), example=args.example)


def _mcp_sdk_installed() -> bool:
    """Whether the SDK is importable: `mcp.server` is the check, because a plain directory named `mcp` is a namespace package."""
    try:
        return importlib.util.find_spec("mcp.server") is not None
    except (ImportError, ValueError):
        return False


def _run_mcp(args: argparse.Namespace) -> None:
    """`--list-tools` prints the registry without the SDK; otherwise serve it, or say how to install the extra."""
    if args.list_tools:
        if args.workspace is not None:
            WorkspaceScope(args.workspace)
        print(json.dumps(registry_document(), indent=2, ensure_ascii=False))
        return
    if not _mcp_sdk_installed():
        raise CliFailure("E_MCP_UNAVAILABLE", "the MCP server needs the optional MCP SDK: pip install 'chrona[mcp]'",
                         "mcp", exit_code=2)
    from chrona.app.mcp_server import serve
    serve(args.workspace if args.workspace is not None else ".", allow_write=args.allow_write)


def _run_preset_copy(args: argparse.Namespace) -> None:
    copy_builtin_preset(args.id, Path(args.output))


def _run_preset_list(_args: argparse.Namespace) -> None:
    print(json.dumps({"status": "ok", "presets": list_builtin_presets()}, ensure_ascii=False))


def _assert_context_format(closure: RenderClosure, format_name: str | None) -> None:
    if format_name and format_name != closure.context.target.kind:
        raise CliFailure("E_RENDER_FORMAT_CONTEXT", "--format must match the Context target", "cli", "/format", 2)


def _run_draft_render(args: argparse.Namespace) -> None:
    target_kind = _resolve_output_target(args.output, args.format)
    result = render_draft(DraftRenderRequest(
        project=args.project, target_kind=target_kind, preset=args.preset, view=args.view, theme=args.theme,
        scheme=args.scheme, layout=args.layout, actual=args.actual, summary=args.summary, detail=args.detail,
        icon_catalogs=tuple(args.icon_catalog), font_metrics=args.font_metrics, system_fonts=args.system_fonts,
        viewport=args.viewport, locale=args.locale, visual_profile=args.visual_profile,
        typesetter_engine=args.typesetter_engine, typesetter_version=args.typesetter_version,
        typesetter_adapter_grammar=args.typesetter_adapter_grammar,
    ))
    _write_render_outputs(result.rendered, args)
    _emit_render_result(result.rendered)


def _write_render_outputs(rendered: RenderedReview, args: argparse.Namespace) -> None:
    """Write the unchanged target artifact and an optional prevalidated Scene sibling."""
    destination = getattr(args, "emit_scene", None)
    scene_path: Path | None = None
    scene_bytes: bytes | None = None
    if destination:
        scene_path = Path(destination)
        if scene_path.exists():
            raise CliFailure("E_SCENE_OUTPUT_EXISTS", "scene output destination already exists", "scene", exit_code=2)
        try:
            scene_bytes = serialize_scene(rendered.scene)
        except SceneSerializationError as error:
            raise CliFailure(str(error), "completed Scene cannot be serialized", "scene") from error
    Path(args.output).write_bytes(rendered.artifact.content)
    if scene_path is not None and scene_bytes is not None:
        from chrona.storage.publication import publish_exclusive
        try:
            publish_exclusive(scene_path, scene_bytes)
        except (FileExistsError, OSError) as error:
            raise CliFailure("E_SCENE_OUTPUT", str(error), "scene", exit_code=2) from error


def _run_guided_draft_render(args: argparse.Namespace) -> None:
    target_kind = _resolve_output_target(args.output, args.format)
    draft = resolve_guided_draft_render(
        workspace_path=Path(args.workspace), viewport=_parse_viewport(args.viewport),
        locale=args.locale, target_kind=target_kind, visual_profile=args.visual_profile,
        typesetter=_draft_typesetter_identity(args, target_kind),
    )
    args.draft_auto_block = draft.auto_block
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
    _emit_render_result(rendered)


def _run_authoring_command(args: argparse.Namespace) -> None:
    result = apply_authoring_command(Path(args.workspace), parse_authoring_command(Path(args.authoring_command)),
                                     read_workspace=read_authoring_workspace, cas_write=cas_write_authoring_workspace,
                                     cas_write_aggregate=cas_write_authoring_aggregate)
    _write_result(Path(args.result), result)
    if result["status"] != "accepted":
        raise SystemExit(2)


def _run_workspace_revision(args: argparse.Namespace) -> None:
    print(workspace_revision(Path(args.workspace), read_workspace=read_authoring_workspace))


def _run_identity(args: argparse.Namespace) -> None:
    path = Path(args.path)
    if args.identity_kind == "bytes":
        print("sha256:" + sha256(path.read_bytes()).hexdigest())
        return
    value = json_value(safe_load(path.read_bytes()))
    if not isinstance(value, dict):
        raise CliFailure("E_IDENTITY_DOCUMENT", "document identity requires a YAML or JSON object", "identity", "/", 2)
    print(content_identity(value))


_parse_viewport = parse_viewport


def _run_render_review_gallery(args: argparse.Namespace) -> None:
    if len(args.context_reference) < 2:
        raise CliFailure("E_SCHEME_GALLERY_INPUT", "at least two Context references are required", "gallery")
    destination = Path(args.output_directory)
    if destination.exists() and any(destination.iterdir()):
        raise CliFailure("E_SCHEME_GALLERY_OUTPUT", "output directory must be empty", "gallery")
    reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=not args.allow_missing_content_identity)
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
    if args.command == "font":
        result = import_font(Path(args.source), Path(args.output), family=args.family,
                             weight=args.weight, index=args.index, axis=tuple(args.axis))
        print(json.dumps(result, sort_keys=True))
        return
    if args.command == "icon-catalog":
        if args.icon_command == "import":
            if args.theme_assets:
                if args.source or args.license_spdx or args.notice_file or args.icon_set or args.alias or args.include or args.source_version:
                    raise CliFailure("E_COMMAND_SYNTAX", "--theme-assets is a self-contained source; do not combine it with Iconify inputs", exit_code=2)
                result = import_theme_assets(Path(args.theme_assets), Path(args.output))
            else:
                if not args.source or not args.license_spdx or not args.notice_file:
                    raise CliFailure("E_COMMAND_SYNTAX", "Iconify import requires SOURCE, --license-spdx, and --notice-file", exit_code=2)
                result = import_iconify(Path(args.source), Path(args.output), set_name=args.icon_set, aliases=tuple(args.alias),
                                        license_spdx=args.license_spdx, notice_path=Path(args.notice_file),
                                        include_path=Path(args.include) if args.include else None,
                                        source_version=args.source_version)
        else:
            result = copy_material_symbols_outline_rounded_catalog(Path(args.output))
        print(json.dumps(result, sort_keys=True))
        return
    if args.command in OPERATIONS:
        try:
            command = parse_command(Path(args.command_path).read_text(encoding="utf-8"))
            reader = _store_reader(args)
        except OSError as error:
            raise CliFailure("E_AUTOMATION_RESULT_IO", str(error), "automation", exit_code=3) from error
        result = run_store_command(args.command, command, reader)
        _write_result(Path(args.result), result)
        if result["status"] != "accepted":
            raise SystemExit(2)
        return
    if args.command == "baseline-compare":
        try:
            reader = _store_reader(args)
            baseline_reference = load_reference(args.baseline_reference)
            candidate_reference = load_reference(args.candidate_reference)
        except OSError as error:
            raise CliFailure("E_AUTOMATION_RESULT_IO", str(error), "automation", exit_code=3) from error
        result = compare_store_baseline(reader, baseline_reference, candidate_reference)
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
    if args.command == "compile":
        _run_compile(args)
        return
    if args.command == "init":
        _run_init(args)
        return
    if args.command == "skill":
        copy_skill(Path(args.output))
        return
    if args.command == "mcp":
        _run_mcp(args)
        return
    if args.command == "preset":
        if args.preset_command == "list":
            _run_preset_list(args)
        else:
            _run_preset_copy(args)
        return
    if args.command == "render":
        if _is_plan_path(args.project):
            _run_draft_render_of_plan(args)
        else:
            _run_draft_render(args)
        return
    if args.command == "render-workspace":
        _run_guided_draft_render(args)
        return
    if args.command == "workspace":
        _run_workspace_revision(args)
        return
    if args.command == "identity":
        _run_identity(args)
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
        reader = LocalSnapshotReader(Path(args.snapshot_root), args.store_identity, require_content_identity=not args.allow_missing_content_identity)
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
        validation = validate_project_mapping(project)
        if not validation.ok:
            _reject(_with_source_ranges(args, validation.diagnostics))
        print("[]")
        return
    outcome = schedule_project_mapping(project)
    if not outcome.ok:
        _reject(_with_source_ranges(args, outcome.diagnostics))
    print(json.dumps(outcome.payload(), indent=2, default=_json_default))


def _write_result(destination: Path, result: dict[str, Any]) -> None:
    """Create one result artifact without replacing an existing result."""
    from chrona.storage.publication import publish_exclusive
    if destination.exists():
        raise CliFailure("E_AUTOMATION_OUTPUT_EXISTS", "result destination already exists", "automation", exit_code=2)
    try:
        publish_exclusive(destination, json.dumps(result, sort_keys=True, default=_json_default).encode("utf-8"))
    except FileExistsError as error:
        raise CliFailure("E_AUTOMATION_OUTPUT_EXISTS", "result destination already exists", "automation", exit_code=2) from error
    except OSError as error:
        raise CliFailure("E_AUTOMATION_RESULT_IO", str(error), "automation", exit_code=3) from error


def main() -> None:
    global _PLAN_SOURCE
    _PLAN_SOURCE = None
    try:
        args = _parser().parse_args()
        _run(args)
    except Exception as error:
        _emit_report(report_failure(error))
