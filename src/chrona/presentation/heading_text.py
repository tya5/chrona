"""Heading templates: the title and subtitle a View declares (#991).

A View's `heading` carries two optional templates of literal text and the closed placeholders
`{project}` (the Project title), `{asOf}` (the Actual Set's as-of date in the declared date form) and
`{calendar}` (the Project's default calendar id). It shares the brace grammar of the group-header
template (`group_header_text.parse_template`) with its own placeholder set. This module is pure: callers
supply the facts.
"""
from __future__ import annotations

from collections.abc import Mapping

from chrona.presentation.group_header_text import GroupHeaderTextError, parse_template

PLACEHOLDERS = ("project", "asOf", "calendar")
CODE = "E_VIEW_HEADING_TEMPLATE"


def validate_heading_template(source: str) -> frozenset[str]:
    """Return the placeholders `source` uses, or raise `GroupHeaderTextError(E_VIEW_HEADING_TEMPLATE)`."""
    return parse_template(source, placeholders=PLACEHOLDERS, code=CODE, allow_figures=False).fields


def render_heading(source: str, facts: Mapping[str, str]) -> str:
    """Substitute `facts` into the template; a fact the Project does not have renders as empty text."""
    template = parse_template(source, placeholders=PLACEHOLDERS, code=CODE, allow_figures=False)
    return "".join(value if kind == "text" else facts.get(value, "") for kind, value in template.parts)


__all__ = ["CODE", "GroupHeaderTextError", "PLACEHOLDERS", "render_heading", "validate_heading_template"]
