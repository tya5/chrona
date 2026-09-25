"""Positioned Typst and TikZ serialization of completed Scene surfaces."""
from __future__ import annotations

from chrona.core.ports import RenderArtifact
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface


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
        raise ValueError("E_PRESENTATION_PAINT_INVALID")
    return value


def _opacity(node: ScenePrimitive) -> float:
    value = node.paint.opacity if node.paint is not None else None
    if not 0 <= value <= 1:
        raise ValueError("E_PRESENTATION_OPACITY_INVALID")
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
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return f', number-width: "{spacing}"'


def _tikz_tracked_text(layout: object, text: str) -> str:
    """Keep TikZ's letterspace request proportional to the completed em value."""
    spacing, size = getattr(layout, "letter_spacing", 0.0), getattr(layout, "font_size", 0.0)
    if not spacing:
        return text
    if size <= 0:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return f"\\textls[{_number(spacing / size * 1000)}]{{{text}}}"


def _tikz_numeric_text(layout: object, text: str) -> str:
    """Apply Layout's selected OpenType number width in the fontspec run."""
    spacing = getattr(layout, "numeric_spacing", "proportional")
    if spacing not in {"proportional", "tabular"}:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    number = "Monospaced" if spacing == "tabular" else "Proportional"
    family = str(getattr(layout, "family", "")).split(",", 1)[0].strip()
    if not family:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return f"\\fontspec[Numbers={number}]{{{_tex_string(family)}}}{text}"


def _typst_rect_paint(node: ScenePrimitive) -> str:
    """Serialize completed rect paint without inventing a missing fill channel."""
    paint = node.paint
    if paint is None or (paint.fill is None and paint.stroke is None):
        raise ValueError("E_PRESENTATION_PAINT_INVALID")
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
        raise ValueError("E_PRESENTATION_PAINT_INVALID")
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
        raise ValueError("E_PRESENTATION_RENDER_INPUT")
    return surface


def render_v05_typst(surface: SceneSurface, *, viewport: tuple[float, float]) -> str:
    if any(node.marker_start is not None or node.marker_end is not None or node.pattern is not None or node.symbol is not None for node in surface.primitives):
        raise ValueError("E_VISUAL_CAPABILITY_UNSUPPORTED")
    width, height = viewport
    background = surface.canvas_paint.fill
    if background is None: raise ValueError("E_PRESENTATION_PAINT_INVALID")
    parts = ["// chrona-typst/v0.1", f"#set page(width: {_number(width)}pt, height: {_number(height)}pt, margin: 0pt)",
             f'#rect(width: {_number(width)}pt, height: {_number(height)}pt, fill: rgb("{background}"))']
    for node in surface.primitives:
        x, y, w, h = node.bounds
        parts.append(f"// scene-id: {_typst_string(node.scene_id)} source-ref: {_typst_string(node.source_ref)}")
        if node.kind == "Rect":
            radius = f', radius: {_number(node.corner_radius)}pt' if node.corner_radius else ''
            parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[#rect(width: {_number(w)}pt, height: {_number(h)}pt{radius}{_typst_rect_paint(node)})]')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            layout = node.text_layout
            parts.append(f"// font-asset: {_typst_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = "\\n".join(_typst_string(line) for line in layout.lines)
            rendered = f'#text(font: "{_typst_string(layout.family)}", weight: {layout.weight}, size: {_number(layout.font_size)}pt{_typst_tracking(layout)}{_typst_numeric_width(layout)}, fill: {_typst_fill(node)})[{text}]'
            if layout.rotation_degrees:
                rendered = (f'#rotate({_number(layout.rotation_degrees)}deg, origin: top + left, reflow: false)['
                            f'{rendered}]')
                parts.append(f'#place(left: {_number(node.baseline[0])}pt, top: {_number(node.baseline[1])}pt)[{rendered}]')
            else:
                parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[{rendered}]')
        elif node.kind == "Symbol":
            if node.symbol is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            raise ValueError("E_VISUAL_CAPABILITY_UNSUPPORTED")
        elif node.kind == "Path":
            if node.path_commands:
                raise ValueError("E_PRESENTATION_ROUNDED_PATH_UNSUPPORTED")
            if len(node.points) < 2:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            points = ", ".join(f"({_number(px)}pt, {_number(py)}pt)" for px, py in node.points)
            parts.append(f'// path points: {points} stroke: {_color(node, "stroke")} opacity: {_number(_opacity(node))}')
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join(parts) + "\n"


def render_v05_tikz(surface: SceneSurface, *, viewport: tuple[float, float]) -> str:
    if any(node.marker_start is not None or node.marker_end is not None or node.pattern is not None for node in surface.primitives):
        raise ValueError("E_VISUAL_CAPABILITY_UNSUPPORTED")
    width, height = viewport
    parts = ["% chrona-tikz/v0.1", r"\documentclass{article}",
             f"\\usepackage[paperwidth={_number(width)}pt,paperheight={_number(height)}pt,margin=0pt]{{geometry}}",
             r"\usepackage{tikz}", r"\usepackage{fontspec}", *( [r"\usepackage{letterspace}"]
                                          if any(node.text_layout is not None and node.text_layout.letter_spacing
                                                 for node in surface.primitives) else []),
             r"\pagestyle{empty}", r"\begin{document}", r"\noindent",
             r"\begin{tikzpicture}[x=1pt,y=-1pt]",
             f"\\path[fill={surface.canvas_paint.fill}] (0,0) rectangle ({_number(width)},{_number(height)});"]
    for node in surface.primitives:
        x, y, w, h = node.bounds
        parts.append(f"% scene-id: {_tex_string(node.scene_id)} source-ref: {_tex_string(node.source_ref)}")
        if node.kind == "Rect":
            rounded = f", rounded corners={_number(node.corner_radius)}pt" if node.corner_radius else ""
            parts.append(f"\\path[{_tikz_rect_paint(node)}{rounded}] ({_number(x)},{_number(y)}) rectangle ({_number(x+w)},{_number(y+h)});")
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            layout = node.text_layout
            parts.append(f"% font-asset: {_tex_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = _tikz_tracked_text(layout, r"\\".join(_tex_string(line) for line in layout.lines))
            rotation = f", rotate={_number(layout.rotation_degrees)}" if layout.rotation_degrees else ""
            parts.append(f"\\node[anchor=base west, align=left{rotation}, text={_color(node, 'fill')}, text opacity={_number(_opacity(node))}, font=\\fontsize{{{_number(layout.font_size)}pt}}{{{_number(layout.font_size * layout.line_height)}pt}}\\selectfont] at ({_number(node.baseline[0])},{_number(node.baseline[1])}) {{{_tikz_numeric_text(layout, text)}}};")
        elif node.kind == "Symbol":
            if node.symbol is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
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
                        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                parts.append(f"\\path[fill={_color(node, 'fill')}{_tikz_opacity(node)}] {' '.join(commands)};")
                continue
        elif node.kind == "Path":
            if len(node.points) < 2:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
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
                        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                points = " ".join(commands)
            else:
                points = " -- ".join(f"({_number(px)},{_number(py)})" for px, py in node.points)
            parts.append(f"\\draw[draw={_color(node, 'stroke')}, opacity={_number(_opacity(node))}] {points};")
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    parts.extend((r"\end{tikzpicture}", r"\end{document}"))
    return "\n".join(parts) + "\n"


class V05TypstRenderer:
    target_kind = "typst"

    def render(self, surface: object, *, viewport: tuple[float, float]) -> RenderArtifact:
        checked_surface = _validate(surface)
        return RenderArtifact("typst", "application/x-typst", render_v05_typst(checked_surface, viewport=viewport).encode("utf-8"), "chrona-typst/v0.1")


class V05TikzRenderer:
    target_kind = "tikz"

    def render(self, surface: object, *, viewport: tuple[float, float]) -> RenderArtifact:
        checked_surface = _validate(surface)
        return RenderArtifact("tikz", "application/x-tex", render_v05_tikz(checked_surface, viewport=viewport).encode("utf-8"), "chrona-tikz/v0.1")
