"""Complete evaluated fill intents once, retaining exact source occurrences."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from chrona.presentation.model.color_scale import ResolvedColorScale, resolve_color_scale, scale_text
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, StyleOccurrence, StyleOccurrenceKey,
)


@dataclass(frozen=True, init=False)
class StyleFillIndex:
    """Concrete colours, never a field lookup or an object-global override."""

    fills: tuple[tuple[StyleOccurrenceKey, str], ...]
    scales: tuple[ResolvedColorScale, ...]
    _by_key: Mapping[StyleOccurrenceKey, str] = field(repr=False, compare=False)

    def __init__(self, fills: tuple[tuple[StyleOccurrenceKey, str], ...] = (),
                 scales: tuple[ResolvedColorScale, ...] = ()) -> None:
        values = tuple((key, color) for key, color in fills)
        index = dict(values)
        if len(index) != len(values):
            raise ValueError("duplicate completed Style fill occurrence")
        object.__setattr__(self, "fills", values)
        object.__setattr__(self, "scales", tuple(scales))
        object.__setattr__(self, "_by_key", MappingProxyType(index))

    def get(self, key: StyleOccurrenceKey | None) -> str | None:
        return self._by_key.get(key) if key is not None else None


def complete_style_fills(
    intents: OccurrenceStyleIndex, occurrences: tuple[StyleOccurrence, ...],
    *, theme: Mapping[str, object] | None = None,
    legacy_scale: ResolvedColorScale | None = None,
    reserved: tuple[str, ...] = (), other_color: str | None = None,
    source_refs: Mapping[str, str] | None = None,
) -> StyleFillIndex:
    """Use the existing total scale resolver against immutable original facts.

    Equal encoding identities share scale completion, not their source values.
    The preclosed View scale retains its original first-appearance domain order.
    """
    facts = {occurrence.key: occurrence for occurrence in occurrences}
    groups = {}
    for intent in intents.intents:
        if intent.fill is not None:
            groups.setdefault(intent.fill, []).append(intent)
    body = theme.get("body", {}) if isinstance(theme, Mapping) else {}
    fills = []
    scales = []
    for encoding, group in groups.items():
        field_name = encoding.source.field_name
        encoding_values = [
            next((fact.value for fact in facts[intent.key].fields
                  if fact.name == field_name and fact.present), None)
            for intent in group
        ]
        if (legacy_scale is not None
                and (encoding.scale_id, field_name, encoding.domain)
                == (legacy_scale.scale_id, legacy_scale.source_field,
                    "firstAppearance" if legacy_scale.derived else legacy_scale.domain)):
            scale = legacy_scale
        else:
            scale = resolve_color_scale(
                {"scale": encoding.scale_id, "source": {"field": field_name},
                 "domain": encoding.domain},
                body.get("colorScales"), body.get("categorySlots"),
                source_ref=(source_refs or {}).get(group[0].fill_rule_ids[0], "/body/rules")
                           + "/then/encode",
                color_vision=tuple(body.get("colorVision", ())),
                observed=tuple(text for value in encoding_values if (text := scale_text(value)) is not None),
                reserved=reserved, other_color=other_color,
            )
        if scale is None:
            continue
        scales.append(scale)
        for intent, value in zip(group, encoding_values):
            fields = {field_name: value}
            if scale.covers(fields):
                fills.append((intent.key, scale.color_for(intent.key.subject_id, fields)))
    return StyleFillIndex(tuple(fills), tuple(scales))
