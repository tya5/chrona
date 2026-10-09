"""Deterministic local Iconify JSON ingestion; no network or render dependency."""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
import os
from pathlib import Path
import tempfile
from typing import Any
from xml.etree import ElementTree

from importlib.resources import files

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.svgLib.path import parse_path

from chrona.presentation.icons.normalizer import IconNormalizationError, normalize_glyph_entry, normalize_pattern_entry
from chrona.resources import safe_load, schema_validator


class IconImportError(ValueError):
    def __init__(self, code: str, icon: str | None = None, source_ref: str = "/", detail: str | None = None):
        self.code, self.icon, self.source_ref, self._detail = code, icon, source_ref, detail
        super().__init__(self.detail)

    @property
    def detail(self) -> str:
        identity = f" icon={self.icon}" if self.icon else ""
        suffix = f" detail={self._detail}" if self._detail else ""
        return f"{self.code}{identity} source={self.source_ref}{suffix}"


def _shown(value: object) -> str:
    """Show a bounded scalar operand without serializing source documents."""
    if isinstance(value, (list, tuple)):
        items = [repr(item) if isinstance(item, (str, int, float, bool, type(None))) else f"<{type(item).__name__}>" for item in value[:8]]
        text = "[" + ", ".join(items) + (", ..." if len(value) > 8 else "") + "]"
    elif isinstance(value, (str, int, float, bool, type(None))):
        text = repr(value)
    else:
        text = f"<{type(value).__name__}>"
    return text if len(text) <= 96 else text[:93] + "..."


def _shown_keys(value: dict[object, object]) -> str:
    """Summarize untrusted mapping keys without dumping a whole document."""
    keys = sorted(_shown(key) for key in value)
    return f"count={len(keys)}, sample={_shown(keys[:8])}"


_THEME_ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _write_catalog(destination: Path, catalog: dict[str, object]) -> str:
    encoded = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(encoded); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return "sha256:" + sha256(encoded).hexdigest()


def import_theme_assets(source: Path, destination: Path) -> dict[str, object]:
    """Import a closed declarative glyph/pattern source as a v0.5 catalogue."""
    try:
        source_bytes = source.read_bytes()
        if not source_bytes or len(source_bytes) > 4_000_000:
            raise IconImportError("E_THEME_ASSET_SOURCE_LIMIT", source_ref=str(source), detail=f"source byte length={len(source_bytes)} must be 1..4000000")
        document = safe_load(source_bytes)
    except OSError as error:
        raise IconImportError("E_THEME_ASSET_SOURCE_IO", source_ref=str(source), detail=f"read failed: {type(error).__name__}") from error
    except Exception as error:
        if isinstance(error, IconImportError):
            raise
        raise IconImportError("E_THEME_ASSET_SOURCE_YAML", source_ref=str(source), detail=f"YAML parse failed: {type(error).__name__}") from error
    if not isinstance(document, dict) or set(document) != {"version", "kind", "id", "body"}:
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref="/", detail=f"expected root object fields id, kind, version, body; found {type(document).__name__} with keys({_shown_keys(document) if isinstance(document, dict) else 'n/a'})")
    if document["version"] != "chrona/theme-asset-source/v0.2" or document["kind"] != "theme-asset-source":
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref="/version", detail=f"expected version chrona/theme-asset-source/v0.2 and kind theme-asset-source; got version={_shown(document['version'])}, kind={_shown(document['kind'])}")
    if not isinstance(document["id"], str) or not _THEME_ASSET_NAME.fullmatch(document["id"]):
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref="/id", detail=f"id must match {_THEME_ASSET_NAME.pattern}; got {_shown(document['id'])}")
    validation = tuple(schema_validator("theme-asset-source-v0.2.schema.yaml").iter_errors(document))
    if validation:
        error = min(validation, key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message))
        pointer = "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in error.absolute_path)
        expected = {
            "type": f"type {error.validator_value!r}",
            "enum": f"one of {_shown(error.validator_value)}",
            "required": f"required field(s) {_shown(error.validator_value)}",
            "additionalProperties": "no additional fields",
        }.get(str(error.validator), f"constraint {error.validator!r}")
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref=pointer, detail=f"schema constraint {expected} failed for {type(error.instance).__name__} value {_shown(error.instance)}")
    body = document["body"]
    expected = {"set", "aliases", "license", "glyphs", "patterns"}
    if not isinstance(body, dict) or set(body) != expected:
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref="/body", detail=f"expected fields={sorted(expected)}; found keys({_shown_keys(body) if isinstance(body, dict) else type(body).__name__})")
    set_name, aliases = body["set"], body["aliases"]
    if not isinstance(set_name, str) or not _THEME_ASSET_NAME.fullmatch(set_name):
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref="/body/set", detail=f"set must match {_THEME_ASSET_NAME.pattern}; got {_shown(set_name)}")
    if not isinstance(aliases, list) or any(not isinstance(alias, str) or not _THEME_ASSET_NAME.fullmatch(alias) for alias in aliases):
        invalid_alias = next((alias for alias in aliases if not isinstance(alias, str) or not _THEME_ASSET_NAME.fullmatch(alias)), None) if isinstance(aliases, list) else aliases
        raise IconImportError("E_THEME_ASSET_SOURCE_ALIAS", source_ref="/body/aliases", detail=f"aliases must be names matching {_THEME_ASSET_NAME.pattern}; invalid={_shown(invalid_alias)}")
    if len(set(aliases)) != len(aliases) or set_name in aliases:
        raise IconImportError("E_THEME_ASSET_SOURCE_ALIAS", source_ref="/body/aliases", detail=f"aliases must be unique and exclude set name {_shown(set_name)}; aliases={_shown(aliases)}")
    license_value = body["license"]
    if (not isinstance(license_value, dict) or set(license_value) != {"spdx", "notice"}
            or not isinstance(license_value.get("spdx"), str) or not license_value["spdx"].strip()
            or not isinstance(license_value.get("notice"), str) or not license_value["notice"].strip()):
        notice = license_value.get("notice") if isinstance(license_value, dict) else None
        raise IconImportError("E_THEME_ASSET_SOURCE_LICENSE", source_ref="/body/license", detail=f"license requires nonempty spdx and notice strings; spdx={_shown(license_value.get('spdx') if isinstance(license_value, dict) else None)}, notice_type={type(notice).__name__}, notice_nonblank={bool(notice.strip()) if isinstance(notice, str) else False}")
    glyphs, patterns = body["glyphs"], body["patterns"]
    if not isinstance(glyphs, dict) or not isinstance(patterns, dict) or not glyphs and not patterns:
        raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref="/body", detail=f"glyphs and patterns must be objects and at least one nonempty; glyphs={type(glyphs).__name__}, patterns={type(patterns).__name__}")
    names: set[str] = set()
    def normalize_entries(entries: object, normalizer: Any, pointer: str) -> dict[str, object]:
        if not isinstance(entries, dict):
            raise IconImportError("E_THEME_ASSET_SOURCE_SCHEMA", source_ref=pointer, detail=f"expected entry object; found {type(entries).__name__}")
        output: dict[str, object] = {}
        for name, entry in sorted(entries.items()):
            entry_pointer = f"{pointer}/{name}"
            if not isinstance(name, str) or not _THEME_ASSET_NAME.fullmatch(name) or name in names:
                raise IconImportError("E_THEME_ASSET_SOURCE_NAME", source_ref=entry_pointer, detail=f"entry name must match {_THEME_ASSET_NAME.pattern} and be unique; got {_shown(name)}")
            names.add(name)
            try:
                output[name] = normalizer(entry)
            except IconNormalizationError as error:
                raise IconImportError(error.diagnostic_id, source_ref=entry_pointer, detail=str(error)) from error
        return output
    normalized_glyphs = normalize_entries(glyphs, normalize_glyph_entry, "/body/glyphs")
    normalized_patterns = normalize_entries(patterns, normalize_pattern_entry, "/body/patterns")
    catalog: dict[str, object] = {
        "version": "chrona/icon-catalog/v0.5", "kind": "icon-catalog", "id": document["id"],
        "body": {
            "set": set_name, "aliases": sorted(aliases),
            "provenance": {
                "sourceKind": "theme-asset-source",
                "sourceContentIdentity": "sha256:" + sha256(source_bytes).hexdigest(),
                "license": {"spdx": license_value["spdx"], "notice": license_value["notice"]},
            },
            "icons": {}, "entryAliases": {},
            "glyphs": normalized_glyphs, "patterns": normalized_patterns,
        },
    }
    identity = _write_catalog(destination, catalog)
    return {"set": set_name, "glyphs": len(normalized_glyphs), "patterns": len(normalized_patterns),
            "license": license_value["spdx"], "contentIdentity": identity}


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
    def __init__(self, icon: str = "<icon>", source_ref: str = "/") -> None:
        self.commands: list[dict[str, object]] = []
        self.icon, self.source_ref = icon, source_ref
    def moveTo(self, p: tuple[float, float]) -> None: self.commands.append({"kind": "move", "points": list(p)})
    def lineTo(self, p: tuple[float, float]) -> None: self.commands.append({"kind": "line", "points": list(p)})
    def qCurveTo(self, *p: tuple[float, float] | None) -> None:
        if len(p) < 2 or p[-1] is None: raise IconImportError("E_ICON_IMPORT_PATH", self.icon, self.source_ref, f"quadratic path needs a control and endpoint; operands={len(p)}")
        # cu2qu can return a chain of off-curves; consecutive pairs retain a
        # bounded quadratic representation without exposing cubic commands.
        for control, end in zip(p[:-1], p[1:]):
            if control is None or end is None: raise IconImportError("E_ICON_IMPORT_PATH", self.icon, self.source_ref, "quadratic control and endpoint must be coordinate pairs")
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
    except ElementTree.ParseError as error:
        raise IconImportError("E_ICON_IMPORT_XML", icon, "/body", f"malformed SVG fragment at {getattr(error, 'position', None)}") from error
    result: list[dict[str, object]] = []
    def visit(node: ElementTree.Element, inherited: dict[str, str]) -> None:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag not in {"svg", "g", "path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}: raise IconImportError("E_ICON_IMPORT_ELEMENT", icon, f"/{tag}", f"element is unsupported; expected svg/g/path/line/polyline/polygon/rect/circle/ellipse, got {tag!r}")
        unsafe = next((key for key in node.attrib if key in {"style", "class", "transform", "opacity"} or key.startswith("on")), None)
        if unsafe is not None: raise IconImportError("E_ICON_IMPORT_UNSAFE", icon, f"/{tag}/@{unsafe}", f"attribute {unsafe!r} is forbidden")
        paint = dict(inherited); paint.update({key: value for key, value in node.attrib.items() if key in {"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"}})
        if tag not in {"svg", "g"}:
            pointer = f"/{tag}/@d" if tag == "path" else f"/{tag}"
            try:
                data = _shape_path(tag, node.attrib, icon=icon, source_ref=f"/{tag}")
            except IconImportError:
                raise
            if not isinstance(data, str): raise IconImportError("E_ICON_IMPORT_PATH", icon, pointer, f"shape conversion must produce path text; got {type(data).__name__}")
            pen = _Pen(icon, pointer)
            try: parse_path(data, Cu2QuPen(pen, max_err=0.25, reverse_direction=False))
            except IconImportError: raise
            except Exception as error: raise IconImportError("E_ICON_IMPORT_PATH", icon, pointer, f"path parser rejected shape ({type(error).__name__})") from error
            for mode in ("fill", "stroke"):
                value = paint.get(mode, "currentColor" if mode == "fill" else "none")
                if value not in {"none", "currentColor"}: raise IconImportError("E_ICON_IMPORT_PAINT", icon, f"/{tag}/@{mode}", f"paint value {_shown(value)} must be none or currentColor")
                if value == "currentColor":
                    item: dict[str, object] = {"paint": mode, "commands": pen.commands}
                    if mode == "stroke": item.update({"strokeWidth": float(paint.get("stroke-width", "1")), "lineCap": paint.get("stroke-linecap", "butt"), "lineJoin": paint.get("stroke-linejoin", "miter")})
                    result.append(item)
        for child in node: visit(child, paint)
    visit(root, {})
    if not result: raise IconImportError("E_ICON_IMPORT_PAINT", icon, "/body", "no visible currentColor fill or stroke was produced")
    current_width, current_height = width, height
    for transform in transforms:
        declared_width, declared_height = transform.get("width", current_width), transform.get("height", current_height)
        if (not isinstance(declared_width, int) or not isinstance(declared_height, int)
                or not (0 < declared_width <= 4096 and 0 < declared_height <= 4096)):
            raise IconImportError("E_ICON_IMPORT_VIEWPORT", icon, "/metadata", f"width={_shown(declared_width)}, height={_shown(declared_height)} must be integers in 1..4096")
        current_width, current_height = declared_width, declared_height
        rotate = transform.get("rotate", 0)
        if not isinstance(rotate, int) or rotate not in {0, 1, 2, 3}:
            raise IconImportError("E_ICON_IMPORT_TRANSFORM", icon, "/metadata/rotate", f"rotate={_shown(rotate)} must be integer quarter-turn count 0..3")
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
            raise IconImportError("E_ICON_IMPORT_VIEWPORT", icon, "/metadata", f"width={_shown(width)}, height={_shown(height)} must be integers in 1..4096")
        rotate = transform.get("rotate", 0)
        if not isinstance(rotate, int) or rotate not in {0, 1, 2, 3}:
            raise IconImportError("E_ICON_IMPORT_TRANSFORM", icon, "/metadata/rotate", f"rotate={_shown(rotate)} must be integer quarter-turn count 0..3")
        if rotate % 2:
            width, height = height, width
    return width, height


def _shape_path(tag: str, values: dict[str, str], *, icon: str = "<icon>", source_ref: str = "/") -> str:
    if tag == "path": return values.get("d", "")
    def n(name: str, default: str = "0") -> float:
        raw = values.get(name, default)
        try:
            result = float(raw)
        except (TypeError, ValueError) as error:
            raise IconImportError("E_ICON_IMPORT_PATH", icon, f"{source_ref}/@{name}", f"expected numeric shape attribute, got {_shown(raw)}") from error
        if not math.isfinite(result):
            raise IconImportError("E_ICON_IMPORT_PATH", icon, f"{source_ref}/@{name}", f"expected finite shape attribute, got {_shown(raw)}")
        return result
    if tag == "line": return f"M{n('x1')} {n('y1')}L{n('x2')} {n('y2')}"
    if tag in {"polyline", "polygon"}:
        points = values.get("points", "").replace(",", " ").split()
        if len(points) < 4 or len(points) % 2: raise IconImportError("E_ICON_IMPORT_PATH", icon, f"{source_ref}/@points", f"expected at least two coordinate pairs; found {len(points)} tokens")
        data = "M" + " ".join(points[:2]) + "L" + " ".join(points[2:])
        return data + ("Z" if tag == "polygon" else "")
    if tag == "rect":
        x, y, w, h = n("x"), n("y"), n("width"), n("height")
        if w <= 0 or h <= 0: raise IconImportError("E_ICON_IMPORT_PATH", icon, source_ref, f"rect width={w}, height={h} must be positive")
        return f"M{x} {y}H{x+w}V{y+h}H{x}Z"
    if tag in {"circle", "ellipse"}:
        cx, cy = n("cx"), n("cy"); rx = n("r") if tag == "circle" else n("rx"); ry = n("r") if tag == "circle" else n("ry")
        if rx <= 0 or ry <= 0: raise IconImportError("E_ICON_IMPORT_PATH", icon, source_ref, f"ellipse radii rx={rx}, ry={ry} must be positive")
        return f"M{cx-rx} {cy}A{rx} {ry} 0 1 0 {cx+rx} {cy}A{rx} {ry} 0 1 0 {cx-rx} {cy}Z"
    raise IconImportError("E_ICON_IMPORT_ELEMENT", icon, source_ref, f"unsupported shape element {tag!r}")


def import_iconify(source: Path, destination: Path, *, set_name: str | None = None,
                   aliases: tuple[str, ...] = (), license_spdx: str | None = None,
                   notice_path: Path | None = None, include_path: Path | None = None,
                   source_version: str | None = None) -> dict[str, object]:
    try:
        source_bytes = source.read_bytes()
        collection = json.loads(source_bytes)
    except OSError as error: raise IconImportError("E_ICON_IMPORT_IO", source_ref=str(source), detail=f"read failed: {type(error).__name__}") from error
    except json.JSONDecodeError as error: raise IconImportError("E_ICON_IMPORT_JSON", source_ref=str(source), detail=f"malformed JSON at line={error.lineno}, column={error.colno}") from error
    if not isinstance(collection, dict):
        raise IconImportError("E_ICON_IMPORT_COLLECTION", source_ref="/", detail=f"collection root must be an object; got {type(collection).__name__}")
    prefix, entries = collection.get("prefix"), collection.get("icons")
    if not isinstance(prefix, str) or not isinstance(entries, dict): raise IconImportError("E_ICON_IMPORT_COLLECTION", source_ref="/", detail=f"prefix must be string and icons object; prefix={_shown(prefix)}, icons={type(entries).__name__}")
    if not license_spdx or notice_path is None: raise IconImportError("E_ICON_IMPORT_LICENSE", source_ref="/provenance/license", detail=f"nonempty SPDX and notice path required; spdx={_shown(license_spdx)}, notice_path={notice_path is not None}")
    try: notice = notice_path.read_text(encoding="utf-8").strip()
    except OSError as error: raise IconImportError("E_ICON_IMPORT_LICENSE", source_ref=str(notice_path), detail=f"notice read failed: {type(error).__name__}") from error
    if not notice: raise IconImportError("E_ICON_IMPORT_LICENSE", source_ref=str(notice_path), detail="notice file is empty")
    selected: set[str] | None = None
    if include_path is not None:
        try:
            selected = {line.strip() for line in include_path.read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.lstrip().startswith("#")}
        except OSError as error:
            raise IconImportError("E_ICON_IMPORT_INCLUDE", source_ref=str(include_path), detail=f"include list read failed: {type(error).__name__}") from error
        if not selected or any(name not in entries for name in selected):
            unknown = sorted(name for name in selected if name not in entries)
            raise IconImportError("E_ICON_IMPORT_INCLUDE", source_ref=str(include_path), detail=f"include names must be nonempty collection members; missing={unknown[:8]}")
    normalized: dict[str, object] = {}; entry_aliases: dict[str, str] = {}
    for name, entry in sorted(entries.items()):
        if selected is not None and name not in selected:
            continue
        if not isinstance(name, str) or not isinstance(entry, dict) or not isinstance(entry.get("body"), str): raise IconImportError("E_ICON_IMPORT_ENTRY", str(name), f"/icons/{name}", f"entry requires object with string body; got {type(entry).__name__}, body={type(entry.get('body')).__name__ if isinstance(entry, dict) else 'n/a'}")
        width, height = entry.get("width", collection.get("width", 24)), entry.get("height", collection.get("height", 24))
        if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096): raise IconImportError("E_ICON_IMPORT_VIEWPORT", f"{prefix}:{name}", f"/icons/{name}/width|height", f"width={_shown(width)}, height={_shown(height)} must be integers in 1..4096")
        identity = f"{prefix}:{name}"
        output_width, output_height = _transformed_dimensions(width, height, (entry,), identity)
        normalized[name] = {"kind": "vector", "viewport": {"inlineSize": output_width, "blockSize": output_height}, "alternative": str(entry.get("title", name.replace("-", " "))), "paths": _compact_paths(_paths(entry["body"], identity, width, height, (entry,)))}
    raw_aliases = collection.get("aliases", {})
    if not isinstance(raw_aliases, dict): raise IconImportError("E_ICON_IMPORT_ALIAS", source_ref="/aliases", detail=f"aliases must be an object; got {type(raw_aliases).__name__}")
    def resolve_alias(alias: str) -> tuple[str, tuple[dict[str, object], ...]]:
        chain: list[dict[str, object]] = []
        current = alias
        seen: set[str] = set()
        while current in raw_aliases:
            if current in seen:
                raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", f"/aliases/{alias}/parent", "alias cycle detected")
            seen.add(current)
            value = raw_aliases[current]
            if not isinstance(value, dict) or not isinstance(value.get("parent"), str):
                raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", f"/aliases/{alias}/parent", f"parent must be a string; got {_shown(value.get('parent'))}")
            chain.append(value)
            current = value["parent"]
        if current not in entries:
            raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", f"/aliases/{alias}/parent", f"parent {_shown(current)} does not name an icon or alias")
        return current, tuple(reversed(chain))

    for alias in sorted(raw_aliases):
        if not isinstance(alias, str):
            raise IconImportError("E_ICON_IMPORT_ALIAS", str(alias), "/aliases", f"alias key must be a string; got {type(alias).__name__}")
        canonical, chain = resolve_alias(alias)
        if selected is not None and canonical not in selected:
            continue
        if not any(any(key in value for key in ("hFlip", "vFlip", "rotate", "width", "height")) for value in chain):
            entry_aliases[alias] = canonical
            continue
        parent = entries[canonical]
        if not isinstance(parent, dict) or not isinstance(parent.get("body"), str):
            raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", f"/aliases/{alias}/parent", "resolved alias parent requires an object with string body")
        width, height = parent.get("width", collection.get("width", 24)), parent.get("height", collection.get("height", 24))
        if not isinstance(width, int) or not isinstance(height, int) or not (0 < width <= 4096 and 0 < height <= 4096):
            raise IconImportError("E_ICON_IMPORT_ALIAS", f"{prefix}:{alias}", f"/aliases/{alias}/width|height", f"width={_shown(width)}, height={_shown(height)} must be integers in 1..4096")
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
