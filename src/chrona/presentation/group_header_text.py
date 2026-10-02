"""Group-header text template: closed grammar, ordinal forms, composition (#583).

A View declares the header of each group as a template of literal text and three
closed placeholders, ``{ordinal}``, ``{title}`` and ``{secondary}`` (``{{`` and ``}}``
are literal braces).  This module is pure: it parses and renders strings and reads
no Project, Theme or Layout fact.  Callers supply the title and the secondary text.
"""
from __future__ import annotations

from dataclasses import dataclass

ORDINAL_FORMS = ("arabic", "zero-padded", "roman", "kanji", "kanji-formal")
PLACEHOLDERS = ("ordinal", "title", "secondary")

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

    @property
    def fields(self) -> frozenset[str]:
        return frozenset(value for kind, value in self.parts if kind == "field")


def parse_template(source: str) -> HeaderTemplate:
    """Parse ``source`` or raise ``E_VIEW_GROUP_HEADER_TEMPLATE`` for any other brace use."""
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
                raise GroupHeaderTextError("E_VIEW_GROUP_HEADER_TEMPLATE", f"unknown or unterminated placeholder in {source!r}")
            if literal:
                parts.append(("text", "".join(literal)))
                literal = []
            parts.append(("field", name))
            index = end + 1
            continue
        if char == "}":
            if source[index + 1:index + 2] != "}":
                raise GroupHeaderTextError("E_VIEW_GROUP_HEADER_TEMPLATE", f"lone closing brace in {source!r}")
            literal.append("}")
            index += 2
            continue
        literal.append(char)
        index += 1
    if literal:
        parts.append(("text", "".join(literal)))
    return HeaderTemplate(tuple(parts))


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


def render_header(template: HeaderTemplate, *, ordinal: str, title: str, secondary: str | None) -> str:
    """Substitute the placeholders; a ``{secondary}`` without a value is an error."""
    out: list[str] = []
    for kind, value in template.parts:
        if kind == "text":
            out.append(value)
        elif value == "ordinal":
            out.append(ordinal)
        elif value == "title":
            out.append(title)
        else:
            if secondary is None:
                raise GroupHeaderTextError("E_REVIEW_GROUP_HEADER_SECONDARY", "template uses {secondary} without a value")
            out.append(secondary)
    return "".join(out)


def compose_group_headers(*, group_ids: tuple[str, ...], titles: dict[str, str], secondaries: dict[str, str] | None,
                          text: str, first: str | None, ordinal: str) -> tuple[tuple[str, str], ...]:
    """Return ``(group id, header text)`` for each group in display order."""
    main = parse_template(text)
    opening = parse_template(first) if first is not None else main
    count = len(group_ids)
    result = []
    for position, group_id in enumerate(group_ids, start=1):
        template = opening if position == 1 else main
        secondary = (secondaries or {}).get(group_id) if "secondary" in template.fields else None
        if "secondary" in template.fields and not secondary:
            raise GroupHeaderTextError("E_REVIEW_GROUP_HEADER_SECONDARY", f"group {group_id}: no secondary text")
        rendered_ordinal = (format_ordinal(position, ordinal, group_count=count)
                            if "ordinal" in template.fields else "")
        result.append((group_id, render_header(template, ordinal=rendered_ordinal,
                                               title=titles.get(group_id, group_id), secondary=secondary)))
    return tuple(result)
