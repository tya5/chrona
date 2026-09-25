#!/usr/bin/env python3
"""A stdlib-only example consumer of published chrona/scene/v0.6 JSON.

This is deliberately outside ``src/chrona``: it proves that an adapter can
consume the inspection boundary without importing Project, View, Theme, Layout,
or Chrona's renderer implementation.  It is not a production renderer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape


SUPPORTED_CAPABILITIES = frozenset()


def _paint(value: dict) -> str:
    paint = value.get("paint") or {}
    parts = [f'fill="{escape(str(paint.get("fill") or "none"))}"']
    if paint.get("stroke") is not None:
        parts.append(f'stroke="{escape(str(paint["stroke"]))}"')
    if paint.get("strokeWidth") is not None:
        parts.append(f'stroke-width="{paint["strokeWidth"]}"')
    if paint.get("opacity") is not None:
        parts.append(f'opacity="{paint["opacity"]}"')
    return " ".join(parts)


def _path(commands: list[dict], points: list[list[float]]) -> str:
    if commands:
        output: list[str] = []
        letters = {"move": "M", "line": "L", "quadratic": "Q", "cubic": "C", "close": "Z"}
        for command in commands:
            letter = letters[command["kind"]]
            values = " ".join(f"{x} {y}" for x, y in command["points"])
            output.append(letter + values)
        return "".join(output)
    return "".join(("M" if index == 0 else "L") + f"{point[0]} {point[1]}"
                   for index, point in enumerate(points))


def render(document: dict) -> str:
    if document.get("version") != "chrona/scene/v0.6" or document.get("kind") != "scene":
        raise ValueError("E_SCENE_VERSION")
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError("E_SCENE_CANVAS")
    canvas = surfaces[0].get("canvasBounds")
    if (not isinstance(canvas, dict)
            or not all(isinstance(canvas.get(key), (int, float)) for key in ("inline", "block", "inlineSize", "blockSize"))
            or canvas["inlineSize"] <= 0 or canvas["blockSize"] <= 0):
        raise ValueError("E_SCENE_CANVAS")
    if any(surface.get("canvasBounds") != canvas for surface in surfaces):
        raise ValueError("E_SCENE_CANVAS")
    inline, block, width, height = (canvas[key] for key in ("inline", "block", "inlineSize", "blockSize"))
    output = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{inline} {block} {width} {height}">']
    for surface in surfaces:
        canvas = surface.get("canvasPaint")
        if canvas is not None:
            output.append(f'<rect x="{inline}" y="{block}" width="{width}" height="{height}" {_paint({"paint": canvas})}/>')
        for primitive in surface["primitives"]:
            bounds = primitive["bounds"]
            kind = primitive["kind"]
            if kind == "Rect":
                output.append(f'<rect x="{bounds["inline"]}" y="{bounds["block"]}" width="{bounds["inlineSize"]}" height="{bounds["blockSize"]}" {_paint(primitive)}/>')
            elif kind == "Text":
                baseline = primitive.get("baseline", [bounds["inline"], bounds["block"]])
                layout = primitive.get("textLayout", {})
                output.append(f'<text x="{baseline[0]}" y="{baseline[1]}" font-family="{escape(str(layout.get("family", "sans-serif")))}" font-size="{layout.get("fontSize", 12)}" {_paint(primitive)}>{escape(primitive.get("text", ""))}</text>')
            elif kind in {"Path", "Symbol"}:
                commands = primitive.get("pathCommands") or (primitive.get("symbol") or {}).get("outline", [])
                output.append(f'<path d="{_path(commands, primitive.get("points", []))}" {_paint(primitive)}/>')
    output.append("</svg>")
    return "".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    document = json.loads(Path(args.scene).read_text(encoding="utf-8"))
    required = set(document.get("requiredCapabilities", ()))
    missing = sorted(required - SUPPORTED_CAPABILITIES)
    if missing:
        print(json.dumps({"code": "E_SCENE_CAPABILITY_UNSUPPORTED", "missingCapabilities": missing}, sort_keys=True))
        raise SystemExit(1)
    destination = Path(args.output)
    if destination.exists():
        print(json.dumps({"code": "E_SCENE_OUTPUT_EXISTS"}, sort_keys=True))
        raise SystemExit(2)
    destination.write_text(render(document), encoding="utf-8")


if __name__ == "__main__":
    main()
