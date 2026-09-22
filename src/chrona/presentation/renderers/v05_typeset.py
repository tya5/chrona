"""Positioned Typst and TikZ serialization of completed Scene surfaces."""
from __future__ import annotations

from chrona.core.ports import RenderArtifact
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _typst_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _tex_string(value: str) -> str:
    return (value.replace("\\", r"\textbackslash{}").replace("{", r"\{").replace("}", r"\}")
            .replace("#", r"\#").replace("$", r"\$").replace("%", r"\%").replace("&", r"\&")
            .replace("_", r"\_").replace("^", r"\textasciicircum{}").replace("~", r"\textasciitilde{}"))


def _color(tokens: ThemeTokenView, primitive: ScenePrimitive, property_name: str) -> str:
    return tokens.color(primitive.visual_role, property_name)


def _validate(surface: object, tokens: object) -> tuple[SceneSurface, ThemeTokenView]:
    if not isinstance(surface, SceneSurface) or not isinstance(tokens, ThemeTokenView):
        raise ValueError("E_PRESENTATION_RENDER_INPUT")
    return surface, tokens


def render_v05_typst(surface: SceneSurface, *, viewport: tuple[float, float], tokens: ThemeTokenView) -> str:
    width, height = viewport
    background = tokens.color("background", "fill")
    parts = ["// chrona-typst/v0.1", f"#set page(width: {_number(width)}pt, height: {_number(height)}pt, margin: 0pt)",
             f'#rect(width: {_number(width)}pt, height: {_number(height)}pt, fill: rgb("{background}"))']
    for node in surface.primitives:
        x, y, w, h = node.bounds
        parts.append(f"// scene-id: {_typst_string(node.scene_id)} source-ref: {_typst_string(node.source_ref)}")
        if node.kind == "Rect":
            parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[#rect(width: {_number(w)}pt, height: {_number(h)}pt, fill: rgb("{_color(tokens, node, "fill")}"))]')
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            layout = node.text_layout
            parts.append(f"// font-asset: {_typst_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = "\\n".join(_typst_string(line) for line in layout.lines)
            parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[#text(font: "{_typst_string(layout.family)}", weight: {layout.weight}, size: {_number(layout.font_size)}pt, fill: rgb("{_color(tokens, node, "fill")}"))[{text}]]')
        elif node.kind == "Symbol":
            if node.shape != "diamond":
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            parts.append(f'#place(left: {_number(x)}pt, top: {_number(y)}pt)[#rotate(45deg, rect(width: {_number(w)}pt, height: {_number(h)}pt, fill: rgb("{_color(tokens, node, "fill")}"))]')
        elif node.kind == "Path":
            if len(node.points) < 2:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            points = ", ".join(f"({_number(px)}pt, {_number(py)}pt)" for px, py in node.points)
            parts.append(f'// path points: {points} stroke: {_color(tokens, node, "stroke")}')
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    return "\n".join(parts) + "\n"


def render_v05_tikz(surface: SceneSurface, *, viewport: tuple[float, float], tokens: ThemeTokenView) -> str:
    width, height = viewport
    parts = ["% chrona-tikz/v0.1", r"\documentclass{article}",
             f"\\usepackage[paperwidth={_number(width)}pt,paperheight={_number(height)}pt,margin=0pt]{{geometry}}",
             r"\usepackage{tikz}", r"\pagestyle{empty}", r"\begin{document}", r"\noindent",
             r"\begin{tikzpicture}[x=1pt,y=-1pt]",
             f"\\path[fill={tokens.color('background', 'fill')}] (0,0) rectangle ({_number(width)},{_number(height)});"]
    for node in surface.primitives:
        x, y, w, h = node.bounds
        parts.append(f"% scene-id: {_tex_string(node.scene_id)} source-ref: {_tex_string(node.source_ref)}")
        if node.kind == "Rect":
            parts.append(f"\\path[fill={_color(tokens, node, 'fill')}] ({_number(x)},{_number(y)}) rectangle ({_number(x+w)},{_number(y+h)});")
        elif node.kind == "Text":
            if node.text is None or node.text_layout is None or node.baseline is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            layout = node.text_layout
            parts.append(f"% font-asset: {_tex_string(layout.asset_identity)} baseline: {_number(node.baseline[0])},{_number(node.baseline[1])}")
            text = r"\\".join(_tex_string(line) for line in layout.lines)
            parts.append(f"\\node[anchor=base west, align=left, text={_color(tokens, node, 'fill')}, font=\\fontsize{{{_number(layout.font_size)}pt}}{{{_number(layout.font_size * layout.line_height)}pt}}\\selectfont] at ({_number(node.baseline[0])},{_number(node.baseline[1])}) {{\\fontfamily{{{_tex_string(layout.family)}}}\\selectfont {text}}};")
        elif node.kind == "Symbol":
            if node.shape != "diamond":
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            parts.append(f"\\path[fill={_color(tokens, node, 'fill')}] ({_number(x+w/2)},{_number(y)}) -- ({_number(x+w)},{_number(y+h/2)}) -- ({_number(x+w/2)},{_number(y+h)}) -- ({_number(x)},{_number(y+h/2)}) -- cycle;")
        elif node.kind == "Path":
            if len(node.points) < 2:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            points = " -- ".join(f"({_number(px)},{_number(py)})" for px, py in node.points)
            parts.append(f"\\draw[draw={_color(tokens, node, 'stroke')}] {points};")
        else:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    parts.extend((r"\end{tikzpicture}", r"\end{document}"))
    return "\n".join(parts) + "\n"


class V05TypstRenderer:
    target_kind = "typst"

    def render(self, surface: object, *, viewport: tuple[float, float], tokens: object) -> RenderArtifact:
        checked_surface, checked_tokens = _validate(surface, tokens)
        return RenderArtifact("typst", "application/x-typst", render_v05_typst(checked_surface, viewport=viewport, tokens=checked_tokens).encode("utf-8"), "chrona-typst/v0.1")


class V05TikzRenderer:
    target_kind = "tikz"

    def render(self, surface: object, *, viewport: tuple[float, float], tokens: object) -> RenderArtifact:
        checked_surface, checked_tokens = _validate(surface, tokens)
        return RenderArtifact("tikz", "application/x-tex", render_v05_tikz(checked_surface, viewport=viewport, tokens=checked_tokens).encode("utf-8"), "chrona-tikz/v0.1")
