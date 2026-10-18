"""Complete evaluated fill intents once, retaining exact source occurrences."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from chrona.presentation.model.color_scale import (
    ColorScaleError, ResolvedColorScale, resolve_color_scale, scale_text,
)
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrence, StyleOccurrenceKey,
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

    One named scale completes once across its source-local field aliases. The
    preclosed View domain remains the prefix of a first-appearance domain.
    """
    facts = {occurrence.key: occurrence for occurrence in occurrences}
    intents_by_key = {intent.key: intent for intent in intents.intents}
    groups: dict[str, list[tuple[OccurrenceStyleIntent, str | None, object]]] = {}
    policies: dict[str, tuple[str, ...] | str] = {}
    references: dict[str, str] = {}

    def source_reference(intent: OccurrenceStyleIntent) -> str:
        fill_rule_ids = intent.fill_rule_ids
        source_ref = (source_refs or {}).get(fill_rule_ids[0], "/body/rules")
        return source_ref if source_ref == "/body/colorEncoding" else source_ref + "/then/encode"

    # Iterate source occurrences, not rule or encoding declarations, so a
    # first-appearance scale follows the same order as the View projection.
    for occurrence in occurrences:
        intent = intents_by_key.get(occurrence.key)
        if intent is None or intent.fill is None:
            continue
        encoding = intent.fill
        scale_id = encoding.scale_id
        policy = encoding.domain
        previous = policies.get(scale_id)
        if previous is not None and previous != policy:
            raise ColorScaleError(
                "E_PRESENTATION_SCALE_MAPPING",
                f"scale {scale_id!r} has incompatible domain policies "
                f"{previous!r} and {policy!r}",
                source_reference(intent),
            )
        policies[scale_id] = policy
        references.setdefault(scale_id, source_reference(intent))
        field_name = encoding.source.field_name
        value = next((fact.value for fact in occurrence.fields
                      if fact.name == field_name and fact.present), None)
        groups.setdefault(scale_id, []).append((intent, field_name, value))

    for intent in intents.intents:
        if intent.fill is not None and intent.key not in facts:
            # The index normally carries only projected occurrences. Retain
            # the prior failure mode for a dangling index key.
            raise KeyError(intent.key)
    body = theme.get("body", {}) if isinstance(theme, Mapping) else {}
    fills = []
    scales = []
    for scale_id, group in groups.items():
        policy = policies[scale_id]
        legacy_policy: tuple[str, ...] | str | None = None
        if legacy_scale is not None and legacy_scale.scale_id == scale_id:
            legacy_policy = ("firstAppearance" if legacy_scale.derived
                             else legacy_scale.domain)
            if policy != legacy_policy:
                raise ColorScaleError(
                    "E_PRESENTATION_SCALE_MAPPING",
                    f"scale {scale_id!r} has incompatible domain policies "
                    f"{legacy_policy!r} and {policy!r}",
                    source_reference(group[0][0]),
                )

        observed: list[str] = []
        if policy == "firstAppearance" and legacy_scale is not None \
                and legacy_scale.scale_id == scale_id:
            observed.extend(legacy_scale.domain)
        observed.extend(text for _, _, value in group
                        if (text := scale_text(value)) is not None)
        observed_domain = tuple(dict.fromkeys(observed))

        if (legacy_scale is not None and legacy_scale.scale_id == scale_id
                and (policy != "firstAppearance" or observed_domain == legacy_scale.domain)):
            # Reuse the precise preclosed object whenever the union adds no
            # domain values; callers retain legacy scale identity and bytes.
            scale = legacy_scale
        else:
            source_field = group[0][1]
            scale = resolve_color_scale(
                {"scale": scale_id, "source": {"field": source_field},
                 "domain": policy},
                body.get("colorScales"), body.get("categorySlots"),
                source_ref=references[scale_id],
                color_vision=tuple(body.get("colorVision", ())),
                observed=observed_domain,
                reserved=reserved, other_color=other_color,
            )
        if scale is None:
            continue
        scales.append(scale)
        for intent, field_name, value in group:
            source_ref = source_reference(intent)
            local_scale = (scale if (scale.source_field == field_name
                                     and scale.encoding_source_ref == source_ref)
                           else replace(scale, source_field=field_name,
                                        encoding_source_ref=source_ref))
            fields = {field_name: value}
            if local_scale.covers(fields):
                fills.append((intent.key, local_scale.color_for(intent.key.subject_id, fields)))
    return StyleFillIndex(tuple(fills), tuple(scales))
