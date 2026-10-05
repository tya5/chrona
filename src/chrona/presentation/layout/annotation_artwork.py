"""Vector artwork behind an annotation container: the completed ``Glyph`` shape (#848).

Pure Layout composition. A rectangle container that declares ``artwork`` stretches each catalogue layer over its paint
box by nine-slice (``glyph_slice_geometry``); the box ``Rect`` keeps painting the paper under it. The shape carries the
completed parts and is emitted right after the box and before the kind frame and the text (paint order is the
caller's). A container without ``artwork`` places nothing.
"""
from __future__ import annotations

from decimal import Decimal

from chrona.presentation.layout.glyph_slice_geometry import GlyphSliceError, slice_glyph_parts
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import AnnotationPresentation, ShapePlacement
from chrona.presentation.model.theme_tokens import ArtworkToken, ThemeTokenError, ThemeTokenView

ARTWORK_ROLE = "annotation-artwork"


def place_artwork(artwork: tuple[ArtworkToken, ...], *, annotation_id: str, presentation: AnnotationPresentation,
                  box: tuple[float, float, float, float], text_size: float, theme_tokens: ThemeTokenView,
                  paint_order: int, pointer: str) -> tuple[ShapePlacement, ...]:
    """Complete ordered layers of one annotation inside its unchanged paper box."""
    x, y, width, height = box
    shapes = []
    for layer in artwork:
        if not theme_tokens.has_role(layer.role):
            where = (f"/body/roles/{ARTWORK_ROLE}" if layer.layer_index is None else layer.declaration_pointer)
            raise LayoutError("E_THEME_ROLE_REQUIRED", where)
        try:
            glyph = theme_tokens.catalog_glyph(layer.glyph)
        except ThemeTokenError as error:
            raise LayoutError("E_THEME_ASSET_REFERENCE", pointer) from error
        try:
            parts: tuple[SymbolPartPlacement, ...] = slice_glyph_parts(
                glyph, box, slice_insets=tuple(float(value) for value in layer.slice_insets),  # type: ignore[arg-type]
                unit_px=float(layer.unit_em) * text_size)
        except GlyphSliceError as error:
            raise LayoutError(error.code, pointer) from error
        suffix = "" if layer.layer_index is None else f":layer{layer.layer_index}"
        shapes.append(ShapePlacement(f"annotation-artwork:{annotation_id}{suffix}", annotation_id, "Glyph",
                                     Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                     semantic_id="annotationArtwork", annotation=presentation, paint_order=paint_order,
                                     symbol_parts=parts, visual_role=layer.role))
    return tuple(shapes)
