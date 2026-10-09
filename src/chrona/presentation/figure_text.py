"""Presentation text substitution for declared derived figures.

This helper knows only literal text, the closed ``{figure:<id>}`` marker, and
already-resolved integer values. Callers own fact collection and resolution.
"""
from __future__ import annotations

from collections.abc import Mapping

from chrona.presentation.group_header_text import GroupHeaderTextError, parse_template


class FigureTextError(ValueError):
    """Stable-coded malformed or unresolved figure text."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail


_FIGURE_MARKER = "{figure:"
_CODE = "E_VIEW_FIGURE_TEMPLATE"


def _template(source: str):
    try:
        return parse_template(source, placeholders=(), code=_CODE, allow_figures=True)
    except GroupHeaderTextError as error:
        raise FigureTextError(_CODE, error.detail) from error


def figure_ids(source: str, *, strict: bool = False) -> frozenset[str]:
    """Return referenced figure IDs, validating marker-bearing template text."""
    if not strict and _FIGURE_MARKER not in source:
        return frozenset()
    return _template(source).figure_ids


def resolve_figure_text(source: str, figures: Mapping[str, int], *, strict: bool = False) -> str:
    """Substitute closed figure markers; preserve marker-free source verbatim."""
    if not strict and _FIGURE_MARKER not in source:
        return source
    template = _template(source)
    parts: list[str] = []
    known = ", ".join(sorted(figures)) if figures else "none"
    for kind, value in template.parts:
        if kind == "text":
            parts.append(value)
            continue
        figure_id = value[len("figure:"):]
        if figure_id not in figures:
            raise FigureTextError(
                "E_VIEW_FIGURE_UNKNOWN",
                f"no resolved figure {figure_id!r} (known figures: {known})",
            )
        parts.append(str(figures[figure_id]))
    return "".join(parts)


__all__ = ["FigureTextError", "figure_ids", "resolve_figure_text"]
