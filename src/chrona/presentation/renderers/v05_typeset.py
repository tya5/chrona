"""Positioned Typst and TikZ serialization of completed Scene surfaces."""
from __future__ import annotations

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
        if node.marker_start is not None or node.marker_end is not None:
            features.append("path markers")
        if node.pattern is not None:
            features.append("pattern")
        if target == "Typst" and node.symbol is not None:
            features.append("symbol")
        if node.stroke_clip is not None:
            features.append("aligned stroke clip")
        if node.text_layout is not None and node.text_layout.runs:
            features.append("small-caps runs")
        if features:
            reasons.append(f"{node.scene_id!r}: {', '.join(features)}")
    return f"{target} cannot serialize completed features ({'; '.join(reasons)}); select SVG"


def render_v05_typst(surface: SceneSurface) -> str:
    if any(node.stroke_clip is not None or (node.text_layout is not None and node.text_layout.runs)
           for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "Typst"))
    if _requires_wobble(surface) or any(node.marker_start is not None or node.marker_end is not None or node.pattern is not None or node.symbol is not None for node in surface.primitives):
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
            raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _primitive_detail(node, "SVG for symbol geometry"))
        elif node.kind == "Path":
            if node.path_commands:
                raise _error("E_PRESENTATION_ROUNDED_PATH_UNSUPPORTED", _primitive_detail(node, f"Typst path without path_commands; received {len(node.path_commands)} path commands"))
            if len(node.points) < 2:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "at least two Path points"))
            points = ", ".join(f"({_number(px)}pt, {_number(py)}pt)" for px, py in node.points)
            parts.append(f'// path points: {points} stroke: {_color(node, "stroke")} opacity: {_number(_opacity(node))}')
        else:
            raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, "a supported Rect, Text, Symbol, or Path primitive"))
    return "\n".join(parts) + "\n"


def render_v05_tikz(surface: SceneSurface) -> str:
    if any(node.stroke_clip is not None or (node.text_layout is not None and node.text_layout.runs)
           for node in surface.primitives):
        raise _error("E_VISUAL_CAPABILITY_UNSUPPORTED", _unsupported_details(surface, "TikZ"))
    if _requires_wobble(surface) or any(node.marker_start is not None or node.marker_end is not None or node.pattern is not None for node in surface.primitives):
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
            if node.symbol.outline:
                commands = []
                for command in node.symbol.outline:
                    if command.kind == "move":
                        commands.append(f"({_number(command.points[0][0])},{_number(command.points[0][1])})")
                    elif command.kind == "line":
                        commands.append(f"-- ({_number(command.points[0][0])},{_number(command.points[0][1])})")
                    elif command.kind == "quadratic":
                        control, end = command.points
                        commands.append(f".. controls ({_number(control[0])},{_number(control[1])}) .. ({_number(end[0])},{_number(end[1])})")
                    else:
                        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} Symbol outline command={command.kind!r}; expected move, line, or quadratic")
                parts.append(f"\\path[fill={_color(node, 'fill')}{_tikz_opacity(node)}] {' '.join(commands)};")
                continue
        elif node.kind == "Path":
            if len(node.points) < 2:
                raise _error("E_PRESENTATION_PRIMITIVE_INVALID", _primitive_detail(node, f"at least two Path points; received {len(node.points)}"))
            if node.path_commands:
                commands = []
                for command in node.path_commands:
                    if command.kind == "move":
                        commands.append(f"({_number(command.points[0][0])},{_number(command.points[0][1])})")
                    elif command.kind == "line":
                        commands.append(f"-- ({_number(command.points[0][0])},{_number(command.points[0][1])})")
                    elif command.kind == "quadratic":
                        control, end = command.points
                        commands.append(f".. controls ({_number(control[0])},{_number(control[1])}) .. ({_number(end[0])},{_number(end[1])})")
                    else:
                        raise _error("E_PRESENTATION_PRIMITIVE_INVALID", f"scene_id={node.scene_id!r} Path command={command.kind!r}; expected move, line, or quadratic")
                points = " ".join(commands)
            else:
                points = " -- ".join(f"({_number(px)},{_number(py)})" for px, py in node.points)
            parts.append(f"\\draw[draw={_color(node, 'stroke')}, opacity={_number(_opacity(node))}] {points};")
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
