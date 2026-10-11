"""Positioned Typst and TikZ serialization of completed Scene surfaces."""
from __future__ import annotations

from math import atan2, cos, degrees, radians, sin

from chrona.core.ports import RenderArtifact
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface


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


def _tikz_opacity(node: ScenePrimitive) -> str:
    opacity = _opacity(node)
    return "" if opacity == 1 else f", fill opacity={_number(opacity)}, draw opacity={_number(opacity)}"


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
    """Keep TikZ's letterspace request proportional to the completed em value."""
    spacing, size = getattr(layout, "letter_spacing", 0.0), getattr(layout, "font_size", 0.0)
    if not spacing:
        return text
    if size <= 0:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"text layout font_size={_brief(size)} with letter_spacing={_brief(spacing)}; expected positive font_size")
    return f"\\textls[{_number(spacing / size * 1000)}]{{{text}}}"


def _tikz_numeric_text(layout: object, text: str) -> str:
    """Apply Layout's selected OpenType number width in the fontspec run."""
    spacing = getattr(layout, "numeric_spacing", "proportional")
    if spacing not in {"proportional", "tabular"}:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"text layout numeric_spacing={_brief(spacing)}; expected 'proportional' or 'tabular'")
    number = "Monospaced" if spacing == "tabular" else "Proportional"
    family = str(getattr(layout, "family", "")).split(",", 1)[0].strip()
    if not family:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", "text layout family is empty; expected a font family for numeric-width serialization")
    return f"\\fontspec[Numbers={number}]{{{_tex_string(family)}}}{text}"


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
        values.append(f"fill={paint.fill}")
    if paint.stroke is not None:
        values.append(f"draw={paint.stroke}")
        if paint.stroke_width is not None:
            values.append(f"line width={_number(paint.stroke_width)}pt")
    return ", ".join(values) + _tikz_opacity(node)


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
        else:
            items.append(f"curve.quad({_typst_pt(points[0])}, {_typst_pt(points[1])})")
    if close:
        items.append("curve.close()")
    return f"#place(left: 0pt, top: 0pt)[#curve(fill: {fill or 'none'}, stroke: {stroke or 'none'}, {', '.join(items)})]"


def _typst_color(node: ScenePrimitive, channel: str) -> str:
    color, opacity = _color(node, channel), _opacity(node)
    return f'rgb("{color}")' if opacity == 1 else f'rgb("{color}").transparentize({_number((1 - opacity) * 100)}%)'


def _typst_stroke(node: ScenePrimitive, channel: str = "stroke") -> str:
    width = node.paint.stroke_width if node.paint is not None else None
    color = _typst_color(node, channel)
    return f"(paint: {color}, thickness: {_number(width)}pt)" if width is not None else color


def _tikz_data(commands: list) -> str:
    parts = []
    for kind, points in commands:
        if kind == "move":
            parts.append(f"({_number(points[0][0])},{_number(points[0][1])})")
        elif kind == "line":
            parts.append(f"-- ({_number(points[0][0])},{_number(points[0][1])})")
        else:
            parts.append(f".. controls ({_number(points[0][0])},{_number(points[0][1])}) .. ({_number(points[1][0])},{_number(points[1][1])})")
    return " ".join(parts)


def _validate(surface: object) -> SceneSurface:
    if not isinstance(surface, SceneSurface) or surface.canvas_paint is None:
        raise _error("E_PRESENTATION_RENDER_INPUT", f"Typst/TikZ requires SceneSurface with canvas paint; received {type(surface).__name__}")
    return surface


def _requires_wobble(surface: SceneSurface) -> bool:
    """A required hand-wobble (#588) cannot be drawn here; an optional one is drawn straight."""
    return any(node.paint is not None and node.paint.wobble is not None and node.paint.wobble.fidelity == "required"
               for node in surface.primitives)


def _unsupported_details(surface: SceneSurface, target: str) -> str:
    reasons = []
    for node in surface.primitives:
        features = []
        if node.paint is not None and node.paint.wobble is not None and node.paint.wobble.fidelity == "required":
            features.append("required wobble")
        if node.pattern is not None:
            features.append("pattern")
        if node.stroke_clip is not None:
            features.append("aligned stroke clip")
        if node.text_layout is not None and node.text_layout.runs:
            features.append("small-caps runs")
        if features:
            reasons.append(f"{node.scene_id!r} (role {node.visual_role}): {', '.join(features)}")
    return f"{target} cannot serialize completed features ({'; '.join(reasons)}); select SVG"


def render_v05_typst(surface: SceneSurface) -> str:
    if any(node.stroke_clip is not None or (node.text_layout is not None and node.text_layout.runs)
           for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "Typst"))
    if _requires_wobble(surface) or any(node.pattern is not None for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "Typst"))
    if surface.canvas_bounds is None:
        raise _error("E_PRESENTATION_RENDER_INPUT", "Typst requires completed canvasBounds")
    _, _, width, height = surface.canvas_bounds
    background = surface.canvas_paint.fill
    if background is None: raise _error("E_PRESENTATION_PAINT_INVALID", "Typst canvasPaint.fill is required as the page background")
    parts = ["// chrona-typst/v0.1", f"#set page(width: {_number(width)}pt, height: {_number(height)}pt, margin: 0pt)",
             f'#rect(width: {_number(width)}pt, height: {_number(height)}pt, fill: rgb("{background}"))']
    for node in (node for _, node in sorted(enumerate(surface.primitives), key=lambda item: (item[1].paint_order, item[0]))):
        x, y, w, h = node.bounds
        parts.append(f"// scene-id: {_typst_string(node.scene_id)} source-ref: {_typst_string(node.source_ref)}")
        if node.kind == "Rect":
            radius = f', radius: {_number(node.corner_radius)}pt' if node.corner_radius else ''
            parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[#rect(width: {_number(w)}pt, height: {_number(h)}pt{radius}{_typst_rect_paint(node)})]')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "Text payload, textLayout, and baseline"))
            layout = node.text_layout
            parts.append(f"// font-asset: {_typst_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = "\\n".join(_typst_string(line) for line in layout.lines)
            rendered = f'#text(font: "{_typst_string(layout.family)}", weight: {layout.weight}, size: {_number(layout.font_size)}pt{_typst_tracking(layout)}{_typst_numeric_width(layout)}, fill: {_typst_fill(node)})[{text}]'
            if layout.horizontal_scale != 1:
                # Compression is applied in the text's own frame, inside the rotation (#585).
                rendered = (f'#scale(x: {_number(layout.horizontal_scale * 100)}%, y: 100%, origin: left + top, '
                            f'reflow: false)[{rendered}]')
            if layout.rotation_degrees:
                rendered = (f'#rotate({_number(layout.rotation_degrees)}deg, origin: top + left, reflow: false)['
                            f'{rendered}]')
                parts.append(f'#place(left: {_number(node.baseline[0])}pt, top: {_number(node.baseline[1])}pt)[{rendered}]')
            else:
                parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[{rendered}]')
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


def render_v05_tikz(surface: SceneSurface) -> str:
    if any(node.stroke_clip is not None or (node.text_layout is not None and node.text_layout.runs)
           for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "TikZ"))
    if _requires_wobble(surface) or any(node.pattern is not None for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "TikZ"))
    if surface.canvas_bounds is None:
        raise _error("E_PRESENTATION_RENDER_INPUT", "TikZ requires completed canvasBounds")
    _, _, width, height = surface.canvas_bounds
    parts = ["% chrona-tikz/v0.1", r"\documentclass{article}",
             f"\\usepackage[paperwidth={_number(width)}pt,paperheight={_number(height)}pt,margin=0pt]{{geometry}}",
             r"\usepackage{tikz}", r"\usepackage{fontspec}", *( [r"\usepackage{letterspace}"]
                                          if any(node.text_layout is not None and node.text_layout.letter_spacing
                                                 for node in surface.primitives) else []),
             r"\pagestyle{empty}", r"\begin{document}", r"\noindent",
             r"\begin{tikzpicture}[x=1pt,y=-1pt]",
             f"\\path[fill={surface.canvas_paint.fill}] (0,0) rectangle ({_number(width)},{_number(height)});"]
    for node in (node for _, node in sorted(enumerate(surface.primitives), key=lambda item: (item[1].paint_order, item[0]))):
        x, y, w, h = node.bounds
        parts.append(f"% scene-id: {_tex_string(node.scene_id)} source-ref: {_tex_string(node.source_ref)}")
        if node.kind == "Rect":
            rounded = f", rounded corners={_number(node.corner_radius)}pt" if node.corner_radius else ""
            parts.append(f"\\path[{_tikz_rect_paint(node)}{rounded}] ({_number(x)},{_number(y)}) rectangle ({_number(x+w)},{_number(y+h)});")
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "Text payload, textLayout, and baseline"))
            layout = node.text_layout
            if layout.horizontal_scale != 1:
                # No engine verifies a TikZ node scale about the baseline pivot, so none is shipped (#585).
                raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", f"Text scene_id={node.scene_id!r} requires horizontal_scale={layout.horizontal_scale!r}; TikZ has no verified horizontal text scale")
            parts.append(f"% font-asset: {_tex_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = _tikz_tracked_text(layout, r"\\".join(_tex_string(line) for line in layout.lines))
            rotation = f", rotate={_number(layout.rotation_degrees)}" if layout.rotation_degrees else ""
            parts.append(f"\\node[anchor=base west, align=left{rotation}, text={_color(node, 'fill')}, text opacity={_number(_opacity(node))}, font=\\fontsize{{{_number(layout.font_size)}pt}}{{{_number(layout.font_size * layout.line_height)}pt}}\\selectfont] at ({_number(node.baseline[0])},{_number(node.baseline[1])}) {{{_tikz_numeric_text(layout, text)}}};")
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
            parts.append(f"\\draw[draw={_color(node, 'stroke')}, opacity={_number(_opacity(node))}{line}] {_tikz_data(_path_commands(node))};")
            for which, commands, marker, stroke_width in _markers(node):
                parts.append(f"% marker-{which} of scene-id: {_tex_string(node.scene_id)}")
                if marker.paint_mode == "fill":
                    parts.append(f"\\path[fill={_color(node, 'stroke')}{_tikz_opacity(node)}] {_tikz_data(commands)} -- cycle;")
                else:
                    parts.append(f"\\draw[draw={_color(node, 'stroke')}, opacity={_number(_opacity(node))}, line width={_number(stroke_width)}pt] {_tikz_data(commands)};")
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

    def render(self, surface: object) -> RenderArtifact:
        checked_surface = _validate(surface)
        return RenderArtifact("tikz", "application/x-tex", render_v05_tikz(checked_surface).encode("utf-8"), "chrona-tikz/v0.1")
