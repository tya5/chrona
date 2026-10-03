"""Viewer-fit stamping of a box role's text (#1050).

Layout alone owns font metrics, so the facts a viewer-fit mode needs are measured here, with the metric and treatment
``place_text`` used, and carried on the completed placement; the adapters only serialise them. ``raw`` (the default)
never reaches this module, so the default output is the one it always was.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import TextFit, TextPlacement
from chrona.presentation.layout.text import measure_text_width, metric_for_family
from chrona.presentation.model.theme_tokens import (
    BOX_FOLLOWS_TEXT, TEXT_FOLLOWS_BOX, VIEWER_FIT_RAW, ViewerFitToken,
)


def _metric(text: TextPlacement, font_metrics: Any) -> Any:
    return metric_for_family(text.font_family, text.font_weight, font_metrics, text.horizontal_scale)


def line_inline_sizes(text: TextPlacement, font_metrics: Any) -> tuple[float, ...]:
    """The measured inline size of every drawn line, as the viewer is asked to draw it.

    The lines are already painted (text transform applied), so they are measured as they stand, through the role's
    metric at its declared compression: the same measurement ``wrap_text`` and ``measure_note`` use.
    """
    metric = _metric(text, font_metrics)
    return tuple(measure_text_width(line, font_size=text.font_size, font_metrics=metric,
                                    letter_spacing=text.letter_spacing, numeric_spacing=text.numeric_spacing)
                 for line in text.lines)


def end_pad_spaces(text: TextPlacement, font_metrics: Any, end_inset: float) -> int:
    """How many spaces of the run's own face stand for ``end_inset`` (the nearest whole count, never negative)."""
    if end_inset <= 0:
        return 0
    space = measure_text_width(" ", font_size=text.font_size, font_metrics=_metric(text, font_metrics),
                               letter_spacing=text.letter_spacing, numeric_spacing=text.numeric_spacing)
    return max(0, round(end_inset / space)) if space > 0 else 0


def fit_text(text: TextPlacement, token: ViewerFitToken, font_metrics: Any, *,
             box_id: str, end_inset: float = 0.0) -> TextPlacement:
    """Return ``text`` with the completed facts of the box role's mode; ``raw`` returns it unchanged."""
    if token.mode == VIEWER_FIT_RAW:
        return text
    if token.mode == TEXT_FOLLOWS_BOX:
        return replace(text, fit=TextFit(TEXT_FOLLOWS_BOX, token.adjust, line_inline_sizes(text, font_metrics)))
    if token.mode == BOX_FOLLOWS_TEXT:
        return replace(text, fit=TextFit(BOX_FOLLOWS_TEXT, "spacing", (), box_id,
                                         end_pad_spaces(text, font_metrics, end_inset)))
    raise ValueError("E_PRESENTATION_TEXT_LAYOUT_INVALID: viewer fit")


def require_followable_content(token: ViewerFitToken, *, has_kind_frame: bool, has_visual: bool, pointer: str) -> None:
    """``box-follows-text`` cannot follow static chrome drawn over the box: refuse it, never drop it silently.

    A kind frame (bar, accent edge, header text, stamp) and a leading or trailing label visual stand at fixed
    offsets over the measured box, so a background that ends elsewhere would leave them hanging.
    """
    if token.mode != BOX_FOLLOWS_TEXT:
        return
    if has_kind_frame:
        raise LayoutError("E_LAYOUT_VIEWER_FIT_STATIC_CHROME", pointer)
    if has_visual:
        raise LayoutError("E_LAYOUT_VIEWER_FIT_STATIC_CHROME", pointer)
