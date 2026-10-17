"""Preflight paint requirements for Style-selected semantic mark roles."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from chrona.presentation.model.style_fills import StyleFillIndex

from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, StyleEvaluationError, StyleOccurrence,
)
from chrona.presentation.model.theme_paint import (
    ThemePaintError, mark_paint_family, resolve_theme_paint_inputs,
)
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView


def validate_style_mark_paint(
    intents: OccurrenceStyleIndex,
    occurrences: tuple[StyleOccurrence, ...],
    fills: StyleFillIndex,
    tokens: ThemeTokenView,
    *,
    source_refs: Mapping[str, str] | None = None,
) -> None:
    """Validate selected mark-role channels before Layout measurement.

    This uses the same finite channel resolver as Scene. It reads only closed
    Theme bindings and the already-completed occurrence fill; it neither
    composes geometry nor reads source fields.
    """
    for occurrence in occurrences:
        if occurrence.primitive_family != "mark":
            continue
        intent = intents.get(occurrence.key)
        if intent is None or intent.role is None:
            continue
        role = intent.role
        rule_ids = intent.role_rule_ids or intent.matched_rule_ids
        authored_rule_ref = (source_refs or {}).get(rule_ids[0]) if rule_ids else None
        source_ref = f"{authored_rule_ref}/then/role" if authored_rule_ref else "/body/rules"
        shape = occurrence.mark_shape
        if shape not in {"point", "span", "open-span"}:
            _raise_incompatible(
                f"mark shape is missing or unsupported: {shape!r}", source_ref,
                rule_ids, occurrence, role,
            )

        fill_override = fills.get(occurrence.key)
        try:
            catalog_pattern = _has_catalog_pattern(tokens, role)
            if shape == "point":
                _validate_point_role(tokens, role, fill_override, catalog_pattern)
            else:
                family = mark_paint_family(
                    tokens, role, has_completed_catalog_pattern=catalog_pattern,
                )
                resolve_theme_paint_inputs(
                    tokens, role, family, fill_override=fill_override,
                    catalog_pattern=catalog_pattern,
                )
        except (ThemePaintError, ThemeTokenError, ValueError) as error:
            path = getattr(error, "path", f"/body/roles/{role}")
            diagnostic_id = getattr(error, "diagnostic_id", "E_THEME_TOKEN_TYPE")
            detail = getattr(error, "detail", None) or str(error)
            _raise_incompatible(
                f"cause={diagnostic_id}; themePath={path}; detail={detail}",
                source_ref, rule_ids, occurrence, role,
            )


def _validate_point_role(tokens: ThemeTokenView, role: str, fill_override: str | None,
                         catalog_pattern: bool) -> None:
    symbol = tokens.symbol(role)
    shape = symbol.get("shape")
    if isinstance(shape, Mapping) and set(shape) == {"catalog"}:
        reference = shape.get("catalog")
        if not isinstance(reference, str):
            raise ThemePaintError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol")
        glyph = tokens.catalog_glyph(reference)
        _validate_glyph_parts(tokens, role, glyph, fill_override,
                              catalog=True, catalog_pattern=catalog_pattern)
        return
    if isinstance(shape, str) and shape in {"glyph", "catalog-glyph"}:
        _validate_glyph_parts(tokens, role, symbol, fill_override,
                              catalog="viewport" in symbol,
                              catalog_pattern=catalog_pattern)
        return

    # A built-in symbol is one host primitive; only a catalogue symbol expands
    # to separately painted fill/stroke parts.
    family = mark_paint_family(tokens, role, has_completed_catalog_pattern=catalog_pattern)
    resolve_theme_paint_inputs(tokens, role, family, fill_override=fill_override,
                               catalog_pattern=catalog_pattern)


def _validate_glyph_parts(tokens: ThemeTokenView, role: str, glyph: Mapping[str, Any],
                          fill_override: str | None, *, catalog: bool,
                          catalog_pattern: bool) -> None:
    parts = glyph.get("parts")
    if not isinstance(parts, (tuple, list)) or not parts:
        raise ThemePaintError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol")
    for index, part in enumerate(parts):
        if not isinstance(part, Mapping):
            raise ThemePaintError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol/parts/{index}")
        mode = part.get("paint")
        if mode == "none" and not catalog:
            continue
        if mode not in {"fill", "stroke"}:
            raise ThemePaintError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol/parts/{index}/paint")
        family = mark_paint_family(
            tokens, role, glyph_paint_mode=str(mode),
            has_completed_catalog_pattern=catalog_pattern,
        )
        resolve_theme_paint_inputs(
            tokens, role, family,
            fill_override=fill_override,
            part_mode=str(mode),
            part_color=part.get("color") if isinstance(part.get("color"), str) else None,
            catalog_pattern=catalog_pattern,
            catalog_glyph_stroke_width=(part.get("strokeWidth") if catalog and mode == "stroke" else None),
        )


def _has_catalog_pattern(tokens: ThemeTokenView, role: str) -> bool:
    pattern = tokens.optional_pattern(role)
    return isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"


def _raise_incompatible(detail: str, source_ref: str, rule_ids: tuple[str, ...],
                        occurrence: StyleOccurrence, role: str) -> None:
    key = occurrence.key
    raise StyleEvaluationError(
        "E_STYLE_ROLE_INCOMPATIBLE",
        f"ruleIds={','.join(rule_ids)}; subject={key!r}; themeRole={role!r}; {detail}",
        source_ref,
        rule_ids,
        key,
    )
