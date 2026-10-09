"""Owns completed Layout visual geometry; reads resolved requests and Theme metrics only."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Mapping

from chrona.presentation.layout.label_visual_measurement import (
    resolve_label_visual_advances, visual_target_placement_id,
)
from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_geometry import HOSTED_TEXT_PAINT_ORDER
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject, table_row_subjects
from chrona.presentation.layout.surface_quality import (
    FitWarning, IconPlacement, MarkPlacement, ShapePlacement, SurfaceLayoutRequest,
    TextPlacement,
)
from chrona.presentation.layout.text import (
    ellipsize_text, measure_text_width, metric_for_family, paint_text, wrap_text,
)


@dataclass(frozen=True)
class TextVisualReservation:
    """Resolved icon budget for a text run before candidate placement."""
    resolved: Mapping[str, tuple[Any, float, float]]
    leading: float
    trailing: float


@dataclass(frozen=True)
class SurfaceTextVisuals:
    text: tuple[TextPlacement, ...]
    icons: tuple[IconPlacement, ...]
    warnings: tuple[FitWarning, ...]


@dataclass(frozen=True)
class SurfaceMarkVisuals:
    icons: tuple[IconPlacement, ...]


@dataclass(frozen=True)
class SurfaceAxisBandVisuals:
    icons: tuple[IconPlacement, ...]


@dataclass(frozen=True)
class CandidateVisualAdvances:
    visuals: tuple[tuple[Any, Any, float, float], ...]

    @property
    def leading(self) -> float:
        return geometry_sum(width + gap for visual, _, width, gap in self.visuals if visual.side == "leading")

    @property
    def trailing(self) -> float:
        return geometry_sum(width + gap for visual, _, width, gap in self.visuals if visual.side == "trailing")


def reserve_text_visuals(*, typography_role: str, font_size: float,
                         visuals: Mapping[str, Any],
                         request: SurfaceLayoutRequest) -> TextVisualReservation:
    """Resolve one text run's icon inline budget before its text is measured."""
    resolved: dict[str, tuple[Any, float, float]] = {}
    for side, visual in visuals.items():
        icon = request.icon_assets.get(visual.ref)
        if icon is None:
            raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
        try:
            scale, gap_ratio = request.theme_tokens.icon_ratios(typography_role)
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = font_size * float(scale)
        if height <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        if icon.viewport[1] <= 0:
            raise LayoutError("E_ICON_IMPORT_VIEWPORT", visual.source_ref)
        resolved[side] = (icon, height * icon.viewport[0] / icon.viewport[1],
                          font_size * float(gap_ratio))
    leading = geometry_sum(width + gap for side, (_, width, gap) in resolved.items()
                           if side == "leading")
    trailing = geometry_sum(width + gap for side, (_, width, gap) in resolved.items()
                            if side == "trailing")
    return TextVisualReservation(resolved, leading, trailing)


def place_text_visuals(text: tuple[TextPlacement, ...], request: SurfaceLayoutRequest, *,
                       handled_sources: set[str] | None = None,
                       axis_label_targets: Mapping[tuple[str, str, str], str] | None = None,
                       pre_reserved_placements: frozenset[str] = frozenset()) -> SurfaceTextVisuals:
    """Complete text and hosted icon geometry without depending on Scene or catalog."""
    handled_sources = handled_sources or set()
    placed_text = list(text)
    requested: dict[str, dict[str, Any]] = {}
    occupied: set[tuple[str, str]] = set()
    for visual in request.visual_requests:
        if visual.target_kind == "mark" or visual.source_ref in handled_sources:
            continue
        selector = dict(visual.selector)
        if visual.target_kind == "axis-band":
            continue
        axis_key = (visual.target_kind, selector.get("level", ""), selector.get("index", ""))
        placement_id = (selector.get("placementId") or (axis_label_targets or {}).get(axis_key)
                        or visual_target_placement_id(visual.target_kind, selector))
        key = (placement_id, visual.side)
        if key in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(key)
        if visual.ref is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", visual.source_ref)
        requested.setdefault(placement_id, {})[visual.side] = visual
    icons: list[IconPlacement] = []
    warnings: list[FitWarning] = []
    surface_content = getattr(request, "surface_content", None)
    table_object_ids = {cell.object_id for cell in getattr(surface_content, "table_cells", ())}
    projection = getattr(request, "projection", None)
    project_items = {str(item.object_id): item for item in getattr(projection, "items", ())}
    declared_rows = getattr(projection, "rows", ())
    cell_subjects = (table_row_subjects(declared_rows) if declared_rows else {
        key: DiagnosticSubject.project_object(key, getattr(item, "title", None))
        for key, item in project_items.items()
    })

    def text_subjects(item: TextPlacement) -> tuple[DiagnosticSubject, ...]:
        # TableCellContent identifies a declared row, whose table subject owns
        # the cell. Generic text and lane-level cells do not prove an object.
        if item.source_ref not in table_object_ids or item.source_ref not in cell_subjects:
            return ()
        return (cell_subjects[item.source_ref],)
    for placement_id, by_side in requested.items():
        matches = [item for item in placed_text if item.placement_id == placement_id
                   and item.overflow != "suppressed"]
        if len(matches) != 1:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(by_side.values())).source_ref)
    for index, item in enumerate(placed_text):
        by_side = requested.pop(item.placement_id, None)
        if not by_side or item.overflow == "suppressed":
            continue
        item_metrics = metric_for_family(item.font_family, item.font_weight, request.font_metrics,
                                        item.horizontal_scale)
        reservation = reserve_text_visuals(typography_role=item.typography_role,
                                           font_size=item.font_size, visuals=by_side,
                                           request=request)
        resolved, leading, trailing = reservation.resolved, reservation.leading, reservation.trailing
        allocated = (item.available_inline_size if item.available_inline_size is not None
                     else float(item.bounds.inline_size))
        available = allocated - leading - trailing
        source = item.source_content if item.source_content is not None else item.content
        natural_lines = (item.lines if item.source_content is None and len(item.lines) > 1
                         else (source,))
        if item.placement_id in pre_reserved_placements:
            lines, content, overflow = item.lines, item.content, item.overflow
        elif available <= 0:
            lines, content, overflow = natural_lines, "\n".join(natural_lines), "visible-overflow"
        elif len(item.lines) > 1:
            lines = wrap_text(source, available_inline=available, font_size=item.font_size,
                              font_metrics=item_metrics, letter_spacing=item.letter_spacing,
                              text_transform=item.text_transform, numeric_spacing=item.numeric_spacing)
            content, overflow = "\n".join(lines), item.overflow
        elif item.source_content is not None:
            ellipsis_width = measure_text_width("…", font_size=item.font_size,
                font_metrics=item_metrics, letter_spacing=item.letter_spacing,
                text_transform=item.text_transform, numeric_spacing=item.numeric_spacing)
            if available < ellipsis_width:
                lines, content, overflow = (source,), source, "visible-overflow"
            else:
                content = ellipsize_text(source, available_inline=available,
                    font_size=item.font_size, font_metrics=item_metrics,
                    letter_spacing=item.letter_spacing, text_transform=item.text_transform,
                    numeric_spacing=item.numeric_spacing)
                lines, overflow = (content,), "ellipsized" if content != source else "fit"
        elif measure_text_width(source, font_size=item.font_size, font_metrics=item_metrics,
                                letter_spacing=item.letter_spacing,
                                text_transform=item.text_transform,
                                numeric_spacing=item.numeric_spacing) <= available:
            content, lines, overflow = source, (source,), item.overflow
        else:
            lines, content, overflow = (source,), source, "visible-overflow"
        width = max(measure_text_width(line, font_size=item.font_size,
            font_metrics=item_metrics, letter_spacing=item.letter_spacing,
            text_transform=item.text_transform, numeric_spacing=item.numeric_spacing) for line in lines)
        if width > available:
            overflow = "visible-overflow"
            if item.placement_id not in pre_reserved_placements:
                warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id,
                    item.source_ref, "text-visual", "visible-overflow", leading + width + trailing,
                    float(item.bounds.block_size), max(0.0, allocated), float(item.bounds.block_size),
                    subjects=text_subjects(item)))
        baseline = item.baseline
        if baseline is None or not hasattr(item_metrics, "cap_height_at"):
            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(iter(by_side.values())).source_ref)
        available_start = (item.available_inline_start if item.available_inline_start is not None
                           else float(item.bounds.inline))
        shifted_baseline = (available_start + leading, baseline[1])
        painted_lines = tuple(paint_text(line, text_transform=item.text_transform) for line in lines)
        placed_text[index] = replace(item, content=paint_text(content, text_transform=item.text_transform),
            lines=painted_lines, overflow=overflow,
            bounds=Rect(Decimal(str(shifted_baseline[0])), item.bounds.block,
                        Decimal(str(width)), Decimal(str(item.font_size * item.line_height * len(lines)))),
            baseline=shifted_baseline)
        cap_height = float(item_metrics.cap_height_at(item.font_size))
        for side, visual in by_side.items():
            icon, icon_width, gap = resolved[side]
            inline = (available_start if side == "leading" else
                      available_start + leading + max(available, width) + trailing - gap - icon_width)
            icon_height = item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0])
            bounds = Rect(Decimal(str(inline)), Decimal(str(baseline[1] - cap_height +
                (cap_height - icon_height) / 2)), Decimal(str(icon_width)), Decimal(str(icon_height)))
            icons.append(IconPlacement(f"visual:{item.placement_id}:{side}", item.source_ref,
                visual.source_ref, icon.icon_id, icon.kind, icon.content_identity, icon.viewport,
                icon.payload, icon.alternative, visual.decorative, bounds, "labelVisual",
                icon_width / icon.viewport[0], item.slot_id, paint_order=item.paint_order,
                lane_row_id=item.lane_row_id, lane_member_id=item.lane_member_id,
                host_placement_id=item.placement_id, subjects=text_subjects(item)))
    if requested:
        raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(next(iter(requested.values())).values())).source_ref)
    return SurfaceTextVisuals(tuple(placed_text), tuple(icons), tuple(warnings))


def place_mark_visuals(marks: tuple[MarkPlacement, ...],
                       request: SurfaceLayoutRequest) -> SurfaceMarkVisuals:
    """Place mark-targeted icons on exactly one completed mark."""
    icons: list[IconPlacement] = []
    occupied: set[str] = set()
    for visual in request.visual_requests:
        if visual.target_kind != "mark":
            continue
        selector = dict(visual.selector)
        placement_id = selector.get("placementId") or visual_target_placement_id("mark", selector)
        if placement_id in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(placement_id)
        mark = [item for item in marks if item.placement_id == placement_id or
                ("placementId" not in selector and item.placement_id.startswith(placement_id + ":"))]
        icon = request.icon_assets.get(visual.ref or "")
        if len(mark) != 1 or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if len(mark) != 1 else "E_ICON_NAME_UNKNOWN",
                              visual.source_ref)
        host = mark[0]
        try:
            scale, _ = request.theme_tokens.icon_ratios("icon-mark")
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = float(host.bounds.block_size) * float(scale)
        if height <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        width = min(float(host.bounds.inline_size), height * icon.viewport[0] / icon.viewport[1])
        bounds = Rect(host.bounds.inline + (host.bounds.inline_size - Decimal(str(width))) / 2,
                      host.bounds.block + (host.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        icons.append(IconPlacement(f"visual:{host.placement_id}", host.source_ref, visual.source_ref,
            icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload,
            icon.alternative, visual.decorative, bounds, "iconMark", width / icon.viewport[0],
            host.slot_id, paint_order=host.paint_order + 1, lane_row_id=host.lane_row_id,
            lane_member_id=host.lane_member_id, host_placement_id=host.placement_id,
            subjects=host.subjects))
    return SurfaceMarkVisuals(tuple(icons))


def place_axis_band_visuals(shapes: tuple[ShapePlacement, ...], request: SurfaceLayoutRequest, *,
                            targets: Mapping[tuple[str, str, str], str]) -> SurfaceAxisBandVisuals:
    """Place band icons from completed typed axis target identities."""
    icons: list[IconPlacement] = []
    for visual in request.visual_requests:
        if visual.target_kind != "axis-band":
            continue
        selector = dict(visual.selector)
        placement_id = targets.get(("axis-band", selector.get("level", ""), selector.get("index", "")))
        shape = next((item for item in shapes if item.placement_id == placement_id), None)
        icon = request.icon_assets.get(visual.ref or "")
        if shape is None or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if shape is None else "E_ICON_NAME_UNKNOWN",
                              visual.source_ref)
        scale, _ = request.theme_tokens.icon_ratios("icon-mark")
        height = min(float(shape.bounds.inline_size), float(shape.bounds.block_size)) * float(scale)
        if height <= 0 or icon.viewport[1] <= 0:
            raise LayoutError("E_THEME_ICON_RATIO" if height <= 0 else "E_ICON_IMPORT_VIEWPORT",
                              visual.source_ref)
        width = height * icon.viewport[0] / icon.viewport[1]
        bounds = Rect(shape.bounds.inline + (shape.bounds.inline_size - Decimal(str(width))) / 2,
                      shape.bounds.block + (shape.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        icons.append(IconPlacement(f"visual:{shape.placement_id}", shape.source_ref,
            visual.source_ref, icon.icon_id, icon.kind, icon.content_identity, icon.viewport,
            icon.payload, icon.alternative, visual.decorative, bounds, "iconMark",
            width / icon.viewport[0], shape.slot_id, paint_order=HOSTED_TEXT_PAINT_ORDER))
    return SurfaceAxisBandVisuals(tuple(icons))


def measure_candidate_visuals(placement_id: str, typography_role: str,
                              request: SurfaceLayoutRequest) -> CandidateVisualAdvances:
    """Reserve icon advances before candidate-label placement."""
    visuals = resolve_label_visual_advances(placement_id, typography_role,
        visual_requests=request.visual_requests, icon_assets=request.icon_assets,
        theme_tokens=request.theme_tokens)
    return CandidateVisualAdvances(visuals)
