"""Explicit unbounded table policy for warning-envelope tests, not defaults."""
from pathlib import Path

import yaml

from chrona.resources import safe_load
from chrona.usecases.preset_library import copy_builtin_preset


def copy_warning_preset(destination: Path) -> Path:
    preset = copy_builtin_preset("chrona-default-draft", destination)
    layout_path = destination / "layout.yaml"
    layout = safe_load(layout_path.read_bytes())

    def visit(node):
        node.pop("maxInlineShare", None)
        for child in node.get("children", ()):
            visit(child)

    visit(layout["root"])
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    view_path = destination / "view.yaml"
    view = safe_load(view_path.read_bytes())
    body = view["body"]
    for column in body.get("tableColumns", ()):
        column.pop("text", None)
    body.get("rows", {}).get("laneTable", {}).pop("text", None)
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    return preset
