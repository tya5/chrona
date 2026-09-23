"""Closed, renderer-neutral normalization for catalog icon bytes."""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from xml.etree import ElementTree


class IconNormalizationError(ValueError):
    def __init__(self, diagnostic_id: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id


@dataclass(frozen=True)
class IconPathCommand:
    kind: str
    points: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class NormalizedIconPath:
    """One normalized icon path with its closed monochrome paint mode."""

    commands: tuple[IconPathCommand, ...]
    paint: str = "fill"
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None


@dataclass(frozen=True)
class NormalizedVectorIcon:
    viewport: tuple[int, int]
    paths: tuple[NormalizedIconPath, ...]


_TOKEN = re.compile(r"([MmLlHhVvQqCcZz])|([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)")
_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "Z": 0}


def normalize_icon(kind: str, payload: bytes, viewport: tuple[int, int]) -> NormalizedVectorIcon | bytes:
    if kind == "vector":
        return normalize_svg(payload, viewport)
    if kind == "raster":
        validate_png(payload, viewport)
        return payload
    raise IconNormalizationError("E_ICON_CATALOG_SCHEMA")


def validate_png(payload: bytes, viewport: tuple[int, int]) -> None:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise IconNormalizationError("E_ICON_PNG_INVALID")
    width, height = int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")
    if not (0 < width <= 4096 and 0 < height <= 4096):
        raise IconNormalizationError("E_ICON_PNG_LIMIT")
    if (width, height) != viewport:
        raise IconNormalizationError("E_ICON_PNG_INVALID")


def normalize_svg(payload: bytes, viewport: tuple[int, int]) -> NormalizedVectorIcon:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise IconNormalizationError("E_ICON_SVG_UNSAFE") from error
    if _local(root.tag) != "svg" or any(key not in {"viewBox", "xmlns"} for key in root.attrib):
        raise IconNormalizationError("E_ICON_SVG_UNSAFE")
    viewbox = root.attrib.get("viewBox", "").replace(",", " ").split()
    if len(viewbox) != 4:
        raise IconNormalizationError("E_ICON_SVG_UNSAFE")
    try:
        values = tuple(float(value) for value in viewbox)
    except ValueError as error:
        raise IconNormalizationError("E_ICON_SVG_UNSAFE") from error
    if not all(math.isfinite(value) for value in values) or values[:2] != (0.0, 0.0) or values[2:] != tuple(map(float, viewport)):
        raise IconNormalizationError("E_ICON_SVG_UNSAFE")
    paths: list[NormalizedIconPath] = []
    def visit(node: ElementTree.Element, depth: int = 0) -> None:
        if depth > 8 or _local(node.tag) not in {"svg", "g", "path"}:
            raise IconNormalizationError("E_ICON_SVG_UNSAFE")
        permitted = {"d"} if _local(node.tag) == "path" else ({"viewBox", "xmlns"} if _local(node.tag) == "svg" else set())
        if any(key not in permitted for key in node.attrib):
            raise IconNormalizationError("E_ICON_SVG_UNSAFE")
        if _local(node.tag) == "path":
            paths.append(NormalizedIconPath(_path(node.attrib.get("d", ""))))
        for child in node:
            visit(child, depth + 1)
    visit(root)
    if not paths or len(paths) > 128 or sum(len(path.commands) for path in paths) > 2048:
        raise IconNormalizationError("E_ICON_SVG_LIMIT")
    return NormalizedVectorIcon(viewport, tuple(paths))


def _local(tag: str) -> str: return tag.rsplit("}", 1)[-1]


def _path(value: str) -> tuple[IconPathCommand, ...]:
    tokens = [command or number for command, number in _TOKEN.findall(value)]
    if not tokens or "".join(tokens) != re.sub(r"[\s,]+", "", value):
        raise IconNormalizationError("E_ICON_SVG_UNSAFE")
    output: list[IconPathCommand] = []; index = 0; command = ""; current = (0.0, 0.0); start = current
    while index < len(tokens):
        if tokens[index].isalpha(): command = tokens[index]; index += 1
        if not command: raise IconNormalizationError("E_ICON_SVG_UNSAFE")
        upper, relative = command.upper(), command.islower()
        if upper not in _ARITY: raise IconNormalizationError("E_ICON_SVG_UNSAFE")
        if upper == "Z": output.append(IconPathCommand("close")); current = start; command = ""; continue
        first = True
        while index < len(tokens) and not tokens[index].isalpha():
            count = _ARITY[upper]
            if index + count > len(tokens): raise IconNormalizationError("E_ICON_SVG_UNSAFE")
            try: numbers = [float(token) for token in tokens[index:index + count]]
            except ValueError as error: raise IconNormalizationError("E_ICON_SVG_UNSAFE") from error
            index += count
            if not all(math.isfinite(number) and abs(number) <= 4096 for number in numbers): raise IconNormalizationError("E_ICON_SVG_LIMIT")
            if upper == "H": point = (numbers[0] + (current[0] if relative else 0), current[1]); kind, points = "line", (point,)
            elif upper == "V": point = (current[0], numbers[0] + (current[1] if relative else 0)); kind, points = "line", (point,)
            else:
                raw = [(numbers[i], numbers[i + 1]) for i in range(0, count, 2)]
                points = tuple((x + current[0], y + current[1]) if relative else (x, y) for x, y in raw)
                kind = {"M": "move", "L": "line", "Q": "quadratic", "C": "cubic"}[upper]
                if upper == "M" and not first: kind = "line"
                point = points[-1]
            output.append(IconPathCommand(kind, points)); current = point
            if upper == "M" and first: start = point
            first = False
    if not output or output[0].kind != "move": raise IconNormalizationError("E_ICON_SVG_UNSAFE")
    return tuple(output)
