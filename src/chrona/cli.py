from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .render import render_svg
from .scene import scene_from_schedule
from .review import review_projects
from .commands import set_typed_field
from .scheduler import schedule
from .validation import load_yaml, validate_project
from .review_svg import build_review_projection, render_review_svg


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="chrona")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "schedule", "render", "render-review", "review", "propose-set"):
        command = sub.add_parser(name)
        command.add_argument("project")
        if name == "review":
            command.add_argument("candidate")
        if name == "propose-set":
            command.add_argument("object_id")
            command.add_argument("field")
            command.add_argument("value")
        if name == "render":
            command.add_argument("--output", "-o", required=True)
        if name == "render-review":
            command.add_argument("--actual", required=True); command.add_argument("--view", required=True); command.add_argument("--style", required=True); command.add_argument("--theme", required=True); command.add_argument("--profile", required=True); command.add_argument("--output", "-o", required=True)
    args = parser.parse_args()
    project = load_yaml(args.project)
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
        Path(args.output).write_text(render_svg(scene, {"marker", "metadata", "text-alternative"}), encoding="utf-8")
        return
    if args.command == "render-review":
        if not result.ok:
            raise SystemExit(1)
        projection=build_review_projection(project,result.placements,load_yaml(args.view),load_yaml(args.actual),load_yaml(args.style),load_yaml(args.theme))
        Path(args.output).write_text(render_review_svg(project["project"].get("title","Chrona"),projection,load_yaml(args.theme),{"sourceMetadata","accessibleText","semanticRoles","marker"},load_yaml(args.profile)),encoding="utf-8")
        return
    print(json.dumps({"placements": result.placements, "diagnostics": [item.as_dict() for item in result.diagnostics]}, indent=2, default=_json_default))
    raise SystemExit(not result.ok)
