"""Annotation kind frame geometry: header block, title bar and stamp (#584).

Pure Layout composition for one annotation whose Project kind the Theme dresses.  `measure_kind_frame`
sizes the frame (the header block and the stamp column that grow the note box)
before the annotation search runs; `place_kind_frame` completes the bar Rect, the stamp
glyph and the header text inside the box that search chose.  A Theme that declares nothing for the
kind measures to the empty frame, so the note's size, position and primitives are exactly what they
were without #584.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Callable

from chrona.presentation.annotation_kind_text import header_lines, heading_text
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
    bar_role: str | None
    stamp_ref: str | None = None
    stamp_corner: str | None = None
    stamp_inline: float = 0.0
    stamp_block: float = 0.0
    stamp_column: float = 0.0
    heading: KindHeaderLine | None = None
    bar_block: float = 0.0
    bar_inline: float = 0.0
    bar_width: str = "fill"
    bar_bleed: str = "none"
    stamp_placement: str = "column"

    @property
    def stamp_at_start(self) -> bool:
        return self.stamp_corner is not None and self.stamp_corner.startswith("start")

    @property
    def inline_insets(self) -> float:
        return self.stamp_column

    @property
    def body_inset_left(self) -> float:
        """The body and bar start after a start-side stamp column."""
        return self.stamp_column if self.stamp_at_start else 0.0

    @property
    def empty(self) -> bool:
        return not self.lines and self.heading is None and self.stamp_ref is None


EMPTY_FRAME = KindFrameMeasure((), False, 0.0, 0.0, 0.0, 0.0, None)


def measure_kind_frame(*, kind: AnnotationKindToken | None, subject: str, frame: AnnotationKindFrame, subject_id: str = "",
                       theme_tokens: ThemeTokenView, metric_for: Callable[[str], Any],
                       outline: str | None, pointer: str, text_size: float = 0.0,
                       header_texts: tuple[str, ...] | None = None,
                       heading_content: str | None = None) -> KindFrameMeasure:
    """Measure the header and stamp; reject a title bar on an unsupported outline."""
    if kind is None:
        return EMPTY_FRAME
    lines: list[KindHeaderLine] = []
    if frame.label_role is not None:
        texts = header_texts if header_texts is not None else header_lines(kind.header, subject=subject, subject_id=subject_id)
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
    if bar and outline in {"balloon", "image"}:
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
        if frame.stamp_placement == "column":
            stamp_column = stamp_inline + STAMP_GAP_EM * text_size
        elif not bar:
            raise LayoutError("E_LAYOUT_ANNOTATION_KIND_STAMP_PLACEMENT", pointer,
                              detail="bar-end stamp placement requires a drawable annotation-kind label bar")
    heading = None
    content = (heading_content if header_texts is not None
               else heading_text(kind.header, subject=subject, subject_id=subject_id))
    if content is not None:
        role = frame.heading_role
        if role is None:
            raise LayoutError("E_THEME_ROLE_REQUIRED", "/body/roles/annotation-heading")
        treatment = theme_tokens.text_treatment(role)
        size = float(treatment.font_size)
        heading = KindHeaderLine(content, role, size, float(treatment.line_height),
                                 measure_text_width(content, font_size=size, font_metrics=metric_for(role),
                                                    letter_spacing=float(treatment.letter_spacing),
                                                    text_transform=treatment.transform))
    if not lines and heading is None and stamp_ref is None:
        return EMPTY_FRAME
    padding_inline = float(frame.bar_padding_em) * lines[0].font_size if bar else 0.0
    padding_block = padding_inline / 2
    bar_block = (geometry_sum(line.font_size * line.leading for line in lines) + 2 * padding_block) if lines else 0.0
    bar_inline = (max(line.width for line in lines) + 2 * padding_inline) if lines else 0.0
    if stamp_ref is not None and frame.stamp_placement == "bar-end":
        # This reserve belongs to the bar, never to the note's body/heading column.
        bar_inline += stamp_inline + STAMP_GAP_EM * text_size
        bar_block = max(bar_block, stamp_block)
    header_block = bar_block + (heading.font_size * heading.leading if heading is not None else 0.0)
    header_inline = max(bar_inline, heading.width if heading is not None else 0.0)
    return KindFrameMeasure(
        tuple(lines), bar, padding_inline, padding_block, header_block, header_inline,
        frame.bar_role if bar else None,
        stamp_ref, frame.stamp_corner if stamp_ref is not None else None, stamp_inline, stamp_block, stamp_column,
        heading, bar_block, bar_inline, frame.bar_width, frame.bar_bleed, frame.stamp_placement)


def place_kind_frame(measure: KindFrameMeasure, *, annotation_id: str, presentation: AnnotationPresentation,
                     content_box: tuple[float, float, float, float], theme_tokens: ThemeTokenView,
                     font_metrics: Any, annotation_slot: str, paint_order: int,
                     inner_border_box: tuple[float, float, float, float] | None = None
                     ) -> tuple[tuple[ShapePlacement, ...], tuple[TextPlacement, ...]]:
    """Complete the bar, stamp and header text inside ``content_box`` (x, y, width, height)."""
    x, y, width, height = content_box
    shapes: list[ShapePlacement] = []
    text: list[TextPlacement] = []

    def rect(placement_id: str, semantic_id: str, left: float, top: float, w: float, h: float) -> ShapePlacement:
        return ShapePlacement(placement_id, annotation_id, "Rect",
                              Rect(Decimal(str(left)), Decimal(str(top)), Decimal(str(w)), Decimal(str(h))),
                              semantic_id=semantic_id, annotation=presentation, paint_order=paint_order)

    inner_x = x + measure.body_inset_left
    inner_y = y
    inner_width = width - measure.inline_insets
    bar_x, bar_y = inner_x, inner_y
    bar_width = inner_width if measure.bar_width == "fill" else measure.bar_inline
    if measure.bar and measure.bar_bleed == "border":
        if inner_border_box is None:
            raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", f"/annotations/{annotation_id}",
                              detail="border-bleeding kind bar requires completed inner-border bounds")
        bar_x, bar_y, bar_width, _ = inner_border_box
    if measure.bar:
        shapes.append(rect(f"annotation-kind-bar:{annotation_id}", "annotationKindBar",
                           bar_x, bar_y, bar_width, measure.bar_block))
    if measure.stamp_ref is not None:
        if measure.stamp_placement == "bar-end":
            stamp_x = bar_x + bar_width - measure.stamp_inline
            stamp_y = bar_y + (measure.bar_block - measure.stamp_block) / 2
        else:
            gap = measure.stamp_column - measure.stamp_inline
            stamp_x = (x if measure.stamp_at_start
                       else x + width - measure.stamp_column + gap)
            stamp_y = (y if str(measure.stamp_corner).endswith("top")
                       else y + height - measure.stamp_block)
        bounds = (stamp_x, stamp_y, measure.stamp_inline, measure.stamp_block)
        try:
            parts = symbol_parts({"shape": {"catalog": measure.stamp_ref}}, bounds,
                                 catalog_glyphs=theme_tokens.catalog_glyphs)
        except ValueError as error:
            raise LayoutError("E_THEME_ASSET_REFERENCE", f"/annotations/{annotation_id}") from error
        shapes.append(replace(rect(f"annotation-kind-stamp:{annotation_id}", "annotationKindStamp", *bounds),
                              kind="Glyph", symbol_parts=parts))
    label_x = inner_x
    label_y = inner_y
    if measure.bar and measure.bar_bleed == "border":
        label_x = bar_x + measure.body_inset_left
        label_y = bar_y
    line_top = label_y + measure.bar_padding_block
    for index, line in enumerate(measure.lines):
        semantic_id = "annotationKindLabel" if index == 0 else "annotationKindSecondary"
        placed = place_text(placement_id=f"annotation-kind-text:{annotation_id}:{index}", source_ref=annotation_id,
                            content=line.content, inline=label_x + measure.bar_padding_inline,
                            baseline_block=line_top + line.font_size, typography_role=line.role,
                            theme_tokens=theme_tokens, font_metrics=font_metrics,
                            collision_region="annotations", collision_domain=CollisionDomain(annotation_slot, "content"),
                            semantic_id=semantic_id, annotation=presentation)
        text.append(replace(placed, paint_order=paint_order + 1))
        line_top += line.font_size * line.leading
    if measure.heading is not None:
        line = measure.heading
        placed = place_text(placement_id=f"annotation-heading:{annotation_id}", source_ref=annotation_id,
                            content=line.content, inline=inner_x,
                            baseline_block=inner_y + measure.bar_block + line.font_size,
                            typography_role=line.role, theme_tokens=theme_tokens, font_metrics=font_metrics,
                            collision_region="annotations", collision_domain=CollisionDomain(annotation_slot, "content"),
                            semantic_id="annotationHeading", annotation=presentation)
        text.append(replace(placed, paint_order=paint_order + 1))
    return tuple(shapes), tuple(text)
