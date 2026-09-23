"""Deterministic local Iconify JSON ingestion; no network or render dependency."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from xml.etree import ElementTree

import yaml
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.svgLib.path import parse_path


class IconImportError(ValueError):
    def __init__(self, code: str, icon: str | None = None):
        super().__init__(code)
        self.code, self.icon = code, icon


class _Pen:
    def __init__(self) -> None: self.commands: list[dict[str, object]] = []
    def moveTo(self, p: tuple[float, float]) -> None: self.commands.append({"kind": "move", "points": list(p)})
    def lineTo(self, p: tuple[float, float]) -> None: self.commands.append({"kind": "line", "points": list(p)})
    def qCurveTo(self, *p: tuple[float, float] | None) -> None:
        if len(p) < 2 or p[-1] is None: raise IconImportError("E_ICON_IMPORT_PATH")
        # cu2qu can return a chain of off-curves; consecutive pairs retain a
        # bounded quadratic representation without exposing cubic commands.
        for control, end in zip(p[:-1], p[1:]):
            if control is None or end is None: raise IconImportError("E_ICON_IMPORT_PATH")
            self.commands.append({"kind": "quadratic", "points": [*control, *end]})
    def closePath(self) -> None: self.commands.append({"kind": "close"})
    def endPath(self) -> None: pass


def _paths(body: str, icon: str, width: int = 24, height: int = 24, transform: dict[str, object] | None = None) -> list[dict[str, object]]:
    """Parse Iconify's monochrome path body; arcs/cubics become quadratics."""
    try: root = ElementTree.fromstring(f"<svg>{body}</svg>")
    except ElementTree.ParseError as error: raise IconImportError("E_ICON_IMPORT_XML", icon) from error
    result: list[dict[str, object]] = []
    def visit(node: ElementTree.Element, inherited: dict[str, str]) -> None:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag not in {"svg", "g", "path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}: raise IconImportError("E_ICON_IMPORT_ELEMENT", icon)
        if any(key in {"style", "class", "transform", "opacity"} or key.startswith("on") for key in node.attrib): raise IconImportError("E_ICON_IMPORT_UNSAFE", icon)
        paint = dict(inherited); paint.update({key: value for key, value in node.attrib.items() if key in {"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"}})
        if tag not in {"svg", "g"}:
            data = _shape_path(tag, node.attrib)
            if not isinstance(data, str): raise IconImportError("E_ICON_IMPORT_PATH", icon)
            pen = _Pen()
            try: parse_path(data, Cu2QuPen(pen, max_err=0.25, reverse_direction=False))
            except IconImportError: raise
            except Exception as error: raise IconImportError("E_ICON_IMPORT_PATH", icon) from error
            for mode in ("fill", "stroke"):
                value = paint.get(mode, "currentColor" if mode == "fill" else "none")
                if value not in {"none", "currentColor"}: raise IconImportError("E_ICON_IMPORT_PAINT", icon)
                if value == "currentColor":
                    item: dict[str, object] = {"paint": mode, "commands": pen.commands}
                    if mode == "stroke": item.update({"strokeWidth": float(paint.get("stroke-width", "1")), "lineCap": paint.get("stroke-linecap", "butt"), "lineJoin": paint.get("stroke-linejoin", "miter")})
                    result.append(item)
        for child in node: visit(child, paint)
    visit(root, {})
    if not result: raise IconImportError("E_ICON_IMPORT_PAINT", icon)
    transform = transform or {}
    rotate = transform.get("rotate", 0)
    if not isinstance(rotate, int) or rotate not in {0, 1, 2, 3}: raise IconImportError("E_ICON_IMPORT_TRANSFORM", icon)
    horizontal, vertical = bool(transform.get("hFlip", False)), bool(transform.get("vFlip", False))
    def point(x: float, y: float) -> tuple[float, float]:
        if horizontal: x = width - x
        if vertical: y = height - y
        for _ in range(rotate): x, y = height - y, x
        return x, y
    for path in result:
        for command in path["commands"]:
            values = command.get("points", [])
            command["points"] = [value for index in range(0, len(values), 2) for value in point(float(values[index]), float(values[index + 1]))]
    return result


def _shape_path(tag: str, values: dict[str, str]) -> str:
    if tag == "path": return values.get("d", "")
    def n(name: str, default: str = "0") -> float: return float(values.get(name, default))
    if tag == "line": return f"M{n('x1')} {n('y1')}L{n('x2')} {n('y2')}"
    if tag in {"polyline", "polygon"}:
        points = values.get("points", "").replace(",", " ").split()
        if len(points) < 4 or len(points) % 2: raise IconImportError("E_ICON_IMPORT_PATH")
        data = "M" + " ".join(points[:2]) + "L" + " ".join(points[2:])
        return data + ("Z" if tag == "polygon" else "")
    if tag == "rect":
        x, y, w, h = n("x"), n("y"), n("width"), n("height")
        if w <= 0 or h <= 0: raise IconImportError("E_ICON_IMPORT_PATH")
        return f"M{x} {y}H{x+w}V{y+h}H{x}Z"
    if tag in {"circle", "ellipse"}:
        cx, cy = n("cx"), n("cy"); rx = n("r") if tag == "circle" else n("rx"); ry = n("r") if tag == "circle" else n("ry")
        if rx <= 0 or ry <= 0: raise IconImportError("E_ICON_IMPORT_PATH")
        return f"M{cx-rx} {cy}A{rx} {ry} 0 1 0 {cx+rx} {cy}A{rx} {ry} 0 1 0 {cx-rx} {cy}Z"
    raise IconImportError("E_ICON_IMPORT_ELEMENT")


def import_iconify(source: Path, destination: Path, *, set_name: str | None = None,
                   aliases: tuple[str, ...] = (), license_spdx: str | None = None,
                   notice_path: Path | None = None) -> dict[str, object]:
    try:
        source_bytes = source.read_bytes()
        collection = json.loads(source_bytes)
    except OSError as error: raise IconImportError("E_ICON_IMPORT_IO") from error
    except json.JSONDecodeError as error: raise IconImportError("E_ICON_IMPORT_JSON") from error
    prefix, entries = collection.get("prefix"), collection.get("icons")
    if not isinstance(prefix, str) or not isinstance(entries, dict): raise IconImportError("E_ICON_IMPORT_COLLECTION")
    if not license_spdx or notice_path is None: raise IconImportError("E_ICON_IMPORT_LICENSE")
    try: notice = notice_path.read_text(encoding="utf-8").strip()
    except OSError as error: raise IconImportError("E_ICON_IMPORT_LICENSE") from error
    if not notice: raise IconImportError("E_ICON_IMPORT_LICENSE")
    normalized: dict[str, object] = {}; entry_aliases: dict[str, str] = {}
    for name, entry in sorted(entries.items()):
        if not isinstance(name, str) or not isinstance(entry, dict) or not isinstance(entry.get("body"), str): raise IconImportError("E_ICON_IMPORT_ENTRY", str(name))
        width, height = entry.get("width", collection.get("width", 24)), entry.get("height", collection.get("height", 24))
        if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096): raise IconImportError("E_ICON_IMPORT_VIEWPORT", name)
        rotate = entry.get("rotate", 0)
        output_width, output_height = (height, width) if rotate in {1, 3} else (width, height)
        normalized[name] = {"kind": "vector", "viewport": {"inlineSize": output_width, "blockSize": output_height}, "alternative": str(entry.get("title", name.replace("-", " "))), "paths": _paths(entry["body"], name, width, height, entry)}
    raw_aliases = collection.get("aliases", {})
    if not isinstance(raw_aliases, dict): raise IconImportError("E_ICON_IMPORT_ALIAS")
    for alias, value in sorted(raw_aliases.items()):
        if not isinstance(alias, str) or not isinstance(value, dict) or not isinstance(value.get("parent"), str) or value["parent"] not in normalized: raise IconImportError("E_ICON_IMPORT_ALIAS", str(alias))
        if any(key in value for key in ("hFlip", "vFlip", "rotate", "width", "height")):
            parent = entries[value["parent"]]
            if not isinstance(parent, dict) or not isinstance(parent.get("body"), str): raise IconImportError("E_ICON_IMPORT_ALIAS", alias)
            width, height = value.get("width", parent.get("width", collection.get("width", 24))), value.get("height", parent.get("height", collection.get("height", 24)))
            if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096): raise IconImportError("E_ICON_IMPORT_ALIAS", alias)
            rotate = value.get("rotate", 0); output_width, output_height = (height, width) if rotate in {1, 3} else (width, height)
            normalized[alias] = {"kind": "vector", "viewport": {"inlineSize": output_width, "blockSize": output_height}, "alternative": str(value.get("title", parent.get("title", alias.replace("-", " ")))), "paths": _paths(parent["body"], alias, width, height, value)}
        else: entry_aliases[alias] = value["parent"]
    catalog = {"version": "chrona/icon-catalog/v0.2", "kind": "icon-catalog", "id": f"{set_name or prefix}-icons", "body": {"set": set_name or prefix, "aliases": list(aliases), "provenance": {"sourceKind": "iconify-json", "sourcePrefix": prefix, "sourceContentIdentity": "sha256:" + sha256(source_bytes).hexdigest(), "sourceVersion": str(collection.get("version", "local")), "license": {"spdx": license_spdx, "notice": notice}}, "icons": normalized, "entryAliases": entry_aliases}}
    encoded = yaml.safe_dump(catalog, sort_keys=False).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as out: out.write(encoded); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, destination)
    finally: Path(temporary).unlink(missing_ok=True)
    return {"set": set_name or prefix, "icons": len(normalized), "license": license_spdx, "contentIdentity": "sha256:" + sha256(encoded).hexdigest()}
