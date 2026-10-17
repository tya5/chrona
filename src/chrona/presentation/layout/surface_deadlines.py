"""Owns deadline tick and run geometry; reads the View-shown deadlines, the completed planned marks and the Theme reach (#822)."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Callable

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.deadline_captions import DeadlineCaptionAnchor
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.surface_quality import MarkPlacement, ShapePlacement
from chrona.presentation.model.projection import ReviewDeadline
from chrona.presentation.model.semantic_registry import semantic_binding

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_base import SurfaceBaseGeometry

DEADLINE_SEMANTIC = "deadlineMark"
TICK_PREFIX = "deadline-tick:"
RUN_PREFIX = "deadline-run:"


def _outline(shape: ShapePlacement, margin: float) -> ShapePlacement | None:
    """Complete a filled ground around a straight stroke, including its caps."""
    if shape.points[0] == shape.points[-1]:
        return None  # A zero-length butt stroke has no painted area to outline.
    xs, ys = zip(*shape.points)
    return replace(shape, placement_id=shape.placement_id + ":outline", kind="Rect",
                   bounds=Rect(Decimal(str(min(xs) - margin)), Decimal(str(min(ys) - margin)),
                               Decimal(str(max(xs) - min(xs) + 2 * margin)),
                               Decimal(str(max(ys) - min(ys) + 2 * margin))),
                   points=(), paint_order=shape.paint_order - 1, semantic_id="deadlineMarkOutline")


@dataclass(frozen=True)
class DeadlineBatch:
    """Completed tick and run paths, in Project order and mark order, and the records of deadlines not drawn."""

    shapes: tuple[ShapePlacement, ...]
    diagnostics: tuple[str, ...]
    captions: tuple[DeadlineCaptionAnchor, ...] = ()


@dataclass(frozen=True)
class DeadlineHostGeometry:
    """One host's completed deadline ink and maximum painted envelope."""

    shapes: tuple[ShapePlacement, ...]
    outlines: tuple[ShapePlacement, ...]
    caption: DeadlineCaptionAnchor | None
    painted_bounds: Rect | None


@dataclass(frozen=True)
class DeadlineInkStyle:
    """Shared Theme-owned deadline stroke envelope used by both surface owners."""

    reach: Decimal
    paint_order: int
    stroke_width: Decimal
    outline_width: Decimal
    wobble_amplitude: Decimal

    @property
    def margin(self) -> float:
        return (float(self.stroke_width) / 2 + float(self.outline_width) + float(self.wobble_amplitude)
                if self.stroke_width > 0 else 0.0)


@dataclass(frozen=True)
class DeadlineInkGeometry:
    """Maximum painted envelope and optional opaque grounds for completed deadline strokes."""

    outlines: tuple[ShapePlacement, ...]
    painted_bounds: Rect | None


def deadline_ink_style(theme_tokens: object, role: str = "deadline-mark") -> DeadlineInkStyle:
    """Close shared reach/order/stroke/outline/wobble facts for deadline ink."""
    reach, order = theme_tokens.deadline_mark(role)
    stroke_width = theme_tokens.number(role, "strokeWidth")
    outline_width = theme_tokens.deadline_outline_width(role)
    wobble = theme_tokens.wobble_intent(role)
    amplitude = wobble.amplitude if wobble is not None else Decimal(0)
    return DeadlineInkStyle(reach, order, stroke_width, outline_width, amplitude)


def complete_deadline_ink(shapes: tuple[ShapePlacement, ...], style: DeadlineInkStyle, *,
                          outline_placement_id: Callable[[ShapePlacement], str] | None = None) -> DeadlineInkGeometry:
    """Complete the common stroke envelope and per-segment opaque outline grounds."""
    margin = style.margin
    outline_id = outline_placement_id or (lambda shape: shape.placement_id + ":outline")
    outlines = tuple(
        replace(ground, placement_id=outline_id(shape))
        for shape in shapes
        if style.outline_width > 0 and style.stroke_width > 0
        and (ground := _outline(shape, margin)) is not None
    )
    painted = None
    if shapes and style.stroke_width > 0:
        bounds = [shape.bounds for shape in shapes]
        left = min(float(bound.inline) for bound in bounds) - margin
        top_bound = min(float(bound.block) for bound in bounds) - margin
        right = max(float(bound.inline + bound.inline_size) for bound in bounds) + margin
        bottom_bound = max(float(bound.block + bound.block_size) for bound in bounds) + margin
        painted = Rect(Decimal(str(left)), Decimal(str(top_bound)),
                       Decimal(str(right - left)), Decimal(str(bottom_bound - top_bound)))
    return DeadlineInkGeometry(outlines, painted)


def complete_deadline_host(*, base: SurfaceBaseGeometry, theme_tokens: object,
                           deadline: ReviewDeadline, host: MarkPlacement,
                           paint_order_base: int) -> DeadlineHostGeometry:
    """Complete one host through the shared final-paint/folded-packing path."""
    style = deadline_ink_style(theme_tokens, semantic_binding(DEADLINE_SEMANTIC).theme_role)
    reach, order = style.reach, style.paint_order
    margin = style.margin
    right_edge = float(base.plot.inline + base.plot.inline_size)
    x = coordinate_for_date(deadline.deadline, base.scale)
    finish = min(coordinate_for_date(deadline.finish, base.scale), right_edge)
    instance = host.placement_id.removeprefix("planned:")
    centre = float(host.bounds.block + host.bounds.block_size / 2)
    half = float(host.bounds.block_size) * float(reach) / 2
    top, bottom = centre - half, centre + half
    shapes = [ShapePlacement(
        f"{TICK_PREFIX}{instance}", deadline.object_id, "Path",
        Rect(Decimal(str(x)), Decimal(str(top)), Decimal(0), Decimal(str(bottom - top))),
        ((x, top), (x, bottom)), slot_id=host.slot_id, paint_order=paint_order_base + order,
        semantic_id=DEADLINE_SEMANTIC, subjects=host.subjects)]
    caption = None
    if deadline.slipped:
        shapes.append(ShapePlacement(
            f"{RUN_PREFIX}{instance}", deadline.object_id, "Path",
            Rect(Decimal(str(x)), Decimal(str(bottom)), Decimal(str(finish - x)), Decimal(0)),
            ((x, bottom), (finish, bottom)), slot_id=host.slot_id, paint_order=paint_order_base + order,
            semantic_id=DEADLINE_SEMANTIC, subjects=host.subjects))
        if deadline.caption is not None:
            caption = DeadlineCaptionAnchor(
                f"deadline-caption:{instance}", deadline.object_id, host.placement_id,
                deadline.caption, x, finish, bottom, margin, host.subjects)
    ink = complete_deadline_ink(tuple(shapes), style)
    return DeadlineHostGeometry(tuple(shapes), ink.outlines, caption, ink.painted_bounds)


def compose_deadline_marks(*, base: SurfaceBaseGeometry, theme_tokens: object, deadlines: tuple[ReviewDeadline, ...],
                           marks: tuple[MarkPlacement, ...], window: tuple[object, object],
                           paint_order_base: int) -> DeadlineBatch:
    """Complete a tick at each shown deadline's date and, for a slipped one, a run from it to the planned finish.

    Each deadline is anchored to the completed planned mark of its object, wherever its track put it: the tick is
    centred on that mark and spans the Theme's ``markReach`` times its block size, so a reach above 1 stands above
    and below the bar; the run is a line along the tick's lower end from the deadline to the finish, below the bar,
    so it never covers the bar's own paint. Both use the scale that places marks. A deadline outside the View window
    draws nothing and is recorded, never silently dropped. Whether a deadline slipped is the Core's verdict, carried on ``ReviewDeadline``: nothing
    here compares two dates to judge lateness.
    """
    if not deadlines:
        return DeadlineBatch((), ())
    window_start, window_end = window
    planned: dict[str, list[MarkPlacement]] = {}
    for mark in marks:
        if mark.semantic_id not in {"planned", "forecast"}:
            continue
        planned.setdefault(mark.source_ref, []).append(mark)
    shapes: list[ShapePlacement] = []
    outlines: list[ShapePlacement] = []
    diagnostics: list[str] = []
    captions: list[DeadlineCaptionAnchor] = []
    for deadline in deadlines:
        hosts = planned.get(deadline.object_id, [])
        if not hosts:
            continue
        if not window_start <= deadline.deadline <= window_end:
            diagnostics.append(f"I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:{deadline.object_id}")
            continue
        for host in hosts:
            geometry = complete_deadline_host(
                base=base, theme_tokens=theme_tokens, deadline=deadline, host=host,
                paint_order_base=paint_order_base)
            shapes.extend(geometry.shapes)
            outlines.extend(geometry.outlines)
            if geometry.caption is not None:
                captions.append(geometry.caption)
    return DeadlineBatch(tuple((*outlines, *shapes)), tuple(diagnostics), tuple(captions))
