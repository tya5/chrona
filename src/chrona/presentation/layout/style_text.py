"""Resolve selected Style typography before text measurement."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.semantic_registry import ContrastClass, semantic_binding
from chrona.presentation.model.surface_content import SurfaceContentInput, TableContent
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrenceKey,
)
from chrona.presentation.model.theme_tokens import ThemeTokenError


def resolve_text_style_intent(key: StyleOccurrenceKey | None, index: OccurrenceStyleIndex,
                              theme_tokens: Any) -> OccurrenceStyleIntent | None:
    """Validate one exact text occurrence's selected treatment before fitting."""
    intent = index.get(key) if key is not None else None
    if intent is None or intent.role is None:
        return None
    role = intent.role
    try:
        theme_tokens.text_treatment(role)
        theme_tokens.color(role, "fill")
        if semantic_binding(key.semantic_id).contrast_class is ContrastClass.STATE_TEXT:
            theme_tokens.contrast_treatment(role)
    except ThemeTokenError as error:
        raise LayoutError(
            "E_STYLE_ROLE_INCOMPATIBLE", error.path, key.subject_id,
            f"ruleIds={','.join(intent.role_rule_ids)}; subject={key!r}; "
            f"source={key.subject_id!r}; themeRole={role!r}; "
            f"cause={error.diagnostic_id}; detail={error.detail or ''}",
        ) from error
    return intent


def resolve_table_cell_typography(content: SurfaceContentInput, table: TableContent,
                                  theme_tokens: Any) -> tuple[SurfaceContentInput, TableContent]:
    """Resolve selected cell roles once, before either source or final measurement.

    The normalized table is the canonical cell sequence at this boundary. Both
    downstream consumers receive that same tuple, while an unstyled table
    preserves the original immutable values by identity.
    """
    index = content.style_intents
    if not index.intents or not table.cells:
        return content, table

    cells = []
    changed = False
    for cell in table.cells:
        key = cell.style_key
        intent = resolve_text_style_intent(key, index, theme_tokens)
        if intent is None:
            cells.append(cell)
            continue
        cells.append(replace(cell, typography_role=intent.role))
        changed = True

    if not changed:
        return content, table
    resolved_cells = tuple(cells)
    return replace(content, table_cells=resolved_cells), replace(table, cells=resolved_cells)
