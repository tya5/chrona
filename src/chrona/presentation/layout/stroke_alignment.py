"""Complete opt-in contour-relative stroke geometry before Scene projection."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import (
    AlignedStrokePlacement, PathCommand, StrokeClip, is_closed_stroke_contour,
)
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.point_paint import resolve_point_paint_role


def complete_stroke_clip(*, alignment: str, bounds: tuple[float, float, float, float],
                         outline: tuple[PathCommand, ...] = (), stroke_width: float,
                         rectangle: bool = False, source: str = "/layout/stroke") -> StrokeClip | None:
    """Keep centre strokes unchanged; carry the exact contour and doubled stroke for clipping."""
    if alignment == "center":
        return None
    if alignment not in {"inside", "outside"}:
        raise LayoutError("E_LAYOUT_STROKE_ALIGNMENT_INVALID", source, "unknown alignment")
    if (isinstance(stroke_width, bool) or not isfinite(stroke_width) or stroke_width <= 0
            or not all(isfinite(value) for value in bounds) or min(bounds[2:]) <= 0):
        raise LayoutError("E_LAYOUT_STROKE_ALIGNMENT_INVALID", source, "nonpositive stroke or bounds")
    if not rectangle and not is_closed_stroke_contour(outline):
        raise LayoutError("E_LAYOUT_STROKE_ALIGNMENT_INVALID", source, "requires a closed nondegenerate contour")
    x, y, width, height = bounds
    # Miter limit 4 bounds a doubled stroke's join by four logical widths.
    # Include command controls when a tilted/compound contour exceeds its box.
    points = [point for command in outline for point in command.points]
    left = min([x, *(px for px, _ in points)])
    top = min([y, *(py for _, py in points)])
    right = max([x + width, *(px for px, _ in points)])
    bottom = max([y + height, *(py for _, py in points)])
    margin = 4 * stroke_width
    return StrokeClip(() if rectangle else outline, alignment == "outside",
                      (left - margin, top - margin, right - left + 2 * margin, bottom - top + 2 * margin),
                      2 * stroke_width)


def complete_aligned_strokes(marks: tuple[Any, ...], shapes: tuple[Any, ...],
                             lane_emissions: tuple[Any, ...], tokens: Any) -> tuple[AlignedStrokePlacement, ...]:
    """Bind each completed clip to the exact primitive identity, including glyph and lane parts."""
    choice = getattr(tokens, "optional_choice", None)
    if choice is None:
        return ()
    identities = {(entry.placement_type, entry.placement_id): entry for entry in lane_emissions}
    result = []
    for kind, values in (("mark", marks), ("shape", shapes)):
        for placed in values:
            legend = placed.placement_id.startswith("legend-swatch:")
            if legend:
                role = semantic_binding("scaleLegendEntry").theme_role if placed.source_ref.startswith("scale:") else placed.source_ref
                role = resolve_point_paint_role(role, gate_declared=tokens.has_role("gate"), legend=True)
            elif kind == "mark":
                # MarkPlacement carries the mark geometry's Theme role name
                # (including missing-actual), not a semantic-registry key.
                role = placed.semantic_id
                if placed.mark_shape == "point":
                    role = resolve_point_paint_role(role, gate_declared=tokens.has_role("gate"))
            elif placed.visual_role:
                role = placed.visual_role
            elif placed.semantic_id:
                role = semantic_binding(placed.semantic_id).theme_role
            else:
                continue
            alignment = choice(role, "strokeAlign", ("inside", "center", "outside"))
            if alignment is None or alignment == "center":
                continue
            source = f"/body/roles/{role}/strokeAlign"
            pattern = tokens.optional_pattern(role)
            outlined = isinstance(pattern, Mapping) and pattern.get("kind") == "outline"
            if (tokens.optional_number(role, "wobbleAmplitude") is not None
                    or choice(role, "viewerFit", ("raw", "text-follows-box", "box-follows-text")) == "box-follows-text"):
                raise LayoutError("E_LAYOUT_STROKE_ALIGNMENT_INVALID", source, "incompatible contour treatment")
            bounds = tuple(float(value) for value in (placed.bounds.inline, placed.bounds.block,
                                                      placed.bounds.inline_size, placed.bounds.block_size))
            parts = placed.symbol_parts
            emission = identities.get((kind, placed.placement_id))
            if emission is not None:
                ids = tuple(dict.fromkeys(facet.primitive_id for facet in sorted(
                    emission.facets, key=lambda facet: -1 if facet.part_index is None else facet.part_index)))
            else:
                ids = tuple(f"{placed.placement_id}:part{index}" if part.paint_mode is not None else placed.placement_id
                            for index, part in enumerate(parts)) if parts else (placed.placement_id,)
            if len(ids) != len(parts or (None,)):
                raise LayoutError("E_LAYOUT_STROKE_ALIGNMENT_INVALID", source, "incomplete contour identities")
            for index, part in enumerate(parts or (None,)):
                if part is not None and part.paint_mode == "fill" and not outlined:
                    continue
                width = (part.stroke_width if not outlined and part is not None and part.stroke_width is not None
                         else tokens.optional_number(role, "strokeWidth"))
                if width is None or (part is None and tokens.optional_color(role, "stroke") is None):
                    continue  # A fill-only contour has no stroke to align.
                rectangle = part is None and not placed.path_commands and not placed.points if kind == "shape" else (
                    part is None and placed.mark_shape == "span" and not placed.path_commands)
                commands = part.commands if part is not None else placed.path_commands
                if kind == "mark" and placed.end_treatment != "closed":
                    raise LayoutError("E_LAYOUT_STROKE_ALIGNMENT_INVALID", source, "requires a closed span")
                clip = complete_stroke_clip(alignment=alignment, bounds=bounds, outline=commands,
                                            stroke_width=float(width), rectangle=rectangle, source=source)
                result.append(AlignedStrokePlacement(ids[index], clip))
    return tuple(result)
