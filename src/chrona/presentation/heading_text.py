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
from chrona.presentation.figure_text import FigureTextError, FigureTextProgram, FigureTextReadError
from chrona.presentation.group_header_text import GroupHeaderTextError, HeaderTemplate, parse_template

PLACEHOLDERS = ("project", "asOf", "calendar")
CODE = "E_VIEW_HEADING_TEMPLATE"


@dataclass(frozen=True)
class HeadingPart:
    """One authored heading fragment, optionally omitted for a raw zero count."""

    text: str
    omit_when_zero: str | None = None


@dataclass(frozen=True)
class ClosedHeadingPart:
    """A heading fragment with semantic facts closed and Layout reads retained."""

    program: FigureTextProgram
    omit_when_zero: str | None = None


@dataclass(frozen=True)
class ClosedHeadingProgram:
    """Ordered heading parts whose guards and figure reads Layout binds before measurement."""

    parts: tuple[ClosedHeadingPart, ...]

    @property
    def figure_ids(self) -> frozenset[str]:
        return frozenset(identifier for part in self.parts
                         for identifier in (part.program.figure_ids | ({part.omit_when_zero}
                                                                        if part.omit_when_zero else set())))

    def bind(self, figures: Mapping[str, int], formats: Mapping[str, CountTextFormat]) -> str:
        values = []
        for part in self.parts:
            if part.omit_when_zero is not None:
                if part.omit_when_zero not in figures:
                    known = ", ".join(sorted(figures)) if figures else "none"
                    raise FigureTextError(
                        "E_VIEW_FIGURE_UNKNOWN",
                        f"no resolved figure {part.omit_when_zero!r} (known figures: {known})")
                if figures[part.omit_when_zero] == 0:
                    continue
            values.append(part.program.bind(figures, formats))
        return "".join(values)


@dataclass(frozen=True)
class HeadingTextPrograms:
    """Semantic facts are literal; Layout binds the remaining count reads before measurement."""
    title: FigureTextProgram | ClosedHeadingProgram
    subtitle: FigureTextProgram | ClosedHeadingProgram | None = None
    kicker: FigureTextProgram | ClosedHeadingProgram | None = None
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
                if isinstance(program, ClosedHeadingProgram) and member != "title" and values[member] == "":
                    values[member] = None
            except (CountTextError, FigureTextError) as error:
                raise FigureTextReadError(error, f"/body/heading/{member}") from error
        return values["title"], values["subtitle"], values["kicker"]


def validate_heading_template(source: str) -> frozenset[str]:
    """Return the placeholders `source` uses, or raise `GroupHeaderTextError(E_VIEW_HEADING_TEMPLATE)`."""
    return parse_template(source, placeholders=PLACEHOLDERS, code=CODE).fields


def _close_heading_source(source: str, facts: Mapping[str, str]) -> FigureTextProgram:
    """Freeze semantic text now, leaving only declared figure reads for Layout binding.

    Fact text becomes literal parts, never reparsed as authored template syntax.
    No number names are required before a completed candidate reads the program.
    """
    template = parse_template(source, placeholders=PLACEHOLDERS, code=CODE)
    parts = tuple((kind, value) if kind == "text" or value.startswith("figure:")
                  else ("text", facts.get(value, "")) for kind, value in template.parts)
    return FigureTextProgram(HeaderTemplate(parts))


def close_heading(source: str | tuple[HeadingPart, ...], facts: Mapping[str, str]) -> FigureTextProgram | ClosedHeadingProgram:
    """Close semantic text while retaining ordered omission guards for Layout."""
    if isinstance(source, str):
        return _close_heading_source(source, facts)
    return ClosedHeadingProgram(tuple(
        ClosedHeadingPart(_close_heading_source(part.text, facts), part.omit_when_zero)
        for part in source))


def heading_figure_ids(source: str) -> frozenset[str]:
    return parse_template(source, placeholders=PLACEHOLDERS, code=CODE).figure_ids


def render_heading(source: str, facts: Mapping[str, str], *, figures: Mapping[str, int] | None = None,
                   formats: Mapping[str, CountTextFormat] | None = None) -> str:
    """Bind semantic facts and already resolved figures without a missing-count default."""
    return close_heading(source, facts).bind(figures or {}, formats)


__all__ = ["CODE", "GroupHeaderTextError", "PLACEHOLDERS", "close_heading", "heading_figure_ids",
           "HeadingPart", "ClosedHeadingProgram", "HeadingTextPrograms", "render_heading",
           "validate_heading_template"]
