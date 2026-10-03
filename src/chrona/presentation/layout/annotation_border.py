"""Per-side box border of an annotation container: widths, mitred strips and the box chrome (#1049).

A Theme declares ``annotationContainer.border`` (``start|end|top|bottom`` -> width, paint).  This module is pure
Layout arithmetic.  The border lies on the outer edge of the paint box, each present side spans the full box side,
and the content inset is measured from the border's inner edge: ``insets`` are the four widths the caller adds to the
content insets, so the text origin, the kind frame's content box, the wrap bound and the box size (#1051's
``chrome``) all read one sum.  Corners are mitred as in CSS: each side is the trapezoid between the outer edge and
the padding edge; a side whose mitres are square (no bordered neighbour) is an axis-aligned ``Rect``, so a single bar
is one plain rectangle.  A ``paint: kind`` side is drawn from the kind accent role (the kind colour replaces its fill);
an ``ink`` side from the role ``annotation-border-<side>``.  ``side_strip`` is also the one strip geometry the
content-box kind accent uses.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from chrona.presentation.layout.annotation_tilt import bounding_rect, polygon_commands
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.rounded_outline import border_strip, commands_points
from chrona.presentation.layout.surface_quality import AnnotationPresentation, ShapePlacement
from chrona.presentation.model.theme_tokens import BORDER_SIDES, BorderSideToken, ThemeTokenView

KIND_INK_ROLE = "annotation-kind-accent"
INK_SEMANTICS = {"start": "annotationBorderStart", "end": "annotationBorderEnd",
                 "top": "annotationBorderTop", "bottom": "annotationBorderBottom"}
Point = tuple[float, float]


def side_strip(side: str, size: float, box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """The (x, y, width, height) of the full-length strip of ``size`` standing on ``side`` of ``box``."""
    x, y, width, height = box
    return {
        "start": (x, y, size, height), "end": (x + width - size, y, size, height),
        "top": (x, y, width, size), "bottom": (x, y + height - size, width, size),
    }[side]


@dataclass(frozen=True)
class BoxBorder:
    """The resolved widths (surface units) and paints of a box border; absent sides are 0."""

    start: float = 0.0
    end: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    paints: Mapping[str, str] | None = None

    @property
    def insets(self) -> tuple[float, float, float, float]:
        """(top, right, bottom, left): the space the border takes inside the box edge."""
        return self.top, self.end, self.bottom, self.start

    @property
    def empty(self) -> bool:
        return not (self.start or self.end or self.top or self.bottom)


NO_BORDER = BoxBorder()


def resolve_border(sides: Mapping[str, BorderSideToken] | None) -> BoxBorder:
    """The widths and paints of a container's declared border (a width of 0 is no border)."""
    if not sides:
        return NO_BORDER
    widths = {side: float(sides[side].width) if side in sides else 0.0 for side in BORDER_SIDES}
    return BoxBorder(widths["start"], widths["end"], widths["top"], widths["bottom"],
                     {side: sides[side].paint for side in sides if sides[side].width > 0})


def _polygons(border: BoxBorder, box: tuple[float, float, float, float]) -> dict[str, tuple[Point, ...]]:
    """The mitred trapezoid of each present side: outer edge on the box edge, mitres to the padding corners."""
    x, y, width, height = box
    right, bottom = x + width, y + height
    bl, br, bt, bb = border.start, border.end, border.top, border.bottom
    polygons = {
        "start": ((x, y), (x + bl, y + bt), (x + bl, bottom - bb), (x, bottom)),
        "end": ((right, y), (right, bottom), (right - br, bottom - bb), (right - br, y + bt)),
        "top": ((x, y), (right, y), (right - br, y + bt), (x + bl, y + bt)),
        "bottom": ((x, bottom), (x + bl, bottom - bb), (right - br, bottom - bb), (right, bottom)),
    }
    widths = {"start": bl, "end": br, "top": bt, "bottom": bb}
    return {side: points for side, points in polygons.items() if widths[side] > 0}


def _is_rectangle(points: tuple[Point, ...]) -> bool:
    xs, ys = {round(point[0], 9) for point in points}, {round(point[1], 9) for point in points}
    return len(xs) <= 2 and len(ys) <= 2


def place_border(border: BoxBorder, *, annotation_id: str, presentation: AnnotationPresentation,
                 box: tuple[float, float, float, float], theme_tokens: ThemeTokenView, paint_order: int,
                 radius: float = 0.0) -> tuple[ShapePlacement, ...]:
    """Complete one strip per bordered side of ``box`` (x, y, width, height), in start, end, top, bottom order.

    With a corner ``radius`` above 0 (#1087) every strip follows the rounded outline as a polygon of arcs.
    """
    shapes: list[ShapePlacement] = []
    paints = border.paints or {}
    widths = {"start": border.start, "end": border.end, "top": border.top, "bottom": border.bottom}
    for side, points in _polygons(border, box).items():
        kind_painted = paints.get(side) == "kind"
        role = KIND_INK_ROLE if kind_painted else f"annotation-border-{side}"
        if not theme_tokens.has_role(role):
            # A declared border with no ink role is a Theme conflict, never a silent omission.
            raise LayoutError("E_THEME_ROLE_REQUIRED", f"/body/roles/{role}")
        semantic_id = "annotationKindAccent" if kind_painted else INK_SEMANTICS[side]
        placement_id = f"annotation-border:{annotation_id}:{side}"
        if radius > 0:
            commands = border_strip(side, box, radius, widths)
            ends = commands_points(commands, samples=8)
            shapes.append(ShapePlacement(placement_id, annotation_id, "Polygon", bounding_rect(ends),
                                         path_commands=commands, semantic_id=semantic_id,
                                         annotation=presentation, paint_order=paint_order))
        elif _is_rectangle(points):
            left, top = min(p[0] for p in points), min(p[1] for p in points)
            w, h = max(p[0] for p in points) - left, max(p[1] for p in points) - top
            shapes.append(ShapePlacement(placement_id, annotation_id, "Rect",
                                         Rect(Decimal(str(left)), Decimal(str(top)), Decimal(str(w)), Decimal(str(h))),
                                         semantic_id=semantic_id, annotation=presentation, paint_order=paint_order))
        else:
            shapes.append(ShapePlacement(placement_id, annotation_id, "Polygon", bounding_rect(points),
                                         path_commands=polygon_commands(points), semantic_id=semantic_id,
                                         annotation=presentation, paint_order=paint_order))
    return tuple(shapes)
