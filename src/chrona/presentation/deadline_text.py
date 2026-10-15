"""Closed deadline copy; Core owns the count and Layout owns its geometry."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.presentation.count_text import CountTextFormat, format_count
from chrona.presentation.group_header_text import HeaderTemplate, parse_template


@dataclass(frozen=True)
class DeadlineCaptionText:
    template: HeaderTemplate
    text_format: CountTextFormat = CountTextFormat()

    def bind(self, days_late: int) -> str:
        # A literal-only template does not read a number or require its names.
        number = format_count(days_late, self.text_format) if self.template.fields else ""
        return "".join(value if kind == "text" else number for kind, value in self.template.parts)


def compile_deadline_caption(source: str, text_format: CountTextFormat = CountTextFormat()) -> DeadlineCaptionText:
    return DeadlineCaptionText(parse_template(
        source, placeholders=("daysLate",), allow_figures=False, allow_roles=False,
        code="E_VIEW_DEADLINE_CAPTION_TEMPLATE"), text_format)
