"""Annotation kind header text: closed template grammar and composition (#584).

A Theme declares, per Project annotation kind, a `label`, an optional `secondary` label and
an optional `title` template of literal text and the closed placeholders `{label}`,
`{secondary}` and `{subject}` (the anchored object's title); `{{` and `}}` are literal
braces.  This module is pure: it parses and renders strings and reads no Project, Theme
or Layout fact.  It is deliberately independent of the group-header grammar, which has
other placeholders.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

PLACEHOLDERS = ("label", "secondary", "subject")
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

    @property
    def inline_secondary(self) -> bool:
        """Whether the title shows the secondary label itself (then there is no second line)."""
        return ("field", "secondary") in self.parts


def parse_title(source: str) -> tuple[tuple[str, str], ...]:
    """Parse ``source`` or raise ``E_THEME_ANNOTATION_KIND_TEMPLATE`` for any other brace use."""
    parts: list[tuple[str, str]] = []
    literal: list[str] = []
    index = 0
    while index < len(source):
        char = source[index]
        if char == "{":
            if source[index + 1:index + 2] == "{":
                literal.append("{")
                index += 2
                continue
            end = source.find("}", index + 1)
            name = source[index + 1:end] if end != -1 else ""
            if name not in PLACEHOLDERS:
                raise AnnotationKindTextError(CODE, f"unknown or unterminated placeholder in {source!r}")
            if literal:
                parts.append(("text", "".join(literal)))
                literal = []
            parts.append(("field", name))
            index = end + 1
            continue
        if char == "}":
            if source[index + 1:index + 2] != "}":
                raise AnnotationKindTextError(CODE, f"lone closing brace in {source!r}")
            literal.append("}")
            index += 2
            continue
        literal.append(char)
        index += 1
    if literal:
        parts.append(("text", "".join(literal)))
    return tuple(parts)


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
    return KindHeader(label, secondary, title, parts)


def header_lines(header: KindHeader, *, subject: str) -> tuple[str, ...]:
    """The header text: the rendered title, then the secondary label unless the title shows it."""
    values = {"label": header.label, "secondary": header.secondary or "", "subject": subject}
    first = "".join(value if kind == "text" else values[value] for kind, value in header.parts)
    if header.secondary is not None and not header.inline_secondary:
        return (first, header.secondary)
    return (first,)
