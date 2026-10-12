"""Heading templates: the title and subtitle a View declares (#991).

A View's `heading` carries two optional templates of literal text and the closed placeholders
`{project}` (the Project title), `{asOf}` (the Actual Set's as-of date in the declared date form) and
`{calendar}` (the Project's default calendar title, else its id), and declared `{figure:id}` reads.
Semantic facts close as literal parts; Layout binds the figure text before measurement.
It shares the brace grammar of the group-header
template (`group_header_text.parse_template`) with its own placeholder set. This module is pure: callers
supply the facts.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from chrona.presentation.count_text import CountTextError, CountTextFormat
from chrona.presentation.figure_text import FigureTextError, FigureTextProgram
from chrona.presentation.group_header_text import GroupHeaderTextError, HeaderTemplate, parse_template

PLACEHOLDERS = ("project", "asOf", "calendar")
CODE = "E_VIEW_HEADING_TEMPLATE"


class HeadingBindError(ValueError):
    """Carry a typed figure failure and the exact text read, not a generic Layout error."""
    def __init__(self, failure: CountTextError | FigureTextError, path: str):
        super().__init__(str(failure))
        self.failure, self.path = failure, path


@dataclass(frozen=True)
class HeadingTextPrograms:
    """Semantic facts are literal; Layout binds the remaining count reads before measurement."""
    title: FigureTextProgram
    subtitle: FigureTextProgram | None = None
    kicker: FigureTextProgram | None = None
    text_wrap: str = "forbid"

    @property
    def figure_ids(self) -> frozenset[str]:
        return frozenset(identifier for program in (self.title, self.subtitle, self.kicker)
                         if program is not None for identifier in program.figure_ids)

    def bind(self, figures: Mapping[str, int], formats: Mapping[str, CountTextFormat]) -> tuple[str, str | None, str | None]:
        values = {}
        for member in ("title", "subtitle", "kicker"):
            program = getattr(self, member)
            try:
                values[member] = program.bind(figures, formats) if program is not None else None
            except (CountTextError, FigureTextError) as error:
                raise HeadingBindError(error, f"/body/heading/{member}") from error
        return values["title"], values["subtitle"], values["kicker"]


def validate_heading_template(source: str) -> frozenset[str]:
    """Return the placeholders `source` uses, or raise `GroupHeaderTextError(E_VIEW_HEADING_TEMPLATE)`."""
    return parse_template(source, placeholders=PLACEHOLDERS, code=CODE).fields


def close_heading(source: str, facts: Mapping[str, str]) -> FigureTextProgram:
    """Freeze semantic text now, leaving only declared figure reads for Layout binding.

    Fact text becomes literal parts, never reparsed as authored template syntax.
    No number names are required before a completed candidate reads the program.
    """
    template = parse_template(source, placeholders=PLACEHOLDERS, code=CODE)
    parts = tuple((kind, value) if kind == "text" or value.startswith("figure:")
                  else ("text", facts.get(value, "")) for kind, value in template.parts)
    return FigureTextProgram(HeaderTemplate(parts))


def heading_figure_ids(source: str) -> frozenset[str]:
    return parse_template(source, placeholders=PLACEHOLDERS, code=CODE).figure_ids


def render_heading(source: str, facts: Mapping[str, str], *, figures: Mapping[str, int] | None = None,
                   formats: Mapping[str, CountTextFormat] | None = None) -> str:
    """Bind semantic facts and already resolved figures without a missing-count default."""
    return close_heading(source, facts).bind(figures or {}, formats)


__all__ = ["CODE", "GroupHeaderTextError", "PLACEHOLDERS", "close_heading", "heading_figure_ids",
           "HeadingBindError", "HeadingTextPrograms", "render_heading", "validate_heading_template"]
