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
    return float(treatment.font_size * treatment.line_height)

