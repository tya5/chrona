"""The vertical group tag column (#585): a group label written vertically spans its rows beside the table."""
from __future__ import annotations

from typing import Any


def vertical_group_tags(request: Any) -> bool:
    """True when group labels are shown (presentation header) and the `groupHeader` role declares a vertical writing mode."""
    tokens = request.theme_tokens
    return (request.surface_content.group_presentation == "header" and tokens is not None
            and tokens.writing_mode("groupHeader") == "vertical")


def group_tag_column_size(theme_tokens: Any) -> float:
    """The column's inline size: the role's line box, the block extent of a vertical line."""
    treatment = theme_tokens.text_treatment("groupHeader")
    from chrona.presentation.layout.surface_groups import resolve_group_tab
    tab = resolve_group_tab(theme_tokens)
    padding = 2 * tab.gap if tab is not None and tab.target == "tag" else 0
    return float(treatment.font_size * treatment.line_height + padding)



def header_child_lead(theme_tokens: Any, *, first_column: bool) -> float | None:
    """Where a header group's rows start relative to the header's label (#1065), or None when no header row is drawn.

    A vertical `groupHeader` draws a tag column and no header row, so rows are not below a header. Otherwise the
    header label starts at the table start, after a start group tab and its gap (#882); that distance is the lead
    of a row's label in the first column. Another column has no header label above it, so its lead is 0.
    """
    if theme_tokens.writing_mode("groupHeader") == "vertical":
        return None
    if not first_column:
        return 0.0
    from chrona.presentation.layout.surface_groups import resolve_group_tab
    tab = resolve_group_tab(theme_tokens)
    return float(tab.reserved) if tab is not None and tab.position == "start" else 0.0
