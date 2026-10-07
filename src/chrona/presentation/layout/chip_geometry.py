"""A label chip's padding around its text: the one rule every chip site shares (#428, #1150)."""
from __future__ import annotations

from typing import Any

from chrona.presentation.model.semantic_registry import semantic_binding


def chip_padding(theme_tokens: Any, chip_semantic: str | None, font_size: float, text_block: float) -> tuple[float, float]:
    """The inline and block padding of a label's chip; (0, 0) when the Theme declares no chip.

    Inline is `chipPadding` times the label font size and the block side is half of it, so the chip's block
    size is the text block plus a padding on each side. A role that declares `chipMinBlockSize` keeps the chip
    at least that tall: the shortfall is split above and below the text.
    """
    role = semantic_binding(chip_semantic).theme_role if chip_semantic else None
    chip = theme_tokens.label_chip(role) if role is not None else None
    if chip is None:
        return 0.0, 0.0
    inline = float(chip[0]) * font_size
    block = inline / 2
    minimum = theme_tokens.label_chip_min_block(role)
    if minimum is not None:
        block = max(block, (float(minimum) - text_block) / 2)
    return inline, block


