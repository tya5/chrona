"""Annotation kind header text: closed template grammar and composition (#584).

A Theme declares, per Project annotation kind, a `label`, an optional `secondary` label and
an optional `title` template of literal text and the closed placeholders `{label}`,
`{secondary}`, `{subject}` (the anchored object's title) and `{subjectId}` (its id, #991); `{{` and `}}` are literal
braces.  This module is pure: it parses and renders strings and reads no Project, Theme
or Layout fact.  It is deliberately independent of the group-header grammar, which has
other placeholders.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from chrona.presentation.group_header_text import FIGURE_PREFIX, GroupHeaderTextError, parse_template

PLACEHOLDERS = ("label", "secondary", "subject", "subjectId")
DEFAULT_TITLE = "{label}"
CODE = "E_THEME_ANNOTATION_KIND_TEMPLATE"


class AnnotationKindTextError(ValueError):
    """A stable-coded failure; ``code`` is the diagnostic identifier."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class KindHeader:
    """One validated kind declaration: its text sources and parsed title template."""

    label: str
    secondary: str | None
    title: str
    parts: tuple[tuple[str, str], ...]  # ("text", literal) or ("field", placeholder)
    heading: str | None = None
    heading_parts: tuple[tuple[str, str], ...] = ()

    @property
    def figure_ids(self) -> frozenset[str]:
        return frozenset(value[len(FIGURE_PREFIX):] for kind, value in (*self.parts, *self.heading_parts)
                         if kind == "field" and value.startswith(FIGURE_PREFIX))

    @property
    def inline_secondary(self) -> bool:
        """Whether the title shows the secondary label itself (then there is no second line)."""
        return ("field", "secondary") in self.parts


def parse_title(source: str) -> tuple[tuple[str, str], ...]:
    """Parse ``source`` or raise ``E_THEME_ANNOTATION_KIND_TEMPLATE`` for any other brace use."""
    try:
        return parse_template(source, placeholders=PLACEHOLDERS, code=CODE).parts
    except GroupHeaderTextError as error:
        raise AnnotationKindTextError(error.code, error.detail) from error


def kind_header(kind_id: str, declaration: Mapping[str, object]) -> KindHeader:
    """Validate one ``annotationKinds`` entry's text declaration."""
    label = declaration.get("label")
    if not isinstance(label, str) or not label.strip():
        raise AnnotationKindTextError(CODE, f"{kind_id}: label must be a non-empty string")
    secondary = declaration.get("secondary")
    if secondary is not None and (not isinstance(secondary, str) or not secondary.strip()):
        raise AnnotationKindTextError(CODE, f"{kind_id}: secondary must be a non-empty string")
    title = declaration.get("title", DEFAULT_TITLE)
    if not isinstance(title, str) or not title:
        raise AnnotationKindTextError(CODE, f"{kind_id}: title must be a non-empty template")
    parts = parse_title(title)
    if ("field", "secondary") in parts and secondary is None:
        raise AnnotationKindTextError(CODE, f"{kind_id}: title uses {{secondary}} without a secondary label")
    heading = declaration.get("heading")
    if "heading" in declaration and (not isinstance(heading, str) or not heading.strip()):
        raise AnnotationKindTextError(CODE, f"{kind_id}: heading must be a non-empty template")
    heading_parts = parse_title(heading) if heading is not None else ()
    if ("field", "secondary") in heading_parts and secondary is None:
        raise AnnotationKindTextError(CODE, f"{kind_id}: heading uses {{secondary}} without a secondary label")
    return KindHeader(label, secondary, title, parts, heading, heading_parts)


def _render(parts: tuple[tuple[str, str], ...], values: Mapping[str, str],
            figures: Mapping[str, int] | None) -> str:
    rendered = []
    for kind, value in parts:
        if kind == "text":
            rendered.append(value)
        elif value.startswith(FIGURE_PREFIX):
            figure_id = value[len(FIGURE_PREFIX):]
            if figures is None or figure_id not in figures:
                raise AnnotationKindTextError("E_VIEW_FIGURE_UNKNOWN", f"no resolved figure {figure_id!r}")
            rendered.append(str(figures[figure_id]))
        else:
            rendered.append(values[value])
    return "".join(rendered)


def heading_text(header: KindHeader, *, subject: str, subject_id: str = "",
                 figures: Mapping[str, int] | None = None) -> str | None:
    """Render the optional separate heading with the same closed grammar as the title."""
    if header.heading is None:
        return None
    values = {"label": header.label, "secondary": header.secondary or "", "subject": subject, "subjectId": subject_id}
    return _render(header.heading_parts, values, figures)


def header_lines(header: KindHeader, *, subject: str, subject_id: str = "",
                 figures: Mapping[str, int] | None = None) -> tuple[str, ...]:
    """The header text: the rendered title, then the secondary label unless the title shows it."""
    values = {"label": header.label, "secondary": header.secondary or "", "subject": subject, "subjectId": subject_id}
    first = _render(header.parts, values, figures)
    if header.secondary is not None and not header.inline_secondary:
        return (first, header.secondary)
    return (first,)
