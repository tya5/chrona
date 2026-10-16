"""Positioned Typst and TikZ serialization of completed Scene surfaces."""
from __future__ import annotations

from collections.abc import Sequence
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
import re
from typing import Protocol

from chrona.core.ports import RenderArtifact
from chrona.presentation.fonts.installed import _weight_rank
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface
from chrona.presentation.renderers.pattern_repeat import repeat_cells


class FontFile(Protocol):
    """One resolved font file of the render's closure; the adapter only names it, it never measures it."""

    path: Path
    family: str
    weight: int
    index: int


def _error(code: str, detail: str) -> ValueError:
    return ValueError(f"{code}: {detail}")


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


def _primitive_detail(node: ScenePrimitive, expected: str) -> str:
    return f"scene_id={node.scene_id!r}, kind={node.kind!r}, bounds={node.bounds!r}; expected {expected}"


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _typst_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _typst_font(family: str) -> str:
    """Project the completed CSS-style family list as native font alternatives."""
    families = [value.strip().strip("\"'") for value in family.split(",") if value.strip()]
    return "(" + ", ".join(f'"{_typst_string(value)}"' for value in families) + ",)"


def _tex_string(value: str) -> str:
    return (value.replace("\\", r"\textbackslash{}").replace("{", r"\{").replace("}", r"\}")
            .replace("#", r"\#").replace("$", r"\$").replace("%", r"\%").replace("&", r"\&")
            .replace("_", r"\_").replace("^", r"\textasciicircum{}").replace("~", r"\textasciitilde{}"))


def _color(primitive: ScenePrimitive, property_name: str) -> str:
    paint = primitive.paint
    value = getattr(paint, property_name) if paint is not None else None
    if not isinstance(value, str):
        raise _error("E_PRESENTATION_PAINT_INVALID", f"scene_id={primitive.scene_id!r} paint.{property_name} must be a color string; received {_brief(value)}")
    return value


def _opacity(node: ScenePrimitive) -> float:
    value = node.paint.opacity if node.paint is not None else None
    if not 0 <= value <= 1:
        raise _error("E_PRESENTATION_OPACITY_INVALID", f"scene_id={node.scene_id!r} paint.opacity={_brief(value)}; expected a number in [0, 1]")
    return value


def _typst_fill(node: ScenePrimitive) -> str:
    color, opacity = _color(node, "fill"), _opacity(node)
    if opacity == 1:
        return f'rgb("{color}")'
    return f'rgb("{color}").transparentize({_number((1 - opacity) * 100)}%)'


def _tikz_hex(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value) is None:
        raise _error("E_PRESENTATION_PAINT_INVALID", f"TikZ colour={_brief(value)}; expected hexadecimal RGB/RGBA")
    return "#" + "".join(char * 2 for char in value[1:]) if len(value) in {4, 5} else value


def _tikz_color_value(value: str) -> str:
    """Serialize an admitted hexadecimal colour in native xcolor syntax."""
    value = _tikz_hex(value)
    red, green, blue = (int(value[index:index + 2], 16) for index in (1, 3, 5))
    return f"{{rgb,255:red,{red};green,{green};blue,{blue}}}"


def _tikz_color(node: ScenePrimitive, channel: str) -> str:
    return _tikz_color_value(_color(node, channel))


def _tikz_channel_opacity(node: ScenePrimitive, channel: str) -> float:
    value = _tikz_hex(_color(node, channel))
    return _opacity(node) * (int(value[7:9], 16) / 255 if len(value) == 9 else 1)


def _typst_tracking(layout: object) -> str:
    """Serialize Layout's resolved tracking without deriving a font feature."""
    spacing = getattr(layout, "letter_spacing", 0.0)
    return f", tracking: {_number(spacing)}pt" if spacing else ""


def _typst_numeric_width(layout: object) -> str:
    """Project Layout's selected OpenType number width to Typst directly."""
    spacing = getattr(layout, "numeric_spacing", "proportional")
    if spacing not in {"proportional", "tabular"}:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"text layout numeric_spacing={_brief(spacing)}; expected 'proportional' or 'tabular'")
    return f', number-width: "{spacing}"'


def _tikz_tracked_text(layout: object, text: str) -> str:
    """Project completed tracking to XeTeX/fontspec's percentage of an em."""
    spacing, size = getattr(layout, "letter_spacing", 0.0), getattr(layout, "font_size", 0.0)
    if not spacing:
        return text
    if size <= 0:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"text layout font_size={_brief(size)} with letter_spacing={_brief(spacing)}; expected positive font_size")
    return f"{{\\addfontfeatures{{LetterSpace={_number(spacing / size * 100)}}}{text}}}"


_GENERIC_FAMILIES = frozenset({"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui"})
_UNSAFE_PATH = re.compile(r"[\\{}#%,=\[\]]")  # read by TeX before \detokenize, or split by fontspec's key parser
_LOADABLE_SUFFIXES = frozenset({".ttf", ".otf", ".ttc", ".otc"})


def _tikz_face(layout: object, font_files: Sequence[FontFile]) -> FontFile:
    """The first family of the completed list that Tectonic can load by file, at the weight nearest the layout's (#1553)."""
    families = [value.strip().strip("\"'") for value in str(getattr(layout, "family", "")).split(",") if value.strip()]
    weight, reasons = getattr(layout, "weight", 400), []
    for family in families:
        if family.casefold() in _GENERIC_FAMILIES:
            continue
        candidates = [item for item in font_files if item.family.casefold() == family.casefold()]
        if not candidates:
            reasons.append(f"{family!r} has no font file in the render's font closure")
            continue
        face = min(candidates, key=lambda item: (_weight_rank(weight, item.weight), str(item.path), item.index))
        path = Path(face.path)
        if face.index != 0 or path.suffix.lower() not in _LOADABLE_SUFFIXES or _UNSAFE_PATH.search(path.as_posix()) or not path.is_file():
            reasons.append(f"{family!r} is {path.name!r} (face index {face.index}), which TikZ cannot name by file")
            continue
        return face
    named = ", ".join(families) or "(empty)"
    raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED",
                 f"TikZ cannot load any family of the completed font list [{named}] by file path ({'; '.join(reasons) or 'no named family'}); "
                 "install the font package for the first family (for example chrona-fonts-noto-cjk) or select SVG")


def _tikz_numeric_text(layout: object, text: str, font_files: Sequence[FontFile] | None = None) -> str:
    """Apply Layout's selected OpenType number width in the fontspec run.

    With the render's font closure the face is named by file (`Path=` and the file name), which Tectonic loads without
    fontconfig; without one the first family is named and fontconfig must find it (#1553). Output that names a file
    depends on where it is rendered, as for an installed face on every other target.
    """
    spacing = getattr(layout, "numeric_spacing", "proportional")
    if spacing not in {"proportional", "tabular"}:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"text layout numeric_spacing={_brief(spacing)}; expected 'proportional' or 'tabular'")
    number = "Monospaced" if spacing == "tabular" else "Proportional"
    family = str(getattr(layout, "family", "")).split(",", 1)[0].strip()
    if not family:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", "text layout family is empty; expected a font family for numeric-width serialization")
    if font_files is not None:
        face = _tikz_face(layout, font_files)
        directory = Path(face.path).parent.as_posix().rstrip("/") + "/"
        return f"\\fontspec[Path=\\detokenize{{{directory}}}, Numbers={number}]{{{Path(face.path).name}}}{text}"
    return f"\\fontspec[Numbers={number}]{{{_tex_string(family)}}}{text}"


def _typst_line(layout: object, index: int) -> str:
    """One line: its single string, or its Layout-measured small-caps runs, each at its own size (#1532)."""
    runs = getattr(layout, "runs", ())
    if not runs:
        return f'#("{_typst_string(layout.lines[index])}")'
    def serialize(run: object) -> str:
        text = f'#("{_typst_string(run.text)}")'
        options = []
        if run.font_size != layout.font_size:
            options.append(f"size: {_number(run.font_size)}pt")
        if getattr(run, "family", None) is not None:
            options.append(f'font: "{_typst_string(run.family)}"')
        if getattr(run, "weight", None) is not None:
            options.append(f"weight: {run.weight}")
        return f"#text({', '.join(options)})[{text}]" if options else text
    body = "".join(serialize(run) for run in runs[index])
    if any(run.font_size == layout.font_size for run in runs[index]):
        return body
    # A line of only small runs would put its top edge at the small cap height; a hidden zero-width capital at the role
    # size keeps the line box (and so the baseline below the placed top) where the unmarked text has it.
    return f'#box(width: 0pt, hide[#text(size: {_number(layout.font_size)}pt)[#("I")]])' + body


def _tikz_line(layout: object, index: int, font_files: Sequence[FontFile] | None = None) -> str:
    """The TikZ counterpart of `_typst_line`: a smaller run is a font-size group inside the node (#1532)."""
    runs = getattr(layout, "runs", ())
    if not runs:
        return _tex_string(layout.lines[index])
    def serialize(run: object) -> str:
        size = (f"\\fontsize{{{_number(run.font_size)}pt}}"
                f"{{{_number(run.font_size * layout.line_height)}pt}}\\selectfont ") \
            if run.font_size != layout.font_size else ""
        family = getattr(run, "family", None)
        weight = getattr(run, "weight", None)
        identity = getattr(run, "asset_identity", None)
        face = ""
        if identity is not None and font_files is not None:
            selected_family = family if family is not None else str(getattr(layout, "family", "")).split(",", 1)[0].strip()
            candidates = [item for item in font_files
                          if item.content_identity == identity
                          and item.family.casefold() == selected_family.casefold()
                          and item.weight == weight]
            if len(candidates) != 1:
                raise _error("E_RENDER_FONT_CLOSURE",
                             f"TikZ run requests an unregistered exact font asset {selected_family}/{weight}/{identity}")
            selected = candidates[0]
            path = Path(selected.path)
            if (selected.index != 0 or path.suffix.lower() not in _LOADABLE_SUFFIXES
                    or _UNSAFE_PATH.search(path.as_posix()) or not path.is_file()):
                raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED",
                             f"TikZ cannot load completed run face {selected_family}/{weight} by file path ({path.name!r}, face index {selected.index})")
            directory = path.parent.as_posix().rstrip("/") + "/"
            spacing = getattr(layout, "numeric_spacing", "proportional")
            number = "Monospaced" if spacing == "tabular" else "Proportional"
            face = (f"\\fontspec[Path=\\detokenize{{{directory}}}, Numbers={number}]"
                    f"{{{path.name}}}")
        elif family is not None or weight is not None:
            selected_family = family if family is not None else str(getattr(layout, "family", "")).split(",", 1)[0].strip()
            options = []
            if weight is not None:
                options.append(f"Weight={weight}")
            face = f"\\fontspec[{','.join(options)}]{{{_tex_string(selected_family)}}}"
        content = _tex_string(run.text)
        return f"{{{size}{face}{content}}}" if size or face else content
    return "".join(serialize(run) for run in runs[index])


def _typst_rect_paint(node: ScenePrimitive) -> str:
    """Serialize completed rect paint without inventing a missing fill channel."""
    paint = node.paint
    if paint is None or (paint.fill is None and paint.stroke is None):
        raise _error("E_PRESENTATION_PAINT_INVALID", _primitive_detail(node, "a Rect with completed fill or stroke paint"))
    values = []
    if paint.fill is not None:
        values.append(f"fill: {_typst_fill(node)}")
    if paint.stroke is not None:
        values.append(f'stroke: rgb("{paint.stroke}")')
    return ", " + ", ".join(values)


def _tikz_rect_paint(node: ScenePrimitive) -> str:
    """Serialize completed rect paint without replacing outline with a fill."""
    paint = node.paint
    if paint is None or (paint.fill is None and paint.stroke is None):
        raise _error("E_PRESENTATION_PAINT_INVALID", _primitive_detail(node, "a Rect with completed fill or stroke paint"))
    values = []
    if paint.fill is not None:
        values.append(f"fill={_tikz_color(node, 'fill')}")
        values.append(f"fill opacity={_number(_tikz_channel_opacity(node, 'fill'))}")
    if paint.stroke is not None:
        values.append(f"draw={_tikz_color(node, 'stroke')}")
        values.append(f"draw opacity={_number(_tikz_channel_opacity(node, 'stroke'))}")
        if paint.stroke_width is not None:
            values.append(f"line width={_number(paint.stroke_width)}pt")
    return ", ".join(values)


def _segment_points(node: ScenePrimitive) -> list[tuple[float, float]]:
    """The vertices a Path runs through, in order (quadratic controls included as the segment's direction)."""
    if node.path_commands:
        return [point for command in node.path_commands for point in command.points]
    return list(node.points)


def _direction(origin: tuple[float, float], target: tuple[float, float]) -> float | None:
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    return None if dx == 0 and dy == 0 else degrees(atan2(dy, dx))


def _lower_marker(node: ScenePrimitive, which: str) -> tuple[list[tuple[str, tuple[tuple[float, float], ...]]], object, float]:
    """Lower a path end marker to absolute plain path commands by the SVG marker rule.

    The marker outline is in its own box (`head_length` x `head_width`); its reference point
    (`head_length - attachment_offset`, `head_width / 2`) is placed on the path end, turned to the path direction there
    (`angle_degrees` when the marker fixes one), and scaled by the stroke width unless it is in physical units. Returns the
    commands, the marker geometry and the stroke width used for a stroked marker (#1308).
    """
    marker = node.marker_start if which == "start" else node.marker_end
    points = _segment_points(node)
    if marker is None or len(points) < 2:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "a Path with two points for its marker"))
    if which == "start":
        vertex, toward = points[0], next((point for point in points[1:] if point != points[0]), points[1])
    else:
        vertex, toward = points[-1], next((point for point in reversed(points[:-1]) if point != points[-1]), points[-2])
    if marker.angle_degrees is not None:
        angle = float(marker.angle_degrees)
    else:
        # `auto` follows the path: forward from the start vertex, and into the end vertex
        found = _direction(vertex, toward) if which == "start" else _direction(toward, vertex)
        if found is None:
            raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "a Path whose end segment has a direction"))
        angle = found
    width = node.paint.stroke_width if node.paint is not None and node.paint.stroke_width is not None else 1.0
    scale = 1.0 if marker.physical_units else float(width)
    ref_x, ref_y = marker.head_length - marker.attachment_offset, marker.head_width / 2
    cos_a, sin_a = cos(radians(angle)), sin(radians(angle))

    def place(point: tuple[float, float]) -> tuple[float, float]:
        u, v = (point[0] - ref_x) * scale, (point[1] - ref_y) * scale
        return (vertex[0] + u * cos_a - v * sin_a, vertex[1] + u * sin_a + v * cos_a)

    commands = []
    for command in marker.outline:
        if command.kind not in {"move", "line", "quadratic"}:
            raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} marker outline command={command.kind!r}; expected move, line, or quadratic")
        commands.append((command.kind, tuple(place(point) for point in command.points)))
    stroke_width = (marker.stroke_width if marker.physical_units and marker.stroke_width is not None else 1.0) * (1.0 if marker.physical_units else scale)
    return commands, marker, stroke_width


def _markers(node: ScenePrimitive) -> list[tuple[str, list, object, float]]:
    return [(which, *_lower_marker(node, which)) for which, marker in (("start", node.marker_start), ("end", node.marker_end)) if marker is not None]


def _path_commands(node: ScenePrimitive) -> list[tuple[str, tuple[tuple[float, float], ...]]]:
    if len(node.points) < 2:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, f"at least two Path points; received {len(node.points)}"))
    if node.path_commands:
        for command in node.path_commands:
            if command.kind not in {"move", "line", "quadratic"}:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} Path command={command.kind!r}; expected move, line, or quadratic")
        return [(command.kind, tuple(command.points)) for command in node.path_commands]
    return [("move" if index == 0 else "line", (point,)) for index, point in enumerate(node.points)]


def _typst_pt(point: tuple[float, float]) -> str:
    return f"({_number(point[0])}pt, {_number(point[1])}pt)"


def _typst_curve(commands: list, *, fill: str | None, stroke: str | None, close: bool) -> str:
    """One absolutely positioned Typst `curve` element for completed path commands (Typst 0.13)."""
    items = []
    for kind, points in commands:
        if kind == "move":
            items.append(f"curve.move({_typst_pt(points[0])})")
        elif kind == "line":
            items.append(f"curve.line({_typst_pt(points[0])})")
        elif kind == "close":
            items.append('curve.close(mode: "straight")')
        else:
            items.append(f"curve.quad({_typst_pt(points[0])}, {_typst_pt(points[1])})")
    if close:
        items.append('curve.close(mode: "straight")')
    return f"#place(top + left, dx: 0pt, dy: 0pt)[#curve(fill: {fill or 'none'}, stroke: {stroke or 'none'}, {', '.join(items)})]"


def _typst_color(node: ScenePrimitive, channel: str) -> str:
    color, opacity = _color(node, channel), _opacity(node)
    return f'rgb("{color}")' if opacity == 1 else f'rgb("{color}").transparentize({_number((1 - opacity) * 100)}%)'


def _typst_stroke(node: ScenePrimitive, channel: str = "stroke") -> str:
    width = node.paint.stroke_width if node.paint is not None else None
    color = _typst_color(node, channel)
    return f"(paint: {color}, thickness: {_number(width)}pt)" if width is not None else color


def _tikz_data(commands: list, *, exact_quadratic: bool = False) -> str:
    parts = []
    current = start = (0.0, 0.0)
    for kind, points in commands:
        if kind == "move":
            parts.append(f"({_number(points[0][0])},{_number(points[0][1])})")
            current = start = points[0]
        elif kind == "line":
            parts.append(f"-- ({_number(points[0][0])},{_number(points[0][1])})")
            current = points[0]
        elif kind == "close":
            parts.append("-- cycle")
            current = start
        else:
            control, end = points
            if exact_quadratic:
                first = tuple(current[i] + (control[i] - current[i]) * 2 / 3 for i in (0, 1))
                second = tuple(end[i] + (control[i] - end[i]) * 2 / 3 for i in (0, 1))
                parts.append(f".. controls ({_number(first[0])},{_number(first[1])}) and ({_number(second[0])},{_number(second[1])}) .. ({_number(end[0])},{_number(end[1])})")
            else:
                parts.append(f".. controls ({_number(control[0])},{_number(control[1])}) .. ({_number(end[0])},{_number(end[1])})")
            current = end
    return " ".join(parts)


def _validate(surface: object) -> SceneSurface:
    if not isinstance(surface, SceneSurface) or surface.canvas_paint is None:
        raise _error("E_PRESENTATION_RENDER_INPUT", f"Typst/TikZ requires SceneSurface with canvas paint; received {type(surface).__name__}")
    return surface


def _requires_wobble(surface: SceneSurface) -> bool:
    """A required hand-wobble (#588) cannot be drawn here; an optional one is drawn straight."""
    return any(node.paint is not None and node.paint.wobble is not None and node.paint.wobble.fidelity == "required"
               for node in surface.primitives)


def _pattern_tile(node: ScenePrimitive, target: str) -> str:
    """Serialize one completed tile in its own clipped coordinate frame."""
    pattern, paint = node.pattern, node.paint
    parts = []

    def path(commands, fill=None, width=None, cap="butt", join="miter"):
        if target == "typst":
            color = _typst_color(node, "stroke")
            stroke = (f'(paint: {color}, thickness: {_number(width)}pt, cap: "{cap}", join: "{join}")'
                      if width is not None else None)
            return _typst_curve(commands, fill=fill, stroke=stroke, close=False)
        options = []
        if fill is not None:
            options.extend((f"fill={fill}", f"fill opacity={_number(_tikz_channel_opacity(node, 'stroke'))}"))
        if width is not None:
            options.extend((f"draw={_tikz_color(node, 'stroke')}",
                            f"draw opacity={_number(_tikz_channel_opacity(node, 'stroke'))}",
                            f"line width={_number(width)}pt", f"line cap={cap}", f"line join={join}"))
        return f"\\path[{', '.join(options)}] {_tikz_data(commands, exact_quadratic=True)};"

    if pattern.primitives and paint.fill is not None:
        if target == "typst":
            parts.append(f'#place(top + left)[#rect(width: {_number(pattern.tile_inline_size)}pt, height: {_number(pattern.tile_block_size)}pt, fill: {_typst_color(node, "fill")}, stroke: none)]')
        else:
            parts.append(f"\\path[fill={_tikz_color(node, 'fill')}, fill opacity={_number(_tikz_channel_opacity(node, 'fill'))}] (0,0) rectangle ({_number(pattern.tile_inline_size)},{_number(pattern.tile_block_size)});")
    for stroke in pattern.strokes:
        parts.append(path([("move", (stroke.start,)), ("line", (stroke.end,))], width=stroke.width))
    for item in pattern.primitives:
        if item.kind == "circle":
            channel = item.fill_channel or "ink"
            color_channel = "fill" if channel == "substrate" else "stroke"
            if target == "typst":
                fill = "none" if channel == "none" else _typst_color(node, color_channel)
                stroke = "none" if item.stroke_width is None else f'(paint: {_typst_color(node, "stroke")}, thickness: {_number(item.stroke_width)}pt)'
                parts.append(f'#place(top + left, dx: {_number(item.cx-item.radius)}pt, dy: {_number(item.cy-item.radius)}pt)[#circle(radius: {_number(item.radius)}pt, fill: {fill}, stroke: {stroke})]')
            else:
                options = ["fill=none"] if channel == "none" else [f"fill={_tikz_color(node, color_channel)}", f"fill opacity={_number(_tikz_channel_opacity(node, color_channel))}"]
                if item.stroke_width is not None:
                    options.extend((f"draw={_tikz_color(node, 'stroke')}", f"draw opacity={_number(_tikz_channel_opacity(node, 'stroke'))}", f"line width={_number(item.stroke_width)}pt"))
                parts.append(f"\\path[{', '.join(options)}] ({_number(item.cx)},{_number(item.cy)}) circle[radius={_number(item.radius)}pt];")
        elif item.kind == "rect":
            commands = [("move", ((item.x, item.y),)), ("line", ((item.x+item.inline_size, item.y),)),
                        ("line", ((item.x+item.inline_size, item.y+item.block_size),)),
                        ("line", ((item.x, item.y+item.block_size),)), ("close", ())]
            fill = _typst_color(node, "stroke") if target == "typst" else _tikz_color(node, "stroke")
            parts.append(path(commands, fill=fill))
        else:
            commands = [(command.kind, command.points) for command in item.commands]
            fill = (_typst_color(node, "stroke") if target == "typst" else _tikz_color(node, "stroke")) if item.paint == "fill" else None
            parts.append(path(commands, fill=fill, width=item.stroke_width,
                              cap=item.line_cap or "butt", join=item.line_join or "miter"))
    return "\n".join(parts)


def _pattern_channels(node: ScenePrimitive) -> tuple[str, ...]:
    channels = {"stroke"}
    if node.pattern.primitives and node.paint.fill is not None:
        channels.add("fill")
    channels.update("fill" if (item.fill_channel or "ink") == "substrate" else "stroke"
                    for item in node.pattern.primitives if item.kind == "circle" and item.fill_channel != "none")
    return tuple(sorted(channels))


def _declarable_tikz_pattern(node: ScenePrimitive) -> bool:
    """A catalogue pattern at angle 0 and full opacity is one periodic fill (#1551).

    pgf patterns cannot rotate and carry no transparency, so a rotated or translucent pattern keeps the per-tile expansion."""
    return (node.pattern is not None and bool(node.pattern.primitives) and node.pattern.angle_degrees == 0
            and all(_tikz_channel_opacity(node, channel) == 1 for channel in _pattern_channels(node)))


def _phase(offset: float, period: float) -> float:
    value = offset % period
    return 0.0 if value < 1e-6 or period - value < 1e-6 else value


def _pgf_point(x: float, y: float) -> str:
    return f"{{\\pgfpoint{{{_number(x)}pt}}{{{_number(y)}pt}}}}"


def _pgf_path(commands: list, fill: str | None, width: float | None, stroke: str | None, cap: str = "butt", join: str = "miter") -> str:
    parts = []
    if fill is not None:
        parts.append(f"\\pgfsetfillcolor{fill}")
    if width is not None:
        parts.extend((f"\\pgfsetstrokecolor{stroke}", f"\\pgfset{cap}cap", f"\\pgfset{join}join", f"\\pgfsetlinewidth{{{_number(width)}pt}}"))
    for kind, points in commands:
        if kind == "close":
            parts.append("\\pgfpathclose")
            continue
        names = {"move": "moveto", "line": "lineto", "quadratic": "quadraticcurveto"}
        parts.append(f"\\pgfpath{names[kind]}" + "".join(_pgf_point(x, y) for x, y in points))
    use = ",".join(name for name, on in (("fill", fill is not None), ("stroke", width is not None)) if on)
    return "".join(parts) + (f"\\pgfusepath{{{use}}}" if use else "")


def _pgf_tile(node: ScenePrimitive) -> str:
    """The completed tile in pgf's basic layer, in the tile's own y-down frame (the caller's transform flips it).

    Only paths: a nested tikzpicture, or any box, would leak into the page when pgf runs the pattern body."""
    pattern, paint = node.pattern, node.paint
    tw, th = pattern.tile_inline_size, pattern.tile_block_size
    ink, substrate = _tikz_color(node, "stroke"), _tikz_color(node, "fill") if paint.fill is not None else None
    parts = []
    if substrate is not None:
        parts.append(_pgf_path([("move", ((0, 0),)), ("line", ((tw, 0),)), ("line", ((tw, th),)), ("line", ((0, th),)), ("close", ())], substrate, None, None))
    for stroke in pattern.strokes:
        parts.append(_pgf_path([("move", (stroke.start,)), ("line", (stroke.end,))], None, stroke.width, ink))
    for item in pattern.primitives:
        if item.kind == "circle":
            channel = item.fill_channel or "ink"
            fill = None if channel == "none" else (substrate if channel == "substrate" else ink)
            head = f"\\pgfsetfillcolor{fill}" if fill is not None else ""
            if item.stroke_width is not None:
                head += f"\\pgfsetstrokecolor{ink}\\pgfsetlinewidth{{{_number(item.stroke_width)}pt}}"
            use = ",".join(n for n, on in (("fill", fill is not None), ("stroke", item.stroke_width is not None)) if on)
            if use:
                parts.append(f"{head}\\pgfpathcircle{_pgf_point(item.cx, item.cy)}{{{_number(item.radius)}pt}}\\pgfusepath{{{use}}}")
        elif item.kind == "rect":
            commands = [("move", ((item.x, item.y),)), ("line", ((item.x+item.inline_size, item.y),)),
                        ("line", ((item.x+item.inline_size, item.y+item.block_size),)),
                        ("line", ((item.x, item.y+item.block_size),)), ("close", ())]
            parts.append(_pgf_path(commands, ink, None, None))
        else:
            commands = [(command.kind, command.points) for command in item.commands]
            parts.append(_pgf_path(commands, ink if item.paint == "fill" else None, item.stroke_width, ink,
                                   item.line_cap or "butt", item.line_join or "miter"))
    return "\n".join(parts)


def _tikz_pattern_declaration(node: ScenePrimitive, name: str, page_height: float) -> str:
    """One pgf pattern whose lattice is the Scene's: origin (x right, y down from the canvas top), tile size, angle 0.

    A pgf pattern is anchored at the page's lower-left corner with y up (measured against Tectonic 0.17.0), so the tile body
    is drawn flipped and offset by the origin's phase, as up to four translated copies; the pattern's bounding box clips
    each of them. Each copy is also clipped to its own tile, as the expansion clips every tile."""
    pattern = node.pattern
    tw, th = pattern.tile_inline_size, pattern.tile_block_size
    ox, oy = pattern.origin
    u0, v0 = _phase(ox, tw), _phase(page_height - oy, th)
    tile = _pgf_tile(node)
    box = f"\\pgfpathrectangle{{\\pgfpointorigin}}{{\\pgfpoint{{{_number(tw)}pt}}{{{_number(th)}pt}}}}"
    copies = [f"\\begin{{pgfscope}}\\pgftransformcm{{1}}{{0}}{{0}}{{-1}}{{\\pgfpoint{{{_number(u)}pt}}{{{_number(v)}pt}}}}{box}\\pgfusepath{{clip}}\n{tile}\n\\end{{pgfscope}}"
              for u in dict.fromkeys((u0, u0 - tw) if u0 else (0.0,)) for v in dict.fromkeys((v0, v0 + th) if v0 else (th,))]
    size = f"{{\\pgfpoint{{{_number(tw)}pt}}{{{_number(th)}pt}}}}"
    return f"\\pgfdeclarepatterninherentlycolored{{{name}}}{{\\pgfpointorigin}}{size}{size}{{%\n" + "\n".join(copies) + "%\n}"


def _pattern_rect(node: ScenePrimitive, target: str, declared: str | None = None) -> str:
    """Lower a periodic fill without changing Layout's completed geometry.

    `declared` names the TikZ pattern that already holds the tile lattice: the fill is then one path (#1551)."""
    cells = repeat_cells(node)
    if declared is not None:
        x, y, w, h = node.bounds
        rounded = f", rounded corners={_number(node.corner_radius)}pt" if node.corner_radius else ""
        return f"\\path[pattern={declared}{rounded}] ({_number(x)},{_number(y)}) rectangle ({_number(x+w)},{_number(y+h)});"
    pattern = node.pattern
    x, y, w, h = node.bounds
    tile = _pattern_tile(node, target)
    tw, th = map(_number, (pattern.tile_inline_size, pattern.tile_block_size))
    radius = _number(node.corner_radius or 0)
    if target == "typst":
        copies = [f'#place(top + left, dx: {_number(cx-x)}pt, dy: {_number(cy-y)}pt)[#rotate({_number(pattern.angle_degrees)}deg, origin: top + left, reflow: false)[#box(width: {tw}pt, height: {th}pt, inset: 0pt, clip: true)[{tile}]]]'
                  for cx, cy in cells]
        return f'#place(top + left, dx: {_number(x)}pt, dy: {_number(y)}pt)[#box(width: {_number(w)}pt, height: {_number(h)}pt, radius: {radius}pt, inset: 0pt, clip: true)[' + "\n".join(copies) + "]]"
    copies = [r"\begin{scope}", f"\\clip[rounded corners={radius}pt] ({_number(x)},{_number(y)}) rectangle ({_number(x+w)},{_number(y+h)});"]
    for cx, cy in cells:
        copies.extend((f"\\begin{{scope}}[shift={{({_number(cx)},{_number(cy)})}}, rotate={_number(-pattern.angle_degrees)}]",
                       f"\\clip (0,0) rectangle ({tw},{th});", tile, r"\end{scope}"))
    copies.append(r"\end{scope}")
    return "\n".join(copies)


def _unsupported_details(surface: SceneSurface, target: str) -> str:
    reasons = []
    for node in surface.primitives:
        features = []
        if node.paint is not None and node.paint.wobble is not None and node.paint.wobble.fidelity == "required":
            features.append("required wobble")
        if node.pattern is not None and node.kind != "Rect":
            features.append("pattern")
        if node.stroke_clip is not None:
            features.append("aligned stroke clip")
        if features:
            reasons.append(f"{node.scene_id!r} (role {node.visual_role}): {', '.join(features)}")
    return f"{target} cannot serialize completed features ({'; '.join(reasons)}); select SVG"


def render_v05_typst(surface: SceneSurface) -> str:
    if any(node.stroke_clip is not None for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "Typst"))
    if _requires_wobble(surface) or any(node.pattern is not None and node.kind != "Rect" for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "Typst"))
    if surface.canvas_bounds is None:
        raise _error("E_PRESENTATION_RENDER_INPUT", "Typst requires completed canvasBounds")
    _, _, width, height = surface.canvas_bounds
    background = surface.canvas_paint.fill
    if background is None: raise _error("E_PRESENTATION_PAINT_INVALID", "Typst canvasPaint.fill is required as the page background")
    parts = ["// chrona-typst/v0.1", f"#set page(width: {_number(width)}pt, height: {_number(height)}pt, margin: 0pt)",
             f'#place(top + left, dx: 0pt, dy: 0pt)[#rect(width: {_number(width)}pt, height: {_number(height)}pt, fill: rgb("{background}"))]']
    for node in (node for _, node in sorted(enumerate(surface.primitives), key=lambda item: (item[1].paint_order, item[0]))):
        x, y, w, h = node.bounds
        parts.append(f"// scene-id: {_typst_string(node.scene_id)} source-ref: {_typst_string(node.source_ref)}")
        if node.kind == "Rect":
            if node.pattern is not None:
                parts.append(_pattern_rect(node, "typst"))
                continue
            radius = f', radius: {_number(node.corner_radius)}pt' if node.corner_radius else ''
            parts.append(f'#place(top + left, dx: {_number(x)}pt, dy: {_number(y)}pt)[#rect(width: {_number(w)}pt, height: {_number(h)}pt{radius}{_typst_rect_paint(node)})]')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "Text payload, textLayout, and baseline"))
            layout = node.text_layout
            parts.append(f"// font-asset: {_typst_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = "#linebreak()".join(_typst_line(layout, index) for index in range(len(layout.lines)))
            rendered = f'#text(font: {_typst_font(layout.family)}, weight: {layout.weight}, size: {_number(layout.font_size)}pt{_typst_tracking(layout)}{_typst_numeric_width(layout)}, fill: {_typst_fill(node)})[{text}]'
            if layout.horizontal_scale != 1:
                # Compression is applied in the text's own frame, inside the rotation (#585).
                rendered = (f'#scale(x: {_number(layout.horizontal_scale * 100)}%, y: 100%, origin: left + top, '
                            f'reflow: false)[{rendered}]')
            if layout.rotation_degrees:
                rendered = (f'#rotate({_number(layout.rotation_degrees)}deg, origin: top + left, reflow: false)['
                            f'{rendered}]')
                parts.append(f'#place(top + left, dx: {_number(node.baseline[0])}pt, dy: {_number(node.baseline[1])}pt)[{rendered}]')
            else:
                parts.append(f'#place(top + left, dx: {_number(x)}pt, dy: {_number(y)}pt)[{rendered}]')
        elif node.kind == "Symbol":
            if node.symbol is None:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "completed Symbol geometry"))
            commands = [(command.kind, tuple(command.points)) for command in node.symbol.outline]
            for kind, _points in commands:
                if kind not in {"move", "line", "quadratic"}:
                    raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} Symbol outline command={kind!r}; expected move, line, or quadratic")
            paint = node.paint
            if paint is None or (paint.fill is None and paint.stroke is None):
                raise _error("E_PRESENTATION_PAINT_INVALID", _primitive_detail(node, "a Symbol with completed fill or stroke paint"))
            parts.append(_typst_curve(commands, fill=_typst_color(node, "fill") if paint.fill is not None else None,
                                      stroke=_typst_stroke(node) if paint.stroke is not None else None, close=True))
        elif node.kind == "Path":
            parts.append(_typst_curve(_path_commands(node), fill=None, stroke=_typst_stroke(node), close=False))
            for which, commands, marker, stroke_width in _markers(node):
                parts.append(f"// marker-{which} of scene-id: {_typst_string(node.scene_id)}")
                if marker.paint_mode == "fill":
                    parts.append(_typst_curve(commands, fill=_typst_color(node, "stroke"), stroke=None, close=True))
                else:
                    parts.append(_typst_curve(commands, fill=None, stroke=f"(paint: {_typst_color(node, 'stroke')}, thickness: {_number(stroke_width)}pt)", close=False))
        else:
            raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "a supported Rect, Text, Symbol, or Path primitive"))
    return "\n".join(parts) + "\n"


def render_v05_tikz(surface: SceneSurface, font_files: Sequence[FontFile] | None = None) -> str:
    if any(node.stroke_clip is not None for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "TikZ"))
    if _requires_wobble(surface) or any(node.pattern is not None and node.kind != "Rect" for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "TikZ"))
    if surface.canvas_bounds is None:
        raise _error("E_PRESENTATION_RENDER_INPUT", "TikZ requires completed canvasBounds")
    _, _, width, height = surface.canvas_bounds
    declarations: dict[str, str] = {}
    pattern_names: dict[int, str] = {}
    for index, node in enumerate(surface.primitives):
        if node.kind == "Rect" and _declarable_tikz_pattern(node):
            repeat_cells(node)  # the same validation as the expansion
            body = _tikz_pattern_declaration(node, "@", height)
            name = declarations.setdefault(body, f"chronaPattern{chr(97 + len(declarations)) if len(declarations) < 26 else len(declarations)}")
            pattern_names[index] = name
    library = [r"\usetikzlibrary{patterns}"] if declarations else []
    declared = [body.replace("{@}", "{" + name + "}", 1) for body, name in declarations.items()]
    parts = ["% chrona-tikz/v0.1", r"\documentclass{article}",
             f"\\usepackage[paperwidth={_number(width)}pt,paperheight={_number(height)}pt,margin=0pt]{{geometry}}",
             r"\usepackage{tikz}", *library, r"\usepackage{fontspec}",
             r"\pagestyle{empty}", r"\begin{document}", *declared, r"\noindent",
             r"\begin{tikzpicture}[x=1pt,y=-1pt]",
             f"\\path[fill={_tikz_color_value(surface.canvas_paint.fill)}] (0,0) rectangle ({_number(width)},{_number(height)});"]
    for index, node in ((index, node) for index, node in sorted(enumerate(surface.primitives), key=lambda item: (item[1].paint_order, item[0]))):
        x, y, w, h = node.bounds
        parts.append(f"% scene-id: {_tex_string(node.scene_id)} source-ref: {_tex_string(node.source_ref)}")
        if node.kind == "Rect":
            if node.pattern is not None:
                parts.append(_pattern_rect(node, "tikz", pattern_names.get(index)))
                continue
            rounded = f", rounded corners={_number(node.corner_radius)}pt" if node.corner_radius else ""
            parts.append(f"\\path[{_tikz_rect_paint(node)}{rounded}] ({_number(x)},{_number(y)}) rectangle ({_number(x+w)},{_number(y+h)});")
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "Text payload, textLayout, and baseline"))
            layout = node.text_layout
            parts.append(f"% font-asset: {_tex_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = _tikz_tracked_text(layout, r"\\".join(
                _tikz_line(layout, index, font_files) for index in range(len(layout.lines))))
            rotation = f", rotate={_number(layout.rotation_degrees)}" if layout.rotation_degrees else ""
            # `inner sep=0pt` puts the text's own origin on the anchor; the default 0.333em padding would shift the run right
            # and, under a scale, about a pivot that is not the baseline start. Compression acts in the text's own frame, so it
            # follows the rotation (#585, #1532).
            rotation += f", xscale={_number(layout.horizontal_scale)}" if layout.horizontal_scale != 1 else ""
            parts.append(f"\\node[anchor=base west, inner sep=0pt, align=left{rotation}, text={_tikz_color(node, 'fill')}, text opacity={_number(_tikz_channel_opacity(node, 'fill'))}, font=\\fontsize{{{_number(layout.font_size)}pt}}{{{_number(layout.font_size * layout.line_height)}pt}}\\selectfont] at ({_number(node.baseline[0])},{_number(node.baseline[1])}) {{{_tikz_numeric_text(layout, text, font_files)}}};")
        elif node.kind == "Symbol":
            if node.symbol is None:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "completed Symbol geometry"))
            symbol = [(command.kind, tuple(command.points)) for command in node.symbol.outline]
            for kind, _points in symbol:
                if kind not in {"move", "line", "quadratic"}:
                    raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} Symbol outline command={kind!r}; expected move, line, or quadratic")
            paint = node.paint
            if paint is None or (paint.fill is None and paint.stroke is None):
                raise _error("E_PRESENTATION_PAINT_INVALID", _primitive_detail(node, "a Symbol with completed fill or stroke paint"))
            parts.append(f"\\path[{_tikz_rect_paint(node)}] {_tikz_data(symbol)};")
        elif node.kind == "Path":
            width = node.paint.stroke_width if node.paint is not None else None
            line = f", line width={_number(width)}pt" if width is not None else ""
            parts.append(f"\\draw[draw={_tikz_color(node, 'stroke')}, draw opacity={_number(_tikz_channel_opacity(node, 'stroke'))}{line}] {_tikz_data(_path_commands(node))};")
            for which, commands, marker, stroke_width in _markers(node):
                parts.append(f"% marker-{which} of scene-id: {_tex_string(node.scene_id)}")
                if marker.paint_mode == "fill":
                    parts.append(f"\\path[fill={_tikz_color(node, 'stroke')}, fill opacity={_number(_tikz_channel_opacity(node, 'stroke'))}] {_tikz_data(commands)} -- cycle;")
                else:
                    parts.append(f"\\draw[draw={_tikz_color(node, 'stroke')}, draw opacity={_number(_tikz_channel_opacity(node, 'stroke'))}, line width={_number(stroke_width)}pt] {_tikz_data(commands)};")
        else:
            raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "a supported Rect, Text, Symbol, or Path primitive"))
    parts.extend((r"\end{tikzpicture}", r"\end{document}"))
    return "\n".join(parts) + "\n"


class V05TypstRenderer:
    target_kind = "typst"

    def render(self, surface: object) -> RenderArtifact:
        checked_surface = _validate(surface)
        return RenderArtifact("typst", "application/x-typst", render_v05_typst(checked_surface).encode("utf-8"), "chrona-typst/v0.1")


class V05TikzRenderer:
    target_kind = "tikz"

    def __init__(self, font_files: Sequence[FontFile] | None = None) -> None:
        self.font_files = None if font_files is None else tuple(font_files)

    def render(self, surface: object) -> RenderArtifact:
        checked_surface = _validate(surface)
        return RenderArtifact("tikz", "application/x-tex", render_v05_tikz(checked_surface, self.font_files).encode("utf-8"), "chrona-tikz/v0.1")
