"""Render the generic Controller Z fixture through the v0.2 presentation path.

This is a verification harness, not a renderer or a preset implementation.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import argparse
import os
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chrona.presentation.presentation_settings import builtin_bases
from chrona.presentation.review_svg import build_review_projection, render_table_timeline_svg
from chrona.scheduling.scheduler import schedule


def load(name: str):
    return yaml.safe_load((ROOT / "examples" / "controller-z" / name).read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    project = load("project.yaml")
    actual = load("actual.yaml")
    view = load("shared/view.yaml")
    style = load("shared/style.yaml")
    theme = load("shared/theme.yaml")
    profile = load("shared/layout.yaml")
    result = schedule(project)
    assert result.ok
    settings = deepcopy(builtin_bases()["executive-v0.2"])
    if args.settings:
        settings = yaml.safe_load(args.settings.read_text())
    projection = build_review_projection(project, result.placements, view, actual, style, theme)
    capabilities = {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}
    first = render_table_timeline_svg(project["project"]["title"], projection, project, view, theme, capabilities, profile, settings=settings)
    second = render_table_timeline_svg(project["project"]["title"], projection, project, view, theme, capabilities, profile, settings=settings)
    assert first == second, "E_PRESENTATION_NONDETERMINISTIC"
    output = args.output or ROOT / "examples/controller-z/variants/executive/alternatives/executive-v2.svg"
    output.write_text(first, encoding="utf-8")
    png = output.with_suffix(".png")
    sharp_root = os.environ.get('CODEX_PRIMARY_RUNTIME_NODE_MODULES', os.environ.get('NODE_PATH', ''))
    raster = "const sharp=require('sharp'); sharp(process.argv[1]).png().toFile(process.argv[2]).catch(e=>{console.error(e);process.exit(1)});"
    subprocess.run(["node", "-e", raster, str(output), str(png)], check=True, env={**__import__("os").environ, "NODE_PATH": sharp_root})
    print(output)
    print(png)


if __name__ == "__main__":
    main()
