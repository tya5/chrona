"""Private adapter placement of Layout-completed inline text runs.

SVG consumers may shape adjacent ``tspan`` elements as one run when font
fallback changes partway through a string. This helper uses only completed
Layout advances to make those boundaries explicit; it never resolves a face or
measures text. The public SVG is left alone.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lxml.etree import _Element as Element

from chrona.presentation.scene.model import SceneSurface

RASTER_TEXT_RUN_GRAMMAR = "resvg-completed-text-runs-v1"


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _invalid(detail: str) -> ValueError:
    return ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: completed SVG text runs: {detail}")


def position_completed_text_runs(element: Element, layout: object) -> None:
    """Project one completed TextLayout's runs to explicit x positions in its own frame."""
    lines = layout.runs
    if not lines:
        return
    x = float(element.get("x", layout.baseline[0]))
    scale = float(layout.horizontal_scale)
    if scale <= 0:
        raise _invalid(f"text {element.get('data-scene-id')!r} has invalid horizontal scale")

    # Preserve the attributes that the public SVG already put on each run,
    # including exact family/weight and private PDF aliases. Face choice is
    # completed upstream; this is only a geometry projection.
    original_runs = [dict(child.attrib) for child in element.iter()
                     if child is not element and child.tag.endswith("}tspan")
                     and len(child) == 0 and child.get("x") is None]
    run_offset = 0
    element.text = None
    for child in tuple(element):
        element.remove(child)
    namespace = element.tag.partition("}")[0] + "}" if "}" in element.tag else ""
    xml_space = "{http://www.w3.org/XML/1998/namespace}space"
    for line_index, runs in enumerate(lines):
        line = element.makeelement(namespace + "tspan", {})
        if len(lines) > 1:
            line.set("x", _number(x))
            line.set("dy", _number(0 if line_index == 0 else layout.font_size * layout.line_height))
            element.append(line)
        else:
            line = element
        advance = 0.0
        for run_index, run in enumerate(runs):
            position = x + (advance + run_index * layout.letter_spacing) / scale
            has_span = run.font_size != layout.font_size or any(
                getattr(run, name, None) is not None for name in ("family", "weight", "asset_identity"))
            attributes: dict[str, str] = {}
            if has_span:
                has_serialized_span = run_offset < len(original_runs)
                if has_serialized_span:
                    attributes.update(original_runs[run_offset])
                run_offset += 1
                # A serialized span may intentionally inherit a render-private
                # alias from its parent, so its attributes must remain exact.
                if not has_serialized_span:
                    if run.family is not None:
                        attributes["font-family"] = run.family
                    if run.weight is not None:
                        attributes["font-weight"] = str(run.weight)
                    if run.asset_identity is not None:
                        attributes["data-asset-identity"] = run.asset_identity
            attributes.update({"x": _number(position), "font-size": _number(run.font_size), xml_space: "preserve"})
            span = line.makeelement(namespace + "tspan", attributes)
            span.text = run.text
            line.append(span)
            advance += run.inline_size


def lower_png_text_runs(surface: SceneSurface, svg: bytes) -> bytes:
    """Place only fallback-face runs in a PNG-private SVG copy.

    No fallback face means no parsing or serialization, preserving the exact
    original bytes for ordinary Latin-only output.
    """
    layouts = {item.scene_id: item.text_layout for item in surface.primitives
               if item.kind == "Text" and item.text_layout is not None
               and any(getattr(run, "asset_identity", None) is not None
                       for line in item.text_layout.runs for run in line)}
    if not layouts:
        return svg
    try:
        from lxml import etree
    except ImportError as error:
        raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE: completed PNG text-run positioning requires lxml") from error
    root = etree.fromstring(svg)
    seen: set[str] = set()
    for element in tuple(root.iter()):
        if element.tag.rsplit("}", 1)[-1] != "text":
            continue
        scene_id = element.get("data-scene-id")
        layout = layouts.get(scene_id)
        if layout is None:
            continue
        position_completed_text_runs(element, layout)
        seen.add(scene_id)
    missing = sorted(set(layouts) - seen)
    if missing:
        raise _invalid(f"fallback-face text did not reach SVG serialization: sceneIds={missing!r}")
    return etree.tostring(root, encoding="utf-8")
