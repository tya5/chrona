from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from chrona.presentation.renderers.generic import render_svg
from chrona.presentation.scene.schedule import scene_from_schedule
from chrona.app.review import review_projects
from chrona.commands.commands import set_typed_field
from chrona.scheduling.scheduler import schedule
from chrona.core.validation import load_yaml, validate_project
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.review.surface_content import _surface_content_input
from chrona.presentation.review.svg import (
    append_review_summary,
    render_review_svg,
    render_table_timeline_svg,
)
from chrona.presentation.layout.solver import resolve_layout_profile, solve_layout
from chrona.storage.loader import load_project
from chrona.presentation.model.settings import resolve_presentation_settings
from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def _add_snapshot_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("project", nargs="?", help="raw Draft Project path")
    command.add_argument("--snapshot-reference", help="immutable Project resource-reference YAML")
    command.add_argument("--snapshot-root", help="local snapshot adapter root")
    command.add_argument("--store-identity", help="expected local snapshot store identity")


def _load_primary_project(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    snapshot_values = (args.snapshot_reference, args.snapshot_root, args.store_identity)
    if any(snapshot_values):
        if not all(snapshot_values) or args.project:
            parser.error("snapshot mode requires --snapshot-reference, --snapshot-root, and --store-identity without a raw project")
        reference = load_yaml(args.snapshot_reference)
        return load_project(reference, LocalSnapshotReader(Path(args.snapshot_root), args.store_identity))
    if not args.project:
        parser.error("a raw project or complete snapshot mode is required")
    return load_yaml(args.project)


def main() -> None:
    parser = argparse.ArgumentParser(prog="chrona")
    sub = parser.add_subparsers(dest="command", required=True)
    help_text = {
        "validate": "validate a raw Draft or immutable Project snapshot",
        "schedule": "derive a Date-only schedule from a raw Draft or immutable snapshot",
        "render": "render the minimal timeline through v0.2 settings or the diagnostic legacy adapter",
        "render-review": "render a Plan/Actual review surface",
        "review": "compare two raw Project files",
        "propose-set": "propose one typed Project field change without writing the input",
    }
    for name in help_text:
        command = sub.add_parser(name, help=help_text[name], description=help_text[name])
        if name in {"validate", "schedule", "render"}:
            _add_snapshot_arguments(command)
        else:
            command.add_argument("project")
        if name == "review":
            command.add_argument("candidate")
        if name == "propose-set":
            command.add_argument("object_id")
            command.add_argument("field")
            command.add_argument("value")
        if name == "render":
            command.add_argument("--output", "-o", required=True)
            command.add_argument("--presentation-settings", help="resolved settings or preset for the common v0.2 Scene path")
        if name == "render-review":
            command.add_argument("--actual", required=True); command.add_argument("--view", required=True); command.add_argument("--style", required=True); command.add_argument("--theme", required=True); command.add_argument("--profile", required=True); command.add_argument("--presentation-settings"); command.add_argument("--summary-profile"); command.add_argument("--detail-profile"); command.add_argument("--output", "-o", required=True)
    args = parser.parse_args()
    try:
        project = (_load_primary_project(args, parser)
                   if args.command in {"validate", "schedule", "render"}
                   else load_yaml(args.project))
    except SnapshotReadError as error:
        print(json.dumps({"diagnostics": [{"id": error.diagnostic_id, "path": "/project"}]}))
        raise SystemExit(1) from error
    if args.command == "review":
        print(json.dumps(review_projects(project, load_yaml(args.candidate)), indent=2, default=_json_default))
        return
    if args.command == "propose-set":
        if project.get("extensions"):
            print(json.dumps({"status": "rejected", "diagnostics": ["E_PACKAGE_RESOLUTION_REQUIRED"]}))
            raise SystemExit(1)
        result = set_typed_field(project, None, args.object_id, args.field, json.loads(args.value))
        print(json.dumps({"status": result.status, "diagnostics": result.diagnostics, "project": result.project}, default=_json_default))
        raise SystemExit(result.status != "accepted")
    if args.command == "validate":
        diagnostics = validate_project(project)
        print(json.dumps([item.as_dict() for item in diagnostics], indent=2))
        raise SystemExit(bool(diagnostics))
    result = schedule(project)
    if args.command == "render":
        if not result.ok:
            print(json.dumps({"diagnostics": [item.as_dict() for item in result.diagnostics]}, indent=2))
            raise SystemExit(1)
        scene = scene_from_schedule(project, result)
        settings = resolve_presentation_settings(load_yaml(args.presentation_settings)) if args.presentation_settings else None
        Path(args.output).write_text(render_svg(scene, {"marker", "metadata", "text-alternative"}, settings), encoding="utf-8")
        return
    if args.command == "render-review":
        if not result.ok:
            raise SystemExit(1)
        view,theme,profile=load_yaml(args.view),load_yaml(args.theme),load_yaml(args.profile)
        projection=build_review_projection(project,result.placements,view,load_yaml(args.actual),load_yaml(args.style),theme)
        settings = resolve_presentation_settings(load_yaml(args.presentation_settings)) if args.presentation_settings else None
        summary_profile = load_yaml(args.summary_profile) if args.summary_profile else None
        detail_profile = load_yaml(args.detail_profile) if args.detail_profile else None
        surface_content = (_surface_content_input(projection, project, view, settings, summary_profile,
                                                  projection.window[0], detail_profile) if settings else None)
        if detail_profile and settings is None:
            raise ValueError("E_PRESENTATION_SETTINGS_REQUIRED")
        layout_slots=None
        if profile.get("version")=="chrona/layout-profile/v0.1":
            manifest=resolve_layout_profile(profile,{"title","table","timeline","summary","legend"})
            if manifest.diagnostics: raise ValueError(",".join(manifest.diagnostics))
            layout_slots=solve_layout(profile,manifest)
            svg=render_table_timeline_svg(project["project"].get("title","Chrona"),projection,project,view,theme,{"sourceMetadata","accessibleText","semanticRoles","marker","tableSemantics","hierarchicalAxis"},profile,layout_slots,settings,surface_content)
        elif profile.get("version")=="chrona/table-timeline-profile/v0.1": raise ValueError("E_LAYOUT_PROFILE_REQUIRED")
        else: svg=render_review_svg(project["project"].get("title","Chrona"),projection,theme,{"sourceMetadata","accessibleText","semanticRoles","marker"},profile,settings,surface_content)
        if summary_profile and settings is None:
            svg=append_review_summary(svg,projection,summary_profile,projection.window[0],layout_slots.get("summary") if layout_slots else None,settings)
        Path(args.output).write_text(svg,encoding="utf-8")
        return
    print(json.dumps({"placements": result.placements, "diagnostics": [item.as_dict() for item in result.diagnostics]}, indent=2, default=_json_default))
    raise SystemExit(not result.ok)
