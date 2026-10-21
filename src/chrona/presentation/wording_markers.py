"""``{wording:<key>}`` placeholders in caption and title text (#1880).

A heading part, a slot caption ``template`` and a Summary panel ``title`` may show a built-in wording-table
entry inside their text. The placeholder resolves to the Render Context locale's entry (the View's
``wording.keys`` override still wins), so one authored text reads in the render locale. An unknown key is
``E_WORDING_KEY_UNKNOWN``. This module is pure: callers supply the resolver.
"""
from __future__ import annotations

from collections.abc import Callable

from chrona.presentation.group_header_text import GroupHeaderTextError, WORDING_PREFIX, parse_template

MARKER = "{" + WORDING_PREFIX
UNKNOWN_KEY = "E_WORDING_KEY_UNKNOWN"


class WordingMarkerError(ValueError):
    """A stable-coded wording-marker failure; ``code`` is the diagnostic identifier."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail


def unknown_key_error(key: str, known: tuple[str, ...]) -> WordingMarkerError:
    return WordingMarkerError(UNKNOWN_KEY, f"key={key!r}; expected one of {known!r}")


def _escape(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def resolve_figure_template_wording(source: str, text_of: Callable[[str], str]) -> str:
    """Replace each ``{wording:<key>}`` of a figure template by its text, keeping every other marker.

    The result is still a figure template: substituted text is escaped, so it can never read as a marker.
    """
    if MARKER not in source:
        return source
    template = parse_template(source, placeholders=(), code="E_VIEW_FIGURE_TEMPLATE", allow_wording=True)
    parts = []
    for kind, value in template.parts:
        if kind == "text":
            parts.append(_escape(value))
        elif value.startswith(WORDING_PREFIX):
            parts.append(_escape(text_of(value[len(WORDING_PREFIX):])))
        else:
            parts.append("{" + value + "}")
    return "".join(parts)


def resolve_plain_wording(source: str, text_of: Callable[[str], str], *, code: str) -> str:
    """Replace each ``{wording:<key>}`` of plain text by its text.

    Text without a marker is returned verbatim, so existing titles keep their braces; only text that uses a
    marker is read as a template (``{{`` and ``}}`` are then literal braces).
    """
    if MARKER not in source:
        return source
    try:
        template = parse_template(source, placeholders=(), code=code, allow_figures=False, allow_wording=True)
    except GroupHeaderTextError as error:
        raise WordingMarkerError(error.code, error.detail) from error
    return "".join(value if kind == "text" else text_of(value[len(WORDING_PREFIX):])
                   for kind, value in template.parts)


def wording_marker_keys(source: str, *, code: str, allow_figures: bool = False) -> frozenset[str]:
    """The keys a text names (empty for text without a marker); malformed marker text raises ``code``."""
    if MARKER not in source:
        return frozenset()
    try:
        return parse_template(source, placeholders=(), code=code, allow_figures=allow_figures,
                              allow_wording=True).wording_keys
    except GroupHeaderTextError as error:
        raise WordingMarkerError(error.code, error.detail) from error
