"""Presentation text substitution for declared derived figures.

This helper knows only literal text, the closed ``{figure:<id>}`` marker, and
already-resolved integer values. Callers own fact collection and resolution.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from chrona.presentation.count_text import CountTextError, CountTextFormat, format_count
from chrona.presentation.group_header_text import GroupHeaderTextError, HeaderTemplate, parse_template


class FigureTextError(ValueError):
    """Stable-coded malformed or unresolved figure text."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail


class FigureTextReadError(ValueError):
    """A typed text-read failure with its resource component and exact reference."""
    def __init__(self, failure: CountTextError | FigureTextError, path: str, component: str = "view"):
        super().__init__(str(failure))
        self.failure, self.path, self.component = failure, path, component


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


@dataclass(frozen=True)
class FigureTextProgram:
    """A closed caption program; facts/format ranges are bound only at a text read."""
    template: HeaderTemplate

    @property
    def figure_ids(self) -> frozenset[str]:
        return self.template.figure_ids

    def bind(self, figures: Mapping[str, int],
             formats: Mapping[str, CountTextFormat] | None = None) -> str:
        return _bind(self.template, figures, formats)


def compile_figure_text(source: str) -> FigureTextProgram:
    return FigureTextProgram(_template(source))


def _bind(template: HeaderTemplate, figures: Mapping[str, int],
          formats: Mapping[str, CountTextFormat] | None = None) -> str:
    parts: list[str] = []
    known = ", ".join(sorted(figures)) if figures else "none"
    for kind, value in template.parts:
        if kind == "text":
            parts.append(value)
            continue
        figure_id = value[len("figure:"):]
        if figure_id not in figures:
            raise FigureTextError("E_VIEW_FIGURE_UNKNOWN",
                f"no resolved figure {figure_id!r} (known figures: {known})")
        text_format = (formats or {}).get(figure_id)
        try:
            parts.append(format_count(figures[figure_id], text_format) if text_format is not None
                         else str(figures[figure_id]))
        except CountTextError as error:
            raise CountTextError(error.code, f"figure={figure_id}; {error.detail}", value=error.value, form=error.form,
                                 supported_range=error.supported_range, figure_id=figure_id) from error
    return "".join(parts)


def resolve_figure_text(source: str, figures: Mapping[str, int], *, strict: bool = False,
                        formats: Mapping[str, CountTextFormat] | None = None) -> str:
    """Substitute closed figure markers; preserve marker-free source verbatim."""
    if not strict and _FIGURE_MARKER not in source:
        return source
    return _bind(_template(source), figures, formats)


__all__ = ["FigureTextError", "FigureTextReadError", "FigureTextProgram", "compile_figure_text", "figure_ids", "resolve_figure_text"]
