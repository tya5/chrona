"""Annotation kind frame geometry: header block, accent edge, title bar and stamp (#584).

Pure Layout composition for one annotation whose Project kind the Theme dresses.  `measure_kind_frame`
sizes the frame (the header block, the accent insets and the stamp column that grow the note box)
before the annotation search runs; `place_kind_frame` completes the accent Rect, the bar Rect, the stamp
glyph and the header text inside the box that search chose.  A Theme that declares nothing for the
kind measures to the empty frame, so the note's size, position and primitives are exactly what they
were without #584.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Callable

from chrona.presentation.annotation_kind_text import header_lines
from chrona.presentation.layout.mark_geometry import symbol_parts
from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_quality import (
    AnnotationPresentation, CollisionDomain, ShapePlacement, TextPlacement,
)
from chrona.presentation.layout.text import measure_text_width, place_text
from chrona.presentation.model.theme_tokens import (
    AnnotationKindFrame, AnnotationKindToken, ThemeTokenError, ThemeTokenView,
)

STAMP_GAP_EM = 0.5  # the space between a stamp and the note content, in note text sizes


@dataclass(frozen=True)
class KindHeaderLine:
    """One measured header line and the Theme text role that paints it."""

    content: str
    role: str
    font_size: float
    leading: float
    width: float


@dataclass(frozen=True)
class KindFrameMeasure:
    """The size the kind frame adds to the note box, in surface units."""

    lines: tuple[KindHeaderLine, ...]
    bar: bool
    bar_padding_inline: float
    bar_padding_block: float
    header_block: float
    header_inline: float
    inset_top: float
    inset_right: float
    inset_bottom: float
    inset_left: float
    accent_role: str | None
    accent_side: str | None
    accent_size: float
    bar_role: str | None
    stamp_ref: str | None = None
    stamp_corner: str | None = None
    stamp_inline: float = 0.0
    stamp_block: float = 0.0
    stamp_column: float = 0.0

    @property
    def stamp_at_start(self) -> bool:
        return self.stamp_corner is not None and self.stamp_corner.startswith("start")

    @property
    def inline_insets(self) -> float:
        return self.inset_left + self.inset_right + self.stamp_column

    @property
    def body_inset_left(self) -> float:
        """The inline start of the body text and the bar: past the accent and a start-side stamp column."""
        return self.inset_left + (self.stamp_column if self.stamp_at_start else 0.0)

    @property
    def block_insets(self) -> float:
        return self.inset_top + self.inset_bottom

    @property
    def empty(self) -> bool:
        return not self.lines and self.accent_role is None and self.stamp_ref is None


EMPTY_FRAME = KindFrameMeasure((), False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, None, 0.0, None)


def measure_kind_frame(*, kind: AnnotationKindToken | None, subject: str, frame: AnnotationKindFrame, subject_id: str = "",
                       theme_tokens: ThemeTokenView, metric_for: Callable[[str], Any],
                       outline: str | None, pointer: str, text_size: float = 0.0) -> KindFrameMeasure:
    """Measure the header block, accent insets and stamp column; raise when a strip cannot sit on this outline."""
    if kind is None:
        return EMPTY_FRAME
    lines: list[KindHeaderLine] = []
    if frame.label_role is not None:
        texts = header_lines(kind.header, subject=subject, subject_id=subject_id)
        for index, content in enumerate(texts):
            role = frame.label_role if index == 0 else frame.secondary_role
            if role is None:
                continue
            treatment = theme_tokens.text_treatment(role)
            size = float(treatment.font_size)
            width = measure_text_width(content, font_size=size, font_metrics=metric_for(role),
                                       letter_spacing=float(treatment.letter_spacing),
                                       text_transform=treatment.transform)
            lines.append(KindHeaderLine(content, role, size, float(treatment.line_height), width))
    bar = bool(lines) and frame.bar_role is not None
    has_accent = frame.accent_role is not None
    if (bar or has_accent) and outline in {"balloon", "image"}:
        # A straight strip at the box edge cannot follow a balloon or an image outline: a declaration
        # conflict, never a strip silently dropped.
        raise LayoutError("E_LAYOUT_ANNOTATION_KIND_FRAME_OUTLINE", pointer)
    stamp_ref = kind.stamp if frame.stamp_role is not None else None
    stamp_inline = stamp_block = stamp_column = 0.0
    if stamp_ref is not None:
        try:
            viewport = theme_tokens.catalog_glyph(stamp_ref)["viewport"]
            aspect = float(viewport["inlineSize"]) / float(viewport["blockSize"])
        except (ThemeTokenError, KeyError, TypeError, ValueError, ZeroDivisionError) as error:
            raise LayoutError("E_THEME_ASSET_REFERENCE", pointer) from error
        stamp_block = float(frame.stamp_size) * text_size
        stamp_inline = stamp_block * aspect
        stamp_column = stamp_inline + STAMP_GAP_EM * text_size
    if not lines and not has_accent and stamp_ref is None:
        return EMPTY_FRAME
    padding_inline = float(frame.bar_padding_em) * lines[0].font_size if bar else 0.0
    padding_block = padding_inline / 2
    header_block = (geometry_sum(line.font_size * line.leading for line in lines) + 2 * padding_block) if lines else 0.0
    header_inline = (max(line.width for line in lines) + 2 * padding_inline) if lines else 0.0
    size = float(frame.accent_size) if has_accent else 0.0
    side = frame.accent_side
    return KindFrameMeasure(
        tuple(lines), bar, padding_inline, padding_block, header_block, header_inline,
        size if side == "top" else 0.0, size if side == "end" else 0.0,
        size if side == "bottom" else 0.0, size if side == "start" else 0.0,
        frame.accent_role, side, size, frame.bar_role if bar else None,
        stamp_ref, frame.stamp_corner if stamp_ref is not None else None, stamp_inline, stamp_block, stamp_column)


def place_kind_frame(measure: KindFrameMeasure, *, annotation_id: str, presentation: AnnotationPresentation,
                     content_box: tuple[float, float, float, float], theme_tokens: ThemeTokenView,
                     font_metrics: Any, annotation_slot: str, paint_order: int
                     ) -> tuple[tuple[ShapePlacement, ...], tuple[TextPlacement, ...]]:
    """Complete the accent Rect, bar Rect, stamp glyph and header text inside ``content_box`` (x, y, width, height)."""
    x, y, width, height = content_box
    shapes: list[ShapePlacement] = []
    text: list[TextPlacement] = []

    def rect(placement_id: str, semantic_id: str, left: float, top: float, w: float, h: float) -> ShapePlacement:
        return ShapePlacement(placement_id, annotation_id, "Rect",
                              Rect(Decimal(str(left)), Decimal(str(top)), Decimal(str(w)), Decimal(str(h))),
                              semantic_id=semantic_id, annotation=presentation, paint_order=paint_order)

    if measure.accent_role is not None:
        side, size = measure.accent_side, measure.accent_size
        left, top, w, h = {
            "start": (x, y, size, height), "end": (x + width - size, y, size, height),
            "top": (x, y, width, size), "bottom": (x, y + height - size, width, size),
        }[str(side)]
        shapes.append(rect(f"annotation-kind-accent:{annotation_id}", "annotationKindAccent", left, top, w, h))
    inner_x = x + measure.body_inset_left
    inner_y = y + measure.inset_top
    inner_width = width - measure.inline_insets
    if measure.bar:
        shapes.append(rect(f"annotation-kind-bar:{annotation_id}", "annotationKindBar",
                           inner_x, inner_y, inner_width, measure.header_block))
    if measure.stamp_ref is not None:
        gap = measure.stamp_column - measure.stamp_inline
        stamp_x = (x + measure.inset_left if measure.stamp_at_start
                   else x + width - measure.inset_right - measure.stamp_column + gap)
        stamp_y = (y + measure.inset_top if str(measure.stamp_corner).endswith("top")
                   else y + height - measure.inset_bottom - measure.stamp_block)
        bounds = (stamp_x, stamp_y, measure.stamp_inline, measure.stamp_block)
        try:
            parts = symbol_parts({"shape": {"catalog": measure.stamp_ref}}, bounds,
                                 catalog_glyphs=theme_tokens.catalog_glyphs)
        except ValueError as error:
            raise LayoutError("E_THEME_ASSET_REFERENCE", f"/annotations/{annotation_id}") from error
        shapes.append(replace(rect(f"annotation-kind-stamp:{annotation_id}", "annotationKindStamp", *bounds),
                              kind="Glyph", symbol_parts=parts))
    line_top = inner_y + measure.bar_padding_block
    for index, line in enumerate(measure.lines):
        semantic_id = "annotationKindLabel" if index == 0 else "annotationKindSecondary"
        placed = place_text(placement_id=f"annotation-kind-text:{annotation_id}:{index}", source_ref=annotation_id,
                            content=line.content, inline=inner_x + measure.bar_padding_inline,
                            baseline_block=line_top + line.font_size, typography_role=line.role,
                            theme_tokens=theme_tokens, font_metrics=font_metrics,
                            collision_region="annotations", collision_domain=CollisionDomain(annotation_slot, "content"),
                            semantic_id=semantic_id, annotation=presentation)
        text.append(replace(placed, paint_order=paint_order + 1))
        line_top += line.font_size * line.leading
    return tuple(shapes), tuple(text)
