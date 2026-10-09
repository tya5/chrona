"""Group-header text template: closed grammar, ordinal forms, composition (#583).

A View declares the header of each group as a template of literal text and closed
placeholders, ``{ordinal}``, ``{title}``, ``{secondary}`` and ``{figure:<id>}``, which
shows a derived figure the View declares (#586); ``{{`` and ``}}`` are literal braces.  A placeholder
MAY carry a Theme text role, ``{name|role}`` (#1192): its text is one run in that role's typography and
ink, on the baseline shared with the other runs.  Literal text and unmarked placeholders take the default
``groupHeader`` role.
This module is pure: it parses and renders strings and reads no Project, Theme or
Layout fact.  Callers supply the title, the secondary text and the resolved figures.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import re
from typing import Any

ORDINAL_FORMS = ("arabic", "zero-padded", "roman", "kanji", "kanji-formal")
PLACEHOLDERS = ("ordinal", "title", "secondary")
FIGURE_PREFIX = "figure:"
ROLE_SEPARATOR = "|"
ROLE_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")

_ROMAN = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
_KANJI = {"digits": "〇一二三四五六七八九", "ten": "十"}
_KANJI_FORMAL = {"digits": "〇壱弐参肆伍陸漆捌玖", "ten": "拾"}
_RANGES = {"roman": (1, 3999), "kanji": (1, 99), "kanji-formal": (1, 99)}


class GroupHeaderTextError(ValueError):
    """A stable-coded failure; ``code`` is the diagnostic identifier."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class HeaderTemplate:
    """A parsed template: literal text and placeholder names in order."""

    parts: tuple[tuple[str, str], ...]  # ("text", literal) or ("field", placeholder)
    # The Theme text role each part carries (#1192), parallel to ``parts``; empty when no part is marked.
    marks: tuple[str | None, ...] = ()

    @property
    def roles(self) -> frozenset[str]:
        """The Theme text roles the template's marked placeholders name."""
        return frozenset(mark for mark in self.marks if mark is not None)

    @property
    def fields(self) -> frozenset[str]:
        return frozenset(value for kind, value in self.parts if kind == "field")

    @property
    def figure_ids(self) -> frozenset[str]:
        """The identifiers of the derived figures this template shows."""
        return frozenset(value[len(FIGURE_PREFIX):] for value in self.fields if value.startswith(FIGURE_PREFIX))


def _is_placeholder(name: str, placeholders: tuple[str, ...] = PLACEHOLDERS, allow_figures: bool = True) -> bool:
    return name in placeholders or (allow_figures and name.startswith(FIGURE_PREFIX) and len(name) > len(FIGURE_PREFIX))


@dataclass(frozen=True)
class HeaderRun:
    """One run of a marked header: its text and Theme role (``None`` is the default ``groupHeader`` role)."""

    text: str
    role: str | None


def template_roles(source: str) -> frozenset[str]:
    """The roles ``source`` marks, read leniently (nothing is raised); used to find a Theme role's consumer (#1117)."""
    return frozenset(match.group(1) for match in re.finditer(r"\{[^{}|]+\|([A-Za-z][A-Za-z0-9_-]*)\}", source))


def parse_template(source: str, *, placeholders: tuple[str, ...] = PLACEHOLDERS, code: str = "E_VIEW_GROUP_HEADER_TEMPLATE",
                   allow_figures: bool = True, allow_roles: bool = False) -> HeaderTemplate:
    """Parse ``source`` or raise ``code`` for any other brace use.

    The grammar (literal text, closed ``{name}`` placeholders, ``{{`` and ``}}``) is shared with the
    heading template (#991), which passes its own closed placeholder set and code.  ``{name|role}`` marks a
    placeholder with a Theme text role (#1192) only where ``allow_roles`` is set (the group header).
    """
    parts: list[tuple[str, str]] = []
    marks: list[str | None] = []
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
            role: str | None = None
            if allow_roles and ROLE_SEPARATOR in name:
                name, _, role = name.partition(ROLE_SEPARATOR)
                if ROLE_PATTERN.fullmatch(role) is None:
                    raise GroupHeaderTextError(code, f"malformed role mark in {source!r}")
            if not _is_placeholder(name, placeholders, allow_figures):
                raise GroupHeaderTextError(code, f"unknown or unterminated placeholder in {source!r}")
            if literal:
                parts.append(("text", "".join(literal)))
                marks.append(None)
                literal = []
            parts.append(("field", name))
            marks.append(role)
            index = end + 1
            continue
        if char == "}":
            if source[index + 1:index + 2] != "}":
                raise GroupHeaderTextError(code, f"lone closing brace in {source!r}")
            literal.append("}")
            index += 2
            continue
        literal.append(char)
        index += 1
    if literal:
        parts.append(("text", "".join(literal)))
        marks.append(None)
    return HeaderTemplate(tuple(parts), tuple(marks) if any(mark is not None for mark in marks) else ())


def format_ordinal(position: int, form: str, *, group_count: int) -> str:
    """Render the 1-based ``position`` in ``form``; outside the form's range is an error, never a fallback."""
    if form not in ORDINAL_FORMS:
        raise GroupHeaderTextError("E_REVIEW_GROUP_ORDINAL_RANGE", f"unknown ordinal form {form!r}")
    low, high = _RANGES.get(form, (1, position if position >= 1 else 1))
    if position < low or position > high:
        raise GroupHeaderTextError("E_REVIEW_GROUP_ORDINAL_RANGE", f"{form} position {position} outside {low}..{high}")
    if form == "arabic":
        return str(position)
    if form == "zero-padded":
        return str(position).zfill(max(2, len(str(group_count))))
    if form == "roman":
        remaining, out = position, []
        for value, numeral in _ROMAN:
            while remaining >= value:
                out.append(numeral)
                remaining -= value
        return "".join(out)
    table = _KANJI if form == "kanji" else _KANJI_FORMAL
    tens, ones = divmod(position, 10)
    prefix = "" if tens == 0 else table["ten"] if tens == 1 else table["digits"][tens] + table["ten"]
    return prefix + (table["digits"][ones] if ones else "")


def _field_text(value: str, *, ordinal: str, title: str, secondary: str | None,
                figures: Mapping[str, int] | None) -> str:
    if value == "ordinal":
        return ordinal
    if value == "title":
        return title
    if value.startswith(FIGURE_PREFIX):
        figure_id = value[len(FIGURE_PREFIX):]
        if figures is None or figure_id not in figures:
            raise GroupHeaderTextError("E_VIEW_GROUP_HEADER_TEMPLATE", f"no resolved figure {figure_id!r}")
        return str(figures[figure_id])
    if secondary is None:
        raise GroupHeaderTextError("E_REVIEW_GROUP_HEADER_SECONDARY", "template uses {secondary} without a value")
    return secondary


def render_header(template: HeaderTemplate, *, ordinal: str, title: str, secondary: str | None,
                  figures: Mapping[str, int] | None = None) -> str:
    """Substitute the placeholders; a ``{secondary}`` without a value or a figure not resolved is an error."""
    return "".join(value if kind == "text" else _field_text(value, ordinal=ordinal, title=title, secondary=secondary,
                                                            figures=figures)
                   for kind, value in template.parts)


def render_header_runs(template: HeaderTemplate, *, ordinal: str, title: str, secondary: str | None,
                       figures: Mapping[str, int] | None = None) -> tuple[HeaderRun, ...]:
    """The runs of a marked template: adjacent parts of one role are one run; the text is the same as ``render_header``."""
    runs: list[HeaderRun] = []
    marks = template.marks or (None,) * len(template.parts)
    for (kind, value), role in zip(template.parts, marks, strict=True):
        text = value if kind == "text" else _field_text(value, ordinal=ordinal, title=title, secondary=secondary,
                                                        figures=figures)
        if not text:
            continue
        if runs and runs[-1].role == role:
            runs[-1] = HeaderRun(runs[-1].text + text, role)
        else:
            runs.append(HeaderRun(text, role))
    return tuple(runs)


def _compose(*, group_ids: tuple[str, ...], titles: dict[str, str], secondaries: dict[str, str] | None,
             text: str, first: str | None, ordinal: str, figures: Mapping[str, int] | None,
             group_figures: Mapping[str, Mapping[str, int]] | None) -> Iterator[
                 tuple[str, HeaderTemplate, dict[str, Any]]]:
    main = parse_template(text, allow_roles=True)
    opening = parse_template(first, allow_roles=True) if first is not None else main
    count = len(group_ids)
    for position, group_id in enumerate(group_ids, start=1):
        template = opening if position == 1 else main
        secondary = (secondaries or {}).get(group_id) if "secondary" in template.fields else None
        if "secondary" in template.fields and not secondary:
            raise GroupHeaderTextError("E_REVIEW_GROUP_HEADER_SECONDARY", f"group {group_id}: no secondary text")
        rendered_ordinal = (format_ordinal(position, ordinal, group_count=count)
                            if "ordinal" in template.fields else "")
        yield group_id, template, dict(ordinal=rendered_ordinal, title=titles.get(group_id, group_id),
                                       secondary=secondary,
                                       figures={**(figures or {}), **((group_figures or {}).get(group_id, {}))})


def compose_group_headers(*, group_ids: tuple[str, ...], titles: dict[str, str], secondaries: dict[str, str] | None,
                          text: str, first: str | None, ordinal: str,
                          figures: Mapping[str, int] | None = None,
                          group_figures: Mapping[str, Mapping[str, int]] | None = None) -> tuple[tuple[str, str], ...]:
    """Return ``(group id, header text)`` for each group in display order (marks do not change the text)."""
    return tuple((group_id, render_header(template, **facts)) for group_id, template, facts in _compose(
        group_ids=group_ids, titles=titles, secondaries=secondaries, text=text, first=first, ordinal=ordinal,
        figures=figures, group_figures=group_figures))


def compose_group_header_runs(*, group_ids: tuple[str, ...], titles: dict[str, str],
                              secondaries: dict[str, str] | None, text: str, first: str | None, ordinal: str,
                              figures: Mapping[str, int] | None = None,
                              group_figures: Mapping[str, Mapping[str, int]] | None = None
                              ) -> tuple[tuple[str, tuple[HeaderRun, ...]], ...]:
    """Return ``(group id, runs)`` for each group whose template marks a role; an unmarked header has none (#1192)."""
    return tuple((group_id, render_header_runs(template, **facts)) for group_id, template, facts in _compose(
        group_ids=group_ids, titles=titles, secondaries=secondaries, text=text, first=first, ordinal=ordinal,
        figures=figures, group_figures=group_figures) if template.roles)
