"""Owns deadline tick and run geometry; reads the View-shown deadlines, the completed planned marks and the Theme reach (#822)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.surface_quality import MarkPlacement, ShapePlacement
from chrona.presentation.model.projection import ReviewDeadline
from chrona.presentation.model.semantic_registry import semantic_binding

DEADLINE_SEMANTIC = "deadlineMark"
TICK_PREFIX = "deadline-tick:"
RUN_PREFIX = "deadline-run:"
# A planned mark folded into a group header has no row of its own to hold a tick (see `compose_deadline_marks`).
_FOLDED_PREFIX = "planned:group-header:"


@dataclass(frozen=True)
class DeadlineBatch:
    """Completed tick and run paths, in Project order and mark order, and the records of deadlines not drawn."""

    shapes: tuple[ShapePlacement, ...]
    diagnostics: tuple[str, ...]


def compose_deadline_marks(*, base: SurfaceBaseGeometry, theme_tokens: object, deadlines: tuple[ReviewDeadline, ...],
                           marks: tuple[MarkPlacement, ...], window: tuple[object, object],
                           paint_order_base: int) -> DeadlineBatch:
    """Complete a tick at each shown deadline's date and, for a slipped one, a run from it to the planned finish.

    Each deadline is anchored to the completed planned mark of its object, wherever its track put it: the tick is
    centred on that mark and spans the Theme's ``markReach`` times its block size, so a reach above 1 stands above
    and below the bar; the run is a line along the tick's lower end from the deadline to the finish, below the bar,
    so it never covers the bar's own paint. Both use the scale that places marks. A deadline outside the View window
    draws nothing and a deadline whose object is only a folded group-header point draws nothing; each is recorded,
    never silently dropped. Whether a deadline slipped is the Core's verdict, carried on ``ReviewDeadline``: nothing
    here compares two dates to judge lateness.
    """
    if not deadlines:
        return DeadlineBatch((), ())
    reach, order = theme_tokens.deadline_mark(semantic_binding(DEADLINE_SEMANTIC).theme_role)
    window_start, window_end = window
    plot = base.plot
    right_edge = float(plot.inline + plot.inline_size)
    planned: dict[str, list[MarkPlacement]] = {}
    folded: set[str] = set()
    for mark in marks:
        if mark.semantic_id != "planned":
            continue
        if mark.placement_id.startswith(_FOLDED_PREFIX):
            folded.add(mark.source_ref)
        else:
            planned.setdefault(mark.source_ref, []).append(mark)
    shapes: list[ShapePlacement] = []
    diagnostics: list[str] = []
    for deadline in deadlines:
        hosts = planned.get(deadline.object_id, [])
        if not hosts:
            if deadline.object_id in folded:
                diagnostics.append(f"I_LAYOUT_DEADLINE_FOLDED:{deadline.object_id}")
            continue
        if not window_start <= deadline.deadline <= window_end:
            diagnostics.append(f"I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:{deadline.object_id}")
            continue
        x = coordinate_for_date(deadline.deadline, base.scale)
        finish = min(coordinate_for_date(deadline.finish, base.scale), right_edge)
        for host in hosts:
            instance = host.placement_id.removeprefix("planned:")
            centre = float(host.bounds.block + host.bounds.block_size / 2)
            half = float(host.bounds.block_size) * float(reach) / 2
            top, bottom = centre - half, centre + half
            shapes.append(ShapePlacement(
                f"{TICK_PREFIX}{instance}", deadline.object_id, "Path",
                Rect(Decimal(str(x)), Decimal(str(top)), Decimal(0), Decimal(str(bottom - top))),
                ((x, top), (x, bottom)), slot_id=host.slot_id, paint_order=paint_order_base + order,
                semantic_id=DEADLINE_SEMANTIC, subjects=host.subjects))
            if deadline.slipped:
                shapes.append(ShapePlacement(
                    f"{RUN_PREFIX}{instance}", deadline.object_id, "Path",
                    Rect(Decimal(str(x)), Decimal(str(bottom)), Decimal(str(finish - x)), Decimal(0)),
                    ((x, bottom), (finish, bottom)), slot_id=host.slot_id, paint_order=paint_order_base + order,
                    semantic_id=DEADLINE_SEMANTIC, subjects=host.subjects))
    return DeadlineBatch(tuple(shapes), tuple(diagnostics))
