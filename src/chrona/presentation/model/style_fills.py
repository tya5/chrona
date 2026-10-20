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
from chrona.presentation.style import EncodingSource, EncodingWitness


@dataclass(frozen=True)
class CompletedStyleFill:
    """One resolved colour and the passive encoding identity that selected it."""

    color: str
    encoding: EncodingWitness

    def __post_init__(self) -> None:
        if not isinstance(self.color, str) or not self.color or not isinstance(self.encoding, EncodingWitness):
            raise ValueError("completed Style fill requires a colour and typed encoding witness")


@dataclass(frozen=True, init=False)
class StyleFillIndex:
    """Concrete occurrence-local colours and their completed encoding witnesses."""

    completed_fills: tuple[tuple[StyleOccurrenceKey, CompletedStyleFill], ...]
    scales: tuple[ResolvedColorScale, ...]
    _by_key: Mapping[StyleOccurrenceKey, CompletedStyleFill] = field(repr=False, compare=False)

    def __init__(self, completed_fills: tuple[tuple[StyleOccurrenceKey, CompletedStyleFill], ...] = (),
                 scales: tuple[ResolvedColorScale, ...] = ()) -> None:
        values = tuple((key, completed) for key, completed in completed_fills)
        index = dict(values)
        if len(index) != len(values):
            raise ValueError("duplicate completed Style fill occurrence")
        if any(not isinstance(value, CompletedStyleFill) for _, value in values):
            raise ValueError("completed Style fills require color and encoding witness")
        if any(not isinstance(key, StyleOccurrenceKey) for key, _ in values):
            raise ValueError("completed Style fills require exact occurrence keys")
        object.__setattr__(self, "completed_fills", values)
        object.__setattr__(self, "scales", tuple(scales))
        object.__setattr__(self, "_by_key", MappingProxyType(index))

    def get(self, key: StyleOccurrenceKey | None) -> str | None:
        value = self._by_key.get(key) if key is not None else None
        return value.color if value is not None else None

    def completed(self, key: StyleOccurrenceKey | None) -> CompletedStyleFill | None:
        return self._by_key.get(key) if key is not None else None

    @property
    def fills(self) -> tuple[tuple[StyleOccurrenceKey, str], ...]:
        return tuple((key, completed.color) for key, completed in self.completed_fills)


def _profile_lacks_field(facts, field_name: str) -> bool:
    """True when the occurrence's object has a declared profile that does not declare ``field_name``.

    A typed fact (``kind`` set) comes only from a declaration, so an object with none is untyped and keeps the
    Spec 60 behaviour. A field the object nevertheless carries a value for is never exempt.
    """
    typed = [fact for fact in facts if fact.kind is not None]
    return bool(typed) and not any(fact.name == field_name and (fact.kind is not None or fact.present) for fact in facts)


def complete_style_fills(
    intents: OccurrenceStyleIndex, occurrences: tuple[StyleOccurrence, ...],
    *, theme: Mapping[str, object] | None = None,
    legacy_scale: ResolvedColorScale | None = None,
    reserved: tuple[str, ...] = (), other_color: str | None = None,
    encoding_sources: Mapping[str, EncodingSource],
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
    reference_identities: dict[tuple[str, str], tuple[str, str, str]] = {}

    def sources(intent: OccurrenceStyleIntent) -> tuple[EncodingSource, ...]:
        try:
            result = tuple(encoding_sources[rule_id] for rule_id in intent.fill_rule_ids)
        except KeyError as error:
            raise ValueError(f"missing encoding source for rule {error.args[0]!r}") from error
        if not result or len(set(result)) != len(result):
            raise ValueError("encoding origins must be non-empty and unique")
        return result

    def source_reference(intent: OccurrenceStyleIntent) -> str:
        return sources(intent)[0].source_ref

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
        # Resolve all origins now. A later unfillable value must not silently
        # lose the identity that was needed to explain its encoded colour.
        sources(intent)
        field_name = encoding.source.field_name
        field_fact = next((fact for fact in occurrence.fields
                           if fact.name == field_name and fact.present), None)
        value = field_fact.value if field_fact is not None else None
        if (field_fact is not None and field_fact.non_scalar_value
                and not _profile_lacks_field(occurrence.fields, field_name)):
            raise ColorScaleError(
                "E_PRESENTATION_SCALE_VALUE",
                f"object={intent.key.subject_id!r}, field={field_name!r}, valueType={field_fact.non_scalar_type or 'non-scalar'}; expected a scalar value in the encoding domain",
                source_reference(intent),
            )
        if (field_fact is not None and field_fact.reference_identity is not None
                and isinstance(value, str)):
            domain_key = (scale_id, value)
            previous_identity = reference_identities.get(domain_key)
            if previous_identity is not None and previous_identity != field_fact.reference_identity:
                raise ColorScaleError(
                    "E_PRESENTATION_SCALE_VALUE",
                    f"object={intent.key.subject_id!r}, field={field_name!r}, value={value!r} resolves to different reference targets within scale {scale_id!r}; use separate scales for distinct target identities",
                    source_reference(intent),
                )
            reference_identities[domain_key] = field_fact.reference_identity
        groups.setdefault(scale_id, []).append((intent, field_name, value))

    for intent in intents.intents:
        if intent.fill is not None and intent.key not in facts:
            # The index normally carries only projected occurrences. Retain
            # the prior failure mode for a dangling index key.
            raise KeyError(intent.key)
    body = theme.get("body", {}) if isinstance(theme, Mapping) else {}
    fills: list[tuple[StyleOccurrenceKey, CompletedStyleFill]] = []
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
                 "domain": policy, "missing": "base"},
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
            if _profile_lacks_field(facts[intent.key].fields, field_name):
                continue  # the occurrence's declared profile has no such field: the encoding does not apply (#1682)
            if value is None:
                # No value for the field (absent from any source, or null): the encoding does not apply (#1789).
                # Base paint is the default; `missing` names a domain value to paint with instead.
                missing = intent.fill.missing
                if missing == "base":
                    continue
                if missing not in local_scale.domain:
                    raise ColorScaleError(
                        "E_PRESENTATION_SCALE_MAPPING",
                        f"encoding.missing={missing!r} is not base or a value of the domain "
                        f"{local_scale.domain!r}", source_reference(intent))
                value = missing
                fields = {field_name: value}
            if local_scale.covers(fields):
                color = local_scale.color_for(intent.key.subject_id, fields)
                canonical_value = scale_text(value)
                if canonical_value is None:  # color_for already enforces this for a covered scale
                    raise ValueError("covered encoded value has no canonical scale text")
                witness = EncodingWitness(
                    channel=intent.fill.channel,
                    scale_id=intent.fill.scale_id,
                    field=str(field_name),
                    value=canonical_value,
                    sources=sources(intent),
                )
                fills.append((intent.key, CompletedStyleFill(color, witness)))
    return StyleFillIndex(tuple(fills), tuple(scales))
