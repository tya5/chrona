"""Closed, renderer-neutral normalization for catalog icon bytes."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import math
import re
from xml.etree import ElementTree


class IconNormalizationError(ValueError):
    def __init__(self, diagnostic_id: str, detail: str | None = None):
        super().__init__(detail or diagnostic_id)
        self.diagnostic_id = diagnostic_id


def _shown(value: object) -> str:
    """Render only a bounded scalar operand in a diagnostic."""
    if isinstance(value, (list, tuple)):
        items = [repr(item) if isinstance(item, (str, int, float, bool, type(None))) else f"<{type(item).__name__}>" for item in value[:8]]
        text = "[" + ", ".join(items) + (", ..." if len(value) > 8 else "") + "]"
    elif isinstance(value, (str, int, float, bool, type(None))):
        text = repr(value)
    else:
        text = f"<{type(value).__name__}>"
    return text if len(text) <= 96 else text[:93] + "..."


def _shown_keys(value: dict[object, object]) -> str:
    """Summarize untrusted mapping keys without dumping a whole declaration."""
    keys = sorted(_shown(key) for key in value)
    return f"count={len(keys)}, sample={_shown(keys[:8])}"


def _normalization_error(code: str, detail: str) -> IconNormalizationError:
    return IconNormalizationError(code, f"{code}: {detail}")


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
    raise _normalization_error("E_ICON_CATALOG_SCHEMA", f"icon kind {_shown(kind)} must be 'vector' or 'raster'")


def validate_png(payload: bytes, viewport: tuple[int, int]) -> None:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        signature_valid = payload[:8] == b"\x89PNG\r\n\x1a\n"
        ihdr_valid = payload[12:16] == b"IHDR"
        raise _normalization_error(
            "E_ICON_PNG_INVALID",
            f"PNG header requires signature and IHDR; byte_length={len(payload)}, "
            f"signature_valid={signature_valid}, ihdr_valid={ihdr_valid}",
        )
    width, height = int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")
    if not (0 < width <= 4096 and 0 < height <= 4096):
        raise _normalization_error("E_ICON_PNG_LIMIT", f"PNG dimensions {width}x{height} must each be within 1..4096")
    if (width, height) != viewport:
        raise _normalization_error("E_ICON_PNG_INVALID", f"PNG dimensions {width}x{height} do not match viewport {viewport[0]}x{viewport[1]}")


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def normalize_svg(payload: bytes, viewport: tuple[int, int]) -> NormalizedVectorIcon:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        position = getattr(error, "position", None)
        raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG XML at / is malformed at {position}") from error
    if _local(root.tag) != "svg" or any(key not in {"viewBox", "xmlns"} for key in root.attrib):
        unexpected = {key: None for key in root.attrib if key not in {"viewBox", "xmlns"}}
        raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG root must be <svg> with only viewBox/xmlns; tag={_shown(_local(root.tag))}, unexpected_attributes({_shown_keys(unexpected)})")
    viewbox = root.attrib.get("viewBox", "").replace(",", " ").split()
    if len(viewbox) != 4:
        raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG /@viewBox needs four finite coordinates; found {len(viewbox)} tokens")
    try:
        values = tuple(float(value) for value in viewbox)
    except ValueError as error:
        bad = next((token for token in viewbox if not _is_float(token)), "unknown")
        raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG /@viewBox coordinate {_shown(bad)} must be numeric") from error
    if not all(math.isfinite(value) for value in values) or values[:2] != (0.0, 0.0) or values[2:] != tuple(map(float, viewport)):
        raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG /@viewBox must be 0 0 {viewport[0]} {viewport[1]}; found {_shown(' '.join(viewbox))}")
    paths: list[NormalizedIconPath] = []
    def visit(node: ElementTree.Element, depth: int = 0) -> None:
        tag = _local(node.tag)
        if depth > 8 or tag not in {"svg", "g", "path"}:
            raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG element /{tag} is unsupported or exceeds maximum nesting depth 8")
        permitted = {"d"} if _local(node.tag) == "path" else ({"viewBox", "xmlns"} if _local(node.tag) == "svg" else set())
        unexpected = sorted(key for key in node.attrib if key not in permitted)
        if unexpected:
            raise _normalization_error("E_ICON_SVG_UNSAFE", f"SVG /{_shown(tag)}/@{_shown(unexpected[0])} is not permitted; attributes allowed here are {sorted(permitted)}")
        if _local(node.tag) == "path":
            paths.append(NormalizedIconPath(parse_path_commands(node.attrib.get("d", ""), source_ref="/svg/path/@d")))
        for child in node:
            visit(child, depth + 1)
    visit(root)
    if not paths or len(paths) > 128 or sum(len(path.commands) for path in paths) > 2048:
        raise _normalization_error("E_ICON_SVG_LIMIT", f"SVG needs 1..128 paths and at most 2048 commands; paths={len(paths)}, commands={sum(len(path.commands) for path in paths)}")
    return NormalizedVectorIcon(viewport, tuple(paths))


_ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_PATH_ARITY = {"move": 2, "line": 2, "quadratic": 4, "close": 0}
_MAX_PATTERN_SIDE = 256
_MAX_PATTERN_PRIMITIVES = 64
_MAX_GLYPH_PARTS = 32
_MAX_PATH_LENGTH = 65_536
_ARC_TOLERANCE = 0.001


def _finite_number(value: object, *, minimum: float | None = None,
                   maximum: float | None = None, positive: bool = False,
                   field: str = "value") -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise _normalization_error("E_THEME_ASSET_SOURCE_VALUE", f"{field} must be a finite number; got {_shown(value)} ({type(value).__name__})")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum) or (maximum is not None and result > maximum) or (positive and result <= 0):
        lower = "> 0" if positive else f">= {minimum}" if minimum is not None else "finite"
        upper = f" and <= {maximum}" if maximum is not None else ""
        raise _normalization_error("E_THEME_ASSET_SOURCE_LIMIT", f"{field}={_shown(value)} must be finite and {lower}{upper}")
    return result


def _number_text(value: float) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return format(value, ".12g")


def _path_string(commands: list[dict[str, object]]) -> str:
    tokens = {"move": "M", "line": "L", "quadratic": "Q", "close": "Z"}
    output: list[str] = []
    for command in commands:
        kind = str(command["kind"])
        output.append(tokens[kind])
        output.extend(_number_text(float(value)) for value in command.get("points", ()))
    return " ".join(output)


def normalize_glyph_entry(value: object) -> dict[str, object]:
    """Validate one declarative glyph and emit the closed #464 path form."""
    if not isinstance(value, dict) or set(value) != {"viewport", "parts"}:
        raise _normalization_error("E_THEME_ASSET_SOURCE_GLYPH", f"/entry requires object fields viewport, parts; found {_shown(value)}")
    viewport = value["viewport"]
    if not isinstance(viewport, dict) or set(viewport) != {"inlineSize", "blockSize"}:
        raise _normalization_error("E_THEME_ASSET_SOURCE_GLYPH", f"/entry/viewport requires inlineSize and blockSize; found {_shown(viewport)}")
    width, height = viewport["inlineSize"], viewport["blockSize"]
    if (not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 4096
            or not isinstance(height, int) or isinstance(height, bool) or not 1 <= height <= 4096):
        raise _normalization_error("E_THEME_ASSET_SOURCE_LIMIT", f"/entry/viewport dimensions must be integers in 1..4096; inlineSize={_shown(width)}, blockSize={_shown(height)}")
    parts = value["parts"]
    if not isinstance(parts, list) or not 1 <= len(parts) <= _MAX_GLYPH_PARTS:
        raise _normalization_error("E_THEME_ASSET_SOURCE_LIMIT", f"/entry/parts count must be 1..{_MAX_GLYPH_PARTS}; found {len(parts) if isinstance(parts, list) else type(parts).__name__}")
    normalized: list[dict[str, object]] = []
    for part_index, part in enumerate(parts):
        pointer = f"/entry/parts/{part_index}"
        if not isinstance(part, dict) or set(part) - {"paint", "d", "strokeWidth", "lineCap", "lineJoin"}:
            found = f"fields({_shown_keys(part)})" if isinstance(part, dict) else _shown(part)
            raise _normalization_error("E_THEME_ASSET_SOURCE_GLYPH", f"{pointer} has unsupported fields or is not an object; found {found}")
        paint, data = part.get("paint"), part.get("d")
        if paint not in {"fill", "stroke"} or not isinstance(data, str) or not data or len(data) > _MAX_PATH_LENGTH:
            raise _normalization_error("E_THEME_ASSET_SOURCE_GLYPH", f"{pointer} requires paint fill/stroke and nonempty d up to {_MAX_PATH_LENGTH} chars; paint={_shown(paint)}, d_type={type(data).__name__}, d_length={len(data) if isinstance(data, str) else 'n/a'}")
        try:
            parsed = parse_path_commands(data, source_ref=f"{pointer}/d")
        except IconNormalizationError as error:
            raise _normalization_error("E_THEME_ASSET_SOURCE_PATH", f"{pointer}/d is invalid: {error}") from error
        if any(command.kind not in _PATH_ARITY for command in parsed):
            raise _normalization_error("E_THEME_ASSET_SOURCE_PATH", f"{pointer}/d contains unsupported command; expected move, line, quadratic, close")
        commands: list[dict[str, object]] = []
        for command in parsed:
            coordinates = [number for point in command.points for number in point]
            points = tuple(_finite_number(number, minimum=0, maximum=width if index % 2 == 0 else height, field=f"{pointer}/d coordinate[{index}]")
                           for index, number in enumerate(coordinates))
            commands.append({"kind": command.kind, "points": list(points)})
        if not commands or commands[0]["kind"] != "move":
            raise _normalization_error("E_THEME_ASSET_SOURCE_PATH", f"{pointer}/d must begin with a move command; found {commands[0]['kind'] if commands else 'no commands'}")
        item: dict[str, object] = {"paint": paint, "data": _path_string(commands)}
        if paint == "stroke":
            item["strokeWidth"] = _finite_number(part.get("strokeWidth"), positive=True, maximum=1024, field=f"{pointer}/strokeWidth")
            if part.get("lineCap") not in {"butt", "round", "square"} or part.get("lineJoin") not in {"miter", "round", "bevel"}:
                raise _normalization_error("E_THEME_ASSET_SOURCE_GLYPH", f"{pointer} stroke lineCap must be butt/round/square and lineJoin miter/round/bevel; found {_shown(part.get('lineCap'))}, {_shown(part.get('lineJoin'))}")
            item["lineCap"], item["lineJoin"] = part["lineCap"], part["lineJoin"]
        elif set(part) != {"paint", "d"}:
            raise _normalization_error("E_THEME_ASSET_SOURCE_GLYPH", f"{pointer} fill paint permits only paint and d; found fields({_shown_keys(part)})")
        normalized.append(item)
    return {"viewport": {"inlineSize": width, "blockSize": height}, "parts": normalized}


def _arc_commands(cx: float, cy: float, radius: float, start: float, end: float) -> list[dict[str, object]]:
    """Approximate a circular arc with quadratics at ≤0.001 tile-unit error."""
    def canonical_coordinate(value: float) -> float:
        # libm may differ in the last binary ULP across supported platforms.
        # Quantize generated coordinates before both density and wire output.
        return float(_number_text(value))

    span = math.radians(end - start)
    # For a circular arc, quadratic control at r/cos(delta/2) gives radial
    # error bounded by r*(sec(delta/2)-1). Pick the largest safe subdivision.
    half = min(math.pi / 2, math.acos(radius / (radius + _ARC_TOLERANCE)))
    segments = max(1, math.ceil(abs(span) / (2 * half)))
    step = span / segments
    commands: list[dict[str, object]] = []
    first = math.radians(start)
    commands.append({"kind": "move", "points": [canonical_coordinate(cx + radius * math.cos(first)),
                                                 canonical_coordinate(cy + radius * math.sin(first))]})
    for index in range(segments):
        a0, a1 = first + index * step, first + (index + 1) * step
        middle = (a0 + a1) / 2
        control_radius = radius / math.cos(step / 2)
        commands.append({"kind": "quadratic", "points": [canonical_coordinate(cx + control_radius * math.cos(middle)),
                                                      canonical_coordinate(cy + control_radius * math.sin(middle)),
                                                      canonical_coordinate(cx + radius * math.cos(a1)),
                                                      canonical_coordinate(cy + radius * math.sin(a1))]})
    return commands


def _primitive_contains(primitive: dict[str, object], x: float, y: float) -> bool:
    kind = primitive["kind"]
    if kind == "circle":
        return math.hypot(x - float(primitive["cx"]), y - float(primitive["cy"])) <= float(primitive["radius"])
    if kind == "rect":
        return (float(primitive["x"]) <= x < float(primitive["x"]) + float(primitive["inlineSize"])
                and float(primitive["y"]) <= y < float(primitive["y"]) + float(primitive["blockSize"]))
    if kind == "path":
        points: list[tuple[float, float]] = primitive.get("_densityPoints", [])
        if not points:
            points = _flatten_path(primitive["commands"])
        if primitive["paint"] == "fill":
            if len(points) < 3:
                return False
            inside = False
            previous = points[-1]
            for current in points:
                x0, y0 = previous; x1, y1 = current
                if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
                    inside = not inside
                previous = current
            return inside
        limit = float(primitive["strokeWidth"]) / 2
        return _segment_tree_contains(primitive["_segmentTree"], x, y)


def _circle_stroke_contains(primitive: dict[str, object], x: float, y: float) -> bool:
    width = float(primitive.get("strokeWidth", 0))
    if width <= 0:
        return False
    distance = math.hypot(x - float(primitive["cx"]), y - float(primitive["cy"]))
    radius = float(primitive["radius"])
    return max(0.0, radius - width / 2) <= distance <= radius + width / 2


def _flatten_path(commands: list[dict[str, object]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    current = start = None
    for command in commands:
        command_kind = command["kind"]
        values = command["points"]
        if command_kind == "move":
            current = start = (float(values[0]), float(values[1]))
            points.append(current)
        elif command_kind == "line":
            current = (float(values[0]), float(values[1]))
            points.append(current)
        elif command_kind == "quadratic" and current is not None:
            control = (float(values[0]), float(values[1]))
            end = (float(values[2]), float(values[3]))
            p0 = current
            for step in range(1, 17):
                t = step / 16
                inverse = 1 - t
                points.append((inverse * inverse * p0[0] + 2 * inverse * t * control[0] + t * t * end[0],
                               inverse * inverse * p0[1] + 2 * inverse * t * control[1] + t * t * end[1]))
            current = end
        elif command_kind == "close" and current is not None and start is not None:
            points.append(start)
            current = start
    return points


def _distance_to_segment(x: float, y: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    denominator = dx * dx + dy * dy
    amount = 0 if denominator == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / denominator))
    return math.hypot(x - (a[0] + amount * dx), y - (a[1] + amount * dy))


def _build_segment_tree(points: list[tuple[float, float]], half_width: float) -> tuple[object, ...]:
    """Build a deterministic BVH over the exact 16-chord stroke predicate."""
    records = [(min(a[0], b[0]) - half_width, min(a[1], b[1]) - half_width,
                max(a[0], b[0]) + half_width, max(a[1], b[1]) + half_width,
                a[0], a[1], b[0], b[1], half_width) for a, b in zip(points, points[1:])]

    def build(items: list[tuple[float, ...]]) -> tuple[object, ...]:
        bounds = (min(item[0] for item in items), min(item[1] for item in items),
                  max(item[2] for item in items), max(item[3] for item in items))
        if len(items) <= 8:
            return (bounds, tuple(items))
        axis = 0 if bounds[2] - bounds[0] >= bounds[3] - bounds[1] else 1
        items.sort(key=lambda item: (item[axis] + item[axis + 2]) / 2)
        middle = len(items) // 2
        return (bounds, build(items[:middle]), build(items[middle:]))

    return build(records)


def _segment_tree_contains(node: tuple[object, ...], x: float, y: float) -> bool:
    """Query a BVH without changing the inclusive segment-distance rule."""
    bounds = node[0]
    if x < bounds[0] or x > bounds[2] or y < bounds[1] or y > bounds[3]:
        return False
    if len(node) == 2:
        for item in node[1]:
            if item[0] <= x <= item[2] and item[1] <= y <= item[3]:
                if _distance_to_segment(x, y, (item[4], item[5]), (item[6], item[7])) <= item[8]:
                    return True
        return False
    return (_segment_tree_contains(node[1], x, y)
            or _segment_tree_contains(node[2], x, y))


def normalize_pattern_entry(value: object) -> dict[str, object]:
    """Normalize a bounded repeat tile and derive its sampled density."""
    if not isinstance(value, dict) or set(value) != {"tile", "angle", "densityBasisPoints", "primitives"}:
        raise _normalization_error("E_THEME_ASSET_SOURCE_PATTERN", f"/entry requires tile, angle, densityBasisPoints, primitives; found {_shown(value)}")
    tile = value["tile"]
    if not isinstance(tile, dict) or set(tile) != {"inlineSize", "blockSize"}:
        raise _normalization_error("E_THEME_ASSET_SOURCE_PATTERN", f"/entry/tile requires inlineSize and blockSize; found {_shown(tile)}")
    width = _finite_number(tile["inlineSize"], minimum=1, maximum=_MAX_PATTERN_SIDE, field="/entry/tile/inlineSize")
    height = _finite_number(tile["blockSize"], minimum=1, maximum=_MAX_PATTERN_SIDE, field="/entry/tile/blockSize")
    angle = _finite_number(value["angle"], minimum=0, maximum=359.999999999, field="/entry/angle")
    primitives = value["primitives"]
    if not isinstance(primitives, list) or not 1 <= len(primitives) <= _MAX_PATTERN_PRIMITIVES:
        raise _normalization_error("E_THEME_ASSET_SOURCE_LIMIT", f"/entry/primitives count must be 1..{_MAX_PATTERN_PRIMITIVES}; found {len(primitives) if isinstance(primitives, list) else type(primitives).__name__}")
    normalized: list[dict[str, object]] = []
    for primitive_index, primitive in enumerate(primitives):
        pointer = f"/entry/primitives/{primitive_index}"
        if not isinstance(primitive, dict):
            raise _normalization_error("E_THEME_ASSET_SOURCE_PATTERN", f"{pointer} must be an object; found {_shown(primitive)}")
        kind = primitive.get("kind")
        item: dict[str, object]
        if kind == "circle" and set(primitive) <= {"kind", "cx", "cy", "radius", "fillChannel", "strokeWidth"} and {"kind", "cx", "cy", "radius"} <= set(primitive):
            cx = _finite_number(primitive["cx"], minimum=0, maximum=width, field=f"{pointer}/cx")
            cy = _finite_number(primitive["cy"], minimum=0, maximum=height, field=f"{pointer}/cy")
            radius = _finite_number(primitive["radius"], positive=True, maximum=128, field=f"{pointer}/radius")
            item = {"kind": "circle", "cx": cx, "cy": cy, "radius": radius}
            fill_channel = primitive.get("fillChannel", "ink")
            if not isinstance(fill_channel, str) or fill_channel not in {"ink", "substrate", "none"}:
                raise _normalization_error(
                    "E_THEME_ASSET_SOURCE_PATTERN",
                    f"{pointer}/fillChannel must be 'ink', 'substrate', or 'none'; found {_shown(fill_channel)}",
                )
            if "fillChannel" in primitive:
                item["fillChannel"] = fill_channel
            if "strokeWidth" in primitive:
                item["strokeWidth"] = _finite_number(primitive["strokeWidth"], positive=True, maximum=16, field=f"{pointer}/strokeWidth")
            if fill_channel == "none" and "strokeWidth" not in primitive:
                raise _normalization_error(
                    "E_THEME_ASSET_SOURCE_PATTERN",
                    f"{pointer}/strokeWidth is required and must be positive when fillChannel='none'",
                )
        elif kind == "rect" and set(primitive) == {"kind", "x", "y", "inlineSize", "blockSize"}:
            x = _finite_number(primitive["x"], minimum=0, maximum=width, field=f"{pointer}/x")
            y = _finite_number(primitive["y"], minimum=0, maximum=height, field=f"{pointer}/y")
            inline = _finite_number(primitive["inlineSize"], positive=True, maximum=width, field=f"{pointer}/inlineSize")
            block = _finite_number(primitive["blockSize"], positive=True, maximum=height, field=f"{pointer}/blockSize")
            if x + inline > width or y + block > height:
                raise _normalization_error("E_THEME_ASSET_SOURCE_LIMIT", f"{pointer} rectangle extent x+inlineSize={x + inline}, y+blockSize={y + block} exceeds tile {width}x{height}")
            item = {"kind": "rect", "x": x, "y": y, "inlineSize": inline, "blockSize": block}
        elif kind == "line" and set(primitive) == {"kind", "x1", "y1", "x2", "y2", "strokeWidth"}:
            x1 = _finite_number(primitive["x1"], minimum=0, maximum=width, field=f"{pointer}/x1")
            y1 = _finite_number(primitive["y1"], minimum=0, maximum=height, field=f"{pointer}/y1")
            x2 = _finite_number(primitive["x2"], minimum=0, maximum=width, field=f"{pointer}/x2")
            y2 = _finite_number(primitive["y2"], minimum=0, maximum=height, field=f"{pointer}/y2")
            stroke = _finite_number(primitive["strokeWidth"], positive=True, maximum=16, field=f"{pointer}/strokeWidth")
            item = {"kind": "path", "paint": "stroke", "strokeWidth": stroke, "lineCap": "round", "lineJoin": "round", "commands": [{"kind": "move", "points": [x1, y1]}, {"kind": "line", "points": [x2, y2]}]}
        elif kind == "arc" and set(primitive) == {"kind", "cx", "cy", "radius", "startAngle", "endAngle", "strokeWidth"}:
            cx = _finite_number(primitive["cx"], minimum=0, maximum=width, field=f"{pointer}/cx")
            cy = _finite_number(primitive["cy"], minimum=0, maximum=height, field=f"{pointer}/cy")
            radius = _finite_number(primitive["radius"], positive=True, maximum=256, field=f"{pointer}/radius")
            start = _finite_number(primitive["startAngle"], minimum=0, maximum=359.999999999, field=f"{pointer}/startAngle")
            end = _finite_number(primitive["endAngle"], minimum=0, maximum=360, field=f"{pointer}/endAngle")
            stroke = _finite_number(primitive["strokeWidth"], positive=True, maximum=16, field=f"{pointer}/strokeWidth")
            if end <= start or end - start > 360:
                raise _normalization_error("E_THEME_ASSET_SOURCE_PATTERN", f"{pointer}/endAngle={end} must exceed startAngle={start} by at most 360 degrees")
            commands = _arc_commands(cx, cy, radius, start, end)
            if any(not 0 <= point[axis] <= (width if axis == 0 else height)
                   for command in commands for point in (command["points"][i:i + 2]
                                                         for i in range(0, len(command["points"]), 2))
                   for axis in (0, 1)):
                raise _normalization_error("E_THEME_ASSET_SOURCE_LIMIT", f"{pointer} arc geometry leaves tile bounds {width}x{height}")
            item = {"kind": "path", "paint": "stroke", "strokeWidth": stroke, "lineCap": "round", "lineJoin": "round", "commands": commands}
        else:
            raise _normalization_error("E_THEME_ASSET_SOURCE_PATTERN", f"{pointer} has unsupported primitive kind/fields; kind={_shown(kind)}, fields({_shown_keys(primitive)})")
        normalized.append(item)
    density_primitives: list[dict[str, object]] = []
    for primitive in normalized:
        sample = dict(primitive)
        if sample.get("kind") == "path":
            sample["_densityPoints"] = _flatten_path(sample["commands"])
            if sample["paint"] == "stroke":
                sample["_segmentTree"] = _build_segment_tree(sample["_densityPoints"], float(sample["strokeWidth"]) / 2)
        density_primitives.append(sample)
    covered = 0
    cells = 128 * 128
    for row in range(128):
        for column in range(128):
            px = ((column + 0.5) / 128) * width
            py = ((row + 0.5) / 128) * height
            # Density is intrinsic to the tile-local fundamental cell.
            # Rotation transforms sample and geometry together, so its value
            # is exactly the unrotated local-grid coverage for every angle.
            x, y = px, py
            # The finite tile clips each primitive before repetition. Evaluate
            # source primitives in authored painter order so substrate fills
            # erase earlier ink and later strokes/paths can paint over them.
            ink = False
            for primitive in density_primitives:
                kind = primitive["kind"]
                if kind == "circle":
                    if _primitive_contains(primitive, x, y):
                        channel = primitive.get("fillChannel", "ink")
                        if channel == "ink":
                            ink = True
                        elif channel == "substrate":
                            ink = False
                    if _circle_stroke_contains(primitive, x, y):
                        ink = True
                elif _primitive_contains(primitive, x, y):
                    ink = True
            if ink:
                covered += 1
    density = int((Decimal(covered * 10_000) / Decimal(cells)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if not 1 <= density <= 10_000:
        raise _normalization_error("E_THEME_ASSET_SOURCE_DENSITY", f"derived density={density} basis points must be within 1..10000")
    declared = value["densityBasisPoints"]
    if not isinstance(declared, int) or isinstance(declared, bool) or not 1 <= declared <= 10_000:
        raise _normalization_error("E_THEME_ASSET_SOURCE_DENSITY", f"/entry/densityBasisPoints={_shown(declared)} must be an integer in 1..10000; derived={density}")
    if declared != density:
        raise _normalization_error("E_THEME_ASSET_SOURCE_DENSITY", f"/entry/densityBasisPoints={declared} does not match derived density={density}")
    return {"tile": {"inlineSize": width, "blockSize": height}, "angle": angle,
            "densityBasisPoints": density, "primitives": normalized}


def _local(tag: str) -> str: return tag.rsplit("}", 1)[-1]


def parse_path_commands(value: str, *, source_ref: str = "/path/@d") -> tuple[IconPathCommand, ...]:
    """Tokenize one SVG path `d` string into normalized absolute commands.

    Shared by the icon normalizer and the Theme glyph symbol geometry
    (`scene/mark_geometry.py`), so there is exactly one SVG path-data grammar
    in the codebase.
    """
    tokens = [command or number for command, number in _TOKEN.findall(value)]
    if not tokens or "".join(tokens) != re.sub(r"[\s,]+", "", value):
        unsupported = re.search(r"[^MmLlHhVvQqCcZz0-9eE+.,\-\s]", value)
        operand = f"unexpected character={_shown(unsupported.group(0))} at offset={unsupported.start()}" if unsupported else "token sequence is incomplete"
        raise _normalization_error("E_ICON_SVG_UNSAFE", f"{source_ref} length={len(value)} does not match supported path grammar; {operand}")
    output: list[IconPathCommand] = []; index = 0; command = ""; current = (0.0, 0.0); start = current
    while index < len(tokens):
        if tokens[index].isalpha(): command = tokens[index]; index += 1
        if not command: raise _normalization_error("E_ICON_SVG_UNSAFE", f"{source_ref} token[{index}] has no active command")
        upper, relative = command.upper(), command.islower()
        if upper not in _ARITY: raise _normalization_error("E_ICON_SVG_UNSAFE", f"{source_ref} command={command!r} is unsupported; expected M/L/H/V/Q/C/Z")
        if upper == "Z": output.append(IconPathCommand("close")); current = start; command = ""; continue
        first = True
        while index < len(tokens) and not tokens[index].isalpha():
            count = _ARITY[upper]
            if index + count > len(tokens): raise _normalization_error("E_ICON_SVG_UNSAFE", f"{source_ref} command={command!r} needs {count} operands; remaining={len(tokens) - index}")
            try: numbers = [float(token) for token in tokens[index:index + count]]
            except ValueError as error: raise _normalization_error("E_ICON_SVG_UNSAFE", f"{source_ref} command={command!r} has a nonnumeric operand") from error
            index += count
            if not all(math.isfinite(number) and abs(number) <= 4096 for number in numbers): raise _normalization_error("E_ICON_SVG_LIMIT", f"{source_ref} command={command!r} operands must be finite with absolute value <=4096; found {_shown(numbers)}")
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
    if not output or output[0].kind != "move": raise _normalization_error("E_ICON_SVG_UNSAFE", f"{source_ref} must begin with a move command; found {output[0].kind if output else 'no commands'}")
    return tuple(output)
