"""Deterministic local Iconify JSON ingestion; no network or render dependency."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from xml.etree import ElementTree

from importlib.resources import files

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.svgLib.path import parse_path


class IconImportError(ValueError):
    def __init__(self, code: str, icon: str | None = None, source_ref: str = "/"):
        super().__init__(code)
        self.code, self.icon, self.source_ref = code, icon, source_ref

    @property
    def detail(self) -> str:
        identity = f" icon={self.icon}" if self.icon else ""
        return f"{self.code}{identity} source={self.source_ref}"


def material_symbols_outline_rounded_catalog() -> bytes:
    """Return the package-owned, normalized default catalog without discovery."""
    return files("chrona.resources").joinpath(
        "icons", "material-symbols-outline-rounded-v2026-09-22.yaml"
    ).read_bytes()


def copy_material_symbols_outline_rounded_catalog(destination: Path) -> dict[str, object]:
    """Write one explicit Draft-ready copy of the packaged default atomically."""
    payload = material_symbols_outline_rounded_catalog()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"set": "material", "aliases": ["material-symbols"],
            "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


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


def _compact_paths(paths: list[dict[str, object]]) -> list[dict[str, object]]:
    """Serialize importer-owned primitives into the v0.3 compact grammar."""
    result: list[dict[str, object]] = []
    tokens = {"move": "M", "line": "L", "quadratic": "Q", "close": "Z"}
    def number(value: object) -> str:
        numeric = float(value)
        if abs(numeric) < 1e-9:
            numeric = 0.0
        return format(numeric, ".9f").rstrip("0").rstrip(".") or "0"
    for path in paths:
        stream: list[str] = []
        for command in path["commands"]:
            stream.append(tokens[str(command["kind"])])
            stream.extend(number(point) for point in command.get("points", ()))
        item = {key: value for key, value in path.items() if key != "commands"}
        item["data"] = " ".join(stream)
        result.append(item)
    return result


def _paths(body: str, icon: str, width: int = 24, height: int = 24,
           transforms: tuple[dict[str, object], ...] = ()) -> list[dict[str, object]]:
    """Parse Iconify's monochrome path body; arcs/cubics become quadratics."""
    try: root = ElementTree.fromstring(f"<svg>{body}</svg>")
    except ElementTree.ParseError as error: raise IconImportError("E_ICON_IMPORT_XML", icon) from error
    result: list[dict[str, object]] = []
    def visit(node: ElementTree.Element, inherited: dict[str, str]) -> None:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag not in {"svg", "g", "path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}: raise IconImportError("E_ICON_IMPORT_ELEMENT", icon, f"/{tag}")
        unsafe = next((key for key in node.attrib if key in {"style", "class", "transform", "opacity"} or key.startswith("on")), None)
        if unsafe is not None: raise IconImportError("E_ICON_IMPORT_UNSAFE", icon, f"/{tag}/@{unsafe}")
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
                if value not in {"none", "currentColor"}: raise IconImportError("E_ICON_IMPORT_PAINT", icon, f"/{tag}/@{mode}")
                if value == "currentColor":
                    item: dict[str, object] = {"paint": mode, "commands": pen.commands}
                    if mode == "stroke": item.update({"strokeWidth": float(paint.get("stroke-width", "1")), "lineCap": paint.get("stroke-linecap", "butt"), "lineJoin": paint.get("stroke-linejoin", "miter")})
                    result.append(item)
        for child in node: visit(child, paint)
    visit(root, {})
    if not result: raise IconImportError("E_ICON_IMPORT_PAINT", icon)
    current_width, current_height = width, height
    for transform in transforms:
        declared_width, declared_height = transform.get("width", current_width), transform.get("height", current_height)
        if (not isinstance(declared_width, int) or not isinstance(declared_height, int)
                or not (0 < declared_width <= 4096 and 0 < declared_height <= 4096)):
            raise IconImportError("E_ICON_IMPORT_VIEWPORT", icon, "/metadata")
        current_width, current_height = declared_width, declared_height
        rotate = transform.get("rotate", 0)
        if not isinstance(rotate, int) or rotate not in {0, 1, 2, 3}:
            raise IconImportError("E_ICON_IMPORT_TRANSFORM", icon, "/metadata/rotate")
        horizontal, vertical = bool(transform.get("hFlip", False)), bool(transform.get("vFlip", False))
        def point(x: float, y: float) -> tuple[float, float]:
            if horizontal: x = current_width - x
            if vertical: y = current_height - y
            local_width, local_height = current_width, current_height
            for _ in range(rotate):
                x, y = local_height - y, x
                local_width, local_height = local_height, local_width
            return x, y
        for path in result:
            for command in path["commands"]:
                values = command.get("points", [])
                command["points"] = [value for index in range(0, len(values), 2) for value in point(float(values[index]), float(values[index + 1]))]
        if rotate % 2:
            current_width, current_height = current_height, current_width
    return result


def _transformed_dimensions(width: int, height: int, transforms: tuple[dict[str, object], ...], icon: str) -> tuple[int, int]:
    for transform in transforms:
        width, height = transform.get("width", width), transform.get("height", height)
        if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096):
            raise IconImportError("E_ICON_IMPORT_VIEWPORT", icon, "/metadata")
        rotate = transform.get("rotate", 0)
        if not isinstance(rotate, int) or rotate not in {0, 1, 2, 3}:
            raise IconImportError("E_ICON_IMPORT_TRANSFORM", icon, "/metadata/rotate")
        if rotate % 2:
            width, height = height, width
    return width, height


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
                   notice_path: Path | None = None, include_path: Path | None = None,
                   source_version: str | None = None) -> dict[str, object]:
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
    selected: set[str] | None = None
    if include_path is not None:
        try:
            selected = {line.strip() for line in include_path.read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.lstrip().startswith("#")}
        except OSError as error:
            raise IconImportError("E_ICON_IMPORT_INCLUDE") from error
        if not selected or any(name not in entries for name in selected):
            raise IconImportError("E_ICON_IMPORT_INCLUDE")
    normalized: dict[str, object] = {}; entry_aliases: dict[str, str] = {}
    for name, entry in sorted(entries.items()):
        if selected is not None and name not in selected:
            continue
        if not isinstance(name, str) or not isinstance(entry, dict) or not isinstance(entry.get("body"), str): raise IconImportError("E_ICON_IMPORT_ENTRY", str(name))
        width, height = entry.get("width", collection.get("width", 24)), entry.get("height", collection.get("height", 24))
        if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096): raise IconImportError("E_ICON_IMPORT_VIEWPORT", name)
        identity = f"{prefix}:{name}"
        output_width, output_height = _transformed_dimensions(width, height, (entry,), identity)
        normalized[name] = {"kind": "vector", "viewport": {"inlineSize": output_width, "blockSize": output_height}, "alternative": str(entry.get("title", name.replace("-", " "))), "paths": _compact_paths(_paths(entry["body"], identity, width, height, (entry,)))}
    raw_aliases = collection.get("aliases", {})
    if not isinstance(raw_aliases, dict): raise IconImportError("E_ICON_IMPORT_ALIAS")
    def resolve_alias(alias: str) -> tuple[str, tuple[dict[str, object], ...]]:
        chain: list[dict[str, object]] = []
        current = alias
        seen: set[str] = set()
        while current in raw_aliases:
            if current in seen:
                raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", "/aliases/parent")
            seen.add(current)
            value = raw_aliases[current]
            if not isinstance(value, dict) or not isinstance(value.get("parent"), str):
                raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", "/aliases/parent")
            chain.append(value)
            current = value["parent"]
        if current not in entries:
            raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", "/aliases/parent")
        return current, tuple(reversed(chain))

    for alias in sorted(raw_aliases):
        if not isinstance(alias, str):
            raise IconImportError("E_ICON_IMPORT_ALIAS", str(alias), "/aliases")
        canonical, chain = resolve_alias(alias)
        if selected is not None and canonical not in selected:
            continue
        if not any(any(key in value for key in ("hFlip", "vFlip", "rotate", "width", "height")) for value in chain):
            entry_aliases[alias] = canonical
            continue
        parent = entries[canonical]
        if not isinstance(parent, dict) or not isinstance(parent.get("body"), str):
            raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", "/aliases/parent")
        width, height = parent.get("width", collection.get("width", 24)), parent.get("height", collection.get("height", 24))
        if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096):
            raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", "/aliases")
        transforms = (parent, *chain)
        identity = f"{prefix}:{alias}"
        output_width, output_height = _transformed_dimensions(width, height, transforms, identity)
        normalized[alias] = {"kind": "vector", "viewport": {"inlineSize": output_width, "blockSize": output_height}, "alternative": str(chain[-1].get("title", parent.get("title", alias.replace("-", " ")))), "paths": _compact_paths(_paths(parent["body"], identity, width, height, transforms))}
    catalog = {"version": "chrona/icon-catalog/v0.3", "kind": "icon-catalog", "id": f"{set_name or prefix}-icons", "body": {"set": set_name or prefix, "aliases": list(aliases), "provenance": {"sourceKind": "iconify-json", "sourcePrefix": prefix, "sourceContentIdentity": "sha256:" + sha256(source_bytes).hexdigest(), "sourceVersion": source_version or str(collection.get("version", "local")), "license": {"spdx": license_spdx, "notice": notice}}, "icons": normalized, "entryAliases": entry_aliases}}
    # JSON is a YAML subset.  Writing the canonical JSON form makes large
    # user-imported catalogs take the same fast decode path as bundled ones.
    encoded = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as out: out.write(encoded); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, destination)
    finally: Path(temporary).unlink(missing_ok=True)
    return {"set": set_name or prefix, "icons": len(normalized), "license": license_spdx, "contentIdentity": "sha256:" + sha256(encoded).hexdigest()}
