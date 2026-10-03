"""Synthetic vector-artwork fixtures for the #848 rules.

A Project with Project annotations goes through the packaged preset bundle and the packaged `chrona-target-parts`
catalogue with a Theme whose note box declares an `annotationContainer.artwork`. Nothing here reads `examples/`.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from tests.support import annotation_kinds as ak

SCROLL = "chrona-target-parts:scroll-frame"
CLIPPING = "chrona-target-parts:clipping-edge"
# The scroll's frame: the hanger and the top rod above the hole, the bottom rod below it, a bar either side.
SCROLL_INSETS = {"top": 16.3, "right": 8.2, "bottom": 11.5, "left": 8.2}
CLIPPING_TOP = {"top": 8, "right": 0, "bottom": 0, "left": 0}
CONTENT_INSET = {"top": 1.9, "right": 1.1, "bottom": 1.5, "left": 1.1}
PAPER = "#F2E8D0"
INK = "#3B2A1E"


def with_artwork(parts: dict[str, dict[str, Any]], *, glyph: str = SCROLL, insets: Mapping[str, float] | None = None,
                 unit_em: float = 0.09, content: Mapping[str, float] | None = CONTENT_INSET,
                 outline: str = "rectangle", role: bool = True, ink: str = "text", ink_stroke: str | None = "text",
                 paper: str | None = "surface", fidelity: str | None = None, opacity: float | None = None,
                 roles: Iterable[str] = ("annotation-note-box",), extra: Mapping[str, Any] | None = None,
                 artwork_declared: bool = True) -> None:
    """Declare the container token (with its artwork), the ink role and the paper fill of the note box."""
    theme, scheme = parts["theme"]["body"], parts["scheme"]["body"]
    artwork = {"glyph": glyph, "sliceInsets": dict(SCROLL_INSETS if insets is None else insets), "unitEm": unit_em}
    value: dict[str, Any] = {"outline": outline, "cornerRadius": 0, **({"artwork": artwork} if artwork_declared else {}),
                             **(extra or {})}
    if outline == "balloon":
        value["tailBaseEm"] = 0.6
    if content is not None:
        value["contentInsetEm"] = dict(content)
    theme["values"]["artwork-container"] = {"type": "annotationContainer", "value": value}
    for name in roles:
        theme["roles"].setdefault(name, {})["annotationContainer"] = "artwork-container"
        if paper is not None:
            theme["colorBindings"][f"{name}.fill"] = paper
    if role:
        ink_role: dict[str, Any] = {}
        if fidelity is not None:
            theme["values"]["artwork-fidelity"] = {"type": "fidelity", "value": fidelity}
            ink_role["artworkFidelity"] = "artwork-fidelity"
        if opacity is not None:
            theme["values"]["artwork-opacity"] = {"type": "number", "value": opacity}
            ink_role["opacity"] = "artwork-opacity"
        theme["roles"]["annotation-artwork"] = ink_role
        theme["colorBindings"]["annotation-artwork.fill"] = ink
        if ink_stroke is not None:
            theme["colorBindings"]["annotation-artwork.stroke"] = ink_stroke
    del scheme  # the packaged Scheme already carries the intents used above


def artwork_parts(rendered: Any, note: str = "view-n0") -> list[Any]:
    """The Scene primitives of one note's artwork, in paint order."""
    return [item for item in rendered.surface.primitives if item.scene_id.startswith(f"annotation-artwork:{note}")]


render = ak.render
