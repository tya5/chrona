"""Bind legacy View scale legend candidates to exact selected occurrences."""
from __future__ import annotations

from dataclasses import replace

from chrona.presentation.model.color_scale import ResolvedColorScale, scale_text
from chrona.presentation.model.style_rules import StyleOccurrence, StyleOccurrenceKey
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.style import StyleRule


def bind_view_legend_witnesses(
    content: SurfaceContentInput,
    occurrences: tuple[StyleOccurrence, ...],
    encoding_rules: tuple[StyleRule, ...],
    color_scale: ResolvedColorScale | None,
) -> SurfaceContentInput:
    """Attach exact View-scale intent keys to matching potential legend entries.

    The completed Style fill index supplies the union scale domain. This only
    binds provenance; Layout later decides which completed paints are visible.
    """
    if color_scale is None:
        return content
    scale = next((candidate for candidate in content.style_fills.scales
                  if candidate.scale_id == color_scale.scale_id), None)
    if scale is None:
        return content

    view_rule_ids = {rule.rule_id for rule in encoding_rules}
    keys_by_ref: dict[str, list[StyleOccurrenceKey]] = {}
    for occurrence in occurrences:
        intent = content.style_intents.get(occurrence.key)
        if (intent is None or intent.fill is None
                or intent.fill.scale_id != color_scale.scale_id
                or not view_rule_ids.intersection(intent.fill_rule_ids)):
            continue
        source = intent.fill.source
        field_name = source.field_name
        if field_name is None:
            continue
        fact = next((item for item in occurrence.fields
                     if item.name == field_name and item.present), None)
        value = scale_text(fact.value) if fact is not None else None
        if value is None:
            continue
        for source_ref, _, _ in scale.legend_items({value}):
            keys_by_ref.setdefault(source_ref, []).append(occurrence.key)

    candidates = {source_ref for value in scale.domain
                  for source_ref, _, _ in scale.legend_items({value})}
    entries = []
    changed = False
    for entry in content.legend_entries:
        if entry.style_scope is not None:
            entries.append(entry)
            continue
        identity = entry.source_ref if entry.source_ref in candidates else entry.role
        if identity not in candidates:
            entries.append(entry)
            continue
        keys = tuple(keys_by_ref.get(identity, ()))
        entries.append(replace(entry, style_occurrences=keys))
        changed = changed or entry.style_occurrences != keys
    return replace(content, legend_entries=tuple(entries)) if changed else content
