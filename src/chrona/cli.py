from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .render import render_svg
from .scene import scene_from_schedule
from .review import review_projects
from .scheduler import schedule
from .validation import load_yaml, validate_project


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="chrona")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "schedule", "render", "review"):
        command = sub.add_parser(name)
        command.add_argument("project")
        if name == "review":
            command.add_argument("candidate")
        if name == "render":
            command.add_argument("--output", "-o", required=True)
    args = parser.parse_args()
    project = load_yaml(args.project)
    if args.command == "review":
        print(json.dumps(review_projects(project, load_yaml(args.candidate)), indent=2, default=_json_default))
        return
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
    print(json.dumps({"placements": result.placements, "diagnostics": [item.as_dict() for item in result.diagnostics]}, indent=2, default=_json_default))
    raise SystemExit(not result.ok)
