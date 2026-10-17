"""Pure evaluation of typed Style rules against projected occurrence facts."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date
import math
from types import MappingProxyType
from typing import Any

from chrona.presentation.model.semantic_registry import purposes, semantic_ids, semantic_binding
from chrona.resources import schema_document
from chrona.presentation.style import (
    StyleEncodingOutcome,
    StyleFieldEquals,
    StyleFieldSource,
    StyleRoleOutcome,
    StyleRule,
    StyleSelector,
    StyleOutcome,
)


@dataclass(frozen=True, order=True)
class StyleOccurrenceKey:
    subject_id: str
    source_kind: str
    semantic_id: str
    row_id: str = ""
    member_id: str = ""
    column_id: str = ""
    occurrence_kind: str = ""


@dataclass(frozen=True)
class StyleFieldFact:
    name: str
    kind: str | None
    present: bool
    value: str | bool | int | float | None
    cardinality: str = "one"
    enum_values: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


def field_facts_for_item(item: Any) -> tuple[StyleFieldFact, ...]:
    """Snapshot typed field facts through one ReviewItem's source-local accessor.

    Declarations are included even when a value is absent or null. Legacy and
    undeclared fields remain opaque (``kind=None``); values are never used to
    infer their type. Style's predicate vocabulary is scalar-only, so a present
    nonscalar retains presence but has no scalar value to compare.
    """
    bindings = item.field_bindings
    object_id = item.object_id
    fields = item.fields
    descriptors = bindings.descriptors_for(object_id)
    descriptor_by_name = {descriptor.name: descriptor for descriptor in descriptors}
    aliases_by_name: dict[str, list[str]] = {}
    for role, field_name in bindings.bindings:
        aliases_by_name.setdefault(field_name, []).append(role)

    names = list(descriptor_by_name)
    if isinstance(fields, Mapping):
        names.extend(name for name in fields if isinstance(name, str) and name not in descriptor_by_name)

    facts = []
    for name in names:
        read = bindings.read_result(fields, {"field": name}, object_id=object_id)
        value = read.value if (read.value is None or isinstance(read.value, (str, bool, int, float))) else None
        descriptor = descriptor_by_name.get(name)
        facts.append(StyleFieldFact(
            name=name,
            kind=descriptor.kind if descriptor is not None else None,
            present=read.present,
            value=value,
            cardinality=descriptor.cardinality if descriptor is not None else "one",
            enum_values=descriptor.enum_values if descriptor is not None else (),
            aliases=tuple(aliases_by_name.get(name, ())),
        ))
    return tuple(facts)


@dataclass(frozen=True)
class StyleOccurrence:
    key: StyleOccurrenceKey
    purpose: str
    primitive_family: str
    original_roles: tuple[str, ...] = ()
    comparison_category: str | None = None
    column_source: str | tuple[tuple[str, str], ...] | None = None
    fields: tuple[StyleFieldFact, ...] = ()
    # Existing source-facet shape, not a selector or completed geometry.
    mark_shape: str | None = None


@dataclass(frozen=True)
class OccurrenceStyleIntent:
    key: StyleOccurrenceKey
    role: str | None
    fill: StyleEncodingOutcome | None
    matched_rule_ids: tuple[str, ...]
    role_rule_ids: tuple[str, ...]
    fill_rule_ids: tuple[str, ...]


class StyleEvaluationError(ValueError):
    """A typed Style rule cannot be applied to its declared occurrence facts."""

    def __init__(self, diagnostic_id: str, detail: str, source_ref: str = "/",
                 rule_ids: tuple[str, ...] = (), subject: StyleOccurrenceKey | None = None) -> None:
        self.diagnostic_id = diagnostic_id
        self.detail = detail
        self.source_ref = source_ref
        self.rule_ids = tuple(sorted(set(rule_ids)))
        self.subject = subject
        super().__init__(detail or diagnostic_id)


_EMPTY_STYLE_INTENTS: Mapping[str, OccurrenceStyleIntent] = MappingProxyType({})


@dataclass(frozen=True, init=False)
class OccurrenceStyleIndex:
    """Immutable intent lookup keyed by exact source occurrence identity."""

    intents: tuple[OccurrenceStyleIntent, ...]
    _by_key: Mapping[StyleOccurrenceKey, OccurrenceStyleIntent] = field(repr=False, compare=False)
    _by_occurrence: Mapping[StyleOccurrenceKey, Mapping[str, OccurrenceStyleIntent]] = field(repr=False, compare=False)

    def __init__(self, intents: tuple[OccurrenceStyleIntent, ...] = ()) -> None:
        frozen_intents = tuple(intents)
        by_key: dict[StyleOccurrenceKey, OccurrenceStyleIntent] = {}
        by_occurrence: dict[StyleOccurrenceKey, dict[str, OccurrenceStyleIntent]] = {}
        for intent in frozen_intents:
            if intent.key in by_key:
                raise StyleEvaluationError("E_STYLE_RULE_CONFLICT", "duplicate Style occurrence identity",
                                           "/", subject=intent.key)
            by_key[intent.key] = intent
            occurrence_key = replace(intent.key, semantic_id="")
            by_occurrence.setdefault(occurrence_key, {})[intent.key.semantic_id] = intent
        object.__setattr__(self, "intents", frozen_intents)
        object.__setattr__(self, "_by_key", MappingProxyType(by_key))
        object.__setattr__(self, "_by_occurrence", MappingProxyType({
            key: MappingProxyType(values) for key, values in by_occurrence.items()
        }))

    def get(self, key: StyleOccurrenceKey) -> OccurrenceStyleIntent | None:
        """Return the intent for one source occurrence, if Style matched it."""
        return self._by_key.get(key)

    def for_occurrence(self, key: StyleOccurrenceKey) -> Mapping[str, OccurrenceStyleIntent]:
        """Return all semantic intents for the exact source occurrence key."""
        return self._by_occurrence.get(replace(key, semantic_id=""), _EMPTY_STYLE_INTENTS)


_FILLABLE_MARKS = frozenset({"planned", "forecast", "actual", "snapshot"})


def _style_enum(name: str) -> frozenset[str]:
    values = schema_document("style-v0.2.schema.yaml")["$defs"][name]["enum"]
    return frozenset(value for value in values if isinstance(value, str))


def _field_source_matches(fact: StyleFieldFact, source: StyleFieldSource) -> bool:
    if source.field_name is not None:
        return fact.name == source.field_name
    if source.field_role is not None:
        return source.field_role in fact.aliases
    return False


def _fact_definitions(source: StyleFieldSource,
                      catalogue: tuple[StyleFieldFact, ...]) -> tuple[StyleFieldFact, ...]:
    return tuple(fact for fact in catalogue if _field_source_matches(fact, source))


def _literal_matches_type(value: object, fact: StyleFieldFact) -> bool:
    kind = fact.kind
    if fact.cardinality != "one":
        return False
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return ((isinstance(value, (int, float)) and not isinstance(value, bool))
                and (not isinstance(value, float) or math.isfinite(value)))
    if kind == "enum":
        return isinstance(value, str) and (not fact.enum_values or value in fact.enum_values)
    if kind == "date":
        if not isinstance(value, str):
            return False
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if kind in {"string", "objectReference"}:
        return isinstance(value, str)
    return False


def _fact_equals_literal(fact: StyleFieldFact, literal: object) -> bool:
    value = fact.value
    if fact.kind == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and isinstance(literal, (int, float)) and not isinstance(literal, bool)
                and (not isinstance(value, float) or math.isfinite(value))
                and (not isinstance(literal, float) or math.isfinite(literal))
                and value == literal)
    if fact.kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool) and type(literal) is int and value == literal
    if fact.kind == "boolean":
        return type(value) is bool and type(literal) is bool and value == literal
    return type(value) is type(literal) and value == literal


def _canonical_column_source(source: str | tuple[tuple[str, str], ...] | None) -> str | tuple[tuple[str, str], ...] | None:
    if isinstance(source, tuple):
        return tuple(sorted(source))
    return source


def _validate_selector(selector: StyleSelector, rule: StyleRule,
                       catalogue: tuple[StyleFieldFact, ...]) -> None:
    if selector.semantic is not None and selector.semantic not in semantic_ids():
        raise StyleEvaluationError("E_STYLE_FACT_UNKNOWN", f"unknown semantic {selector.semantic!r}",
                                   f"{rule.source_ref}/when/semantic", (rule.rule_id,))
    if selector.purpose is not None and selector.purpose not in purposes():
        raise StyleEvaluationError("E_STYLE_FACT_UNKNOWN", f"unknown purpose {selector.purpose!r}",
                                   f"{rule.source_ref}/when/purpose", (rule.rule_id,))
    if selector.comparison_category is not None and selector.comparison_category not in _style_enum("comparisonCategory"):
        raise StyleEvaluationError("E_STYLE_FACT_UNKNOWN",
                                   f"unknown comparison category {selector.comparison_category!r}",
                                   f"{rule.source_ref}/when/comparisonCategory", (rule.rule_id,))
    allowed_roles = _style_enum("projectedStyleRole")
    unknown_roles = tuple(role for role in selector.roles if role not in allowed_roles)
    if unknown_roles:
        raise StyleEvaluationError("E_STYLE_FACT_UNKNOWN", f"unknown original role {unknown_roles[0]!r}",
                                   f"{rule.source_ref}/when/roles", (rule.rule_id,))
    for index, predicate in enumerate(selector.fields):
        definitions = _fact_definitions(predicate.source, catalogue)
        ref = f"{rule.source_ref}/when/fields/{index}"
        typed_definitions = tuple(definition for definition in definitions if definition.kind is not None)
        if not typed_definitions:
            source_name = predicate.source.field_name or predicate.source.field_role or "?"
            raise StyleEvaluationError("E_STYLE_FACT_UNKNOWN", f"unknown field source {source_name!r}",
                                       ref, (rule.rule_id,))
        if not any(_literal_matches_type(predicate.equals, definition) for definition in typed_definitions):
            raise StyleEvaluationError("E_STYLE_FACT_TYPE",
                                       "field equality is incompatible with its declared scalar type/cardinality",
                                       ref, (rule.rule_id,))


def _validate_rule_target(rule: StyleRule) -> None:
    outcome = rule.outcome
    if not isinstance(outcome, StyleEncodingOutcome):
        return
    if outcome.channel != "fill":
        raise StyleEvaluationError("E_STYLE_TARGET", "only the fill channel is supported",
                                   f"{rule.source_ref}/then/encode/channel", (rule.rule_id,))
    candidate_semantics = {
        semantic for semantic in semantic_ids()
        if (semantic in _FILLABLE_MARKS and semantic_binding(semantic).primitive_kind == "mark")
        or semantic_binding(semantic).purpose == "table-cell"
    }
    if rule.selector.semantic is not None:
        candidate_semantics.intersection_update((rule.selector.semantic,))
    if rule.selector.purpose is not None:
        candidate_semantics.intersection_update(
            semantic for semantic in semantic_ids()
            if semantic_binding(semantic).purpose == rule.selector.purpose
        )
    if not candidate_semantics:
        raise StyleEvaluationError("E_STYLE_TARGET", "fill selector cannot target an admitted mark or table cell",
                                   f"{rule.source_ref}/then/encode", (rule.rule_id,))


def _predicate_matches(predicate: StyleFieldEquals, occurrence: StyleOccurrence) -> bool:
    return any(
        fact.present and _literal_matches_type(predicate.equals, fact)
        and _fact_equals_literal(fact, predicate.equals)
        for fact in occurrence.fields if _field_source_matches(fact, predicate.source)
    )


def _matches(selector: StyleSelector, occurrence: StyleOccurrence) -> bool:
    return (
        (selector.semantic is None or selector.semantic == occurrence.key.semantic_id)
        and (selector.purpose is None or selector.purpose == occurrence.purpose)
        and (selector.comparison_category is None
             or selector.comparison_category == occurrence.comparison_category)
        and (selector.column_source is None
             or _canonical_column_source(selector.column_source)
             == _canonical_column_source(occurrence.column_source))
        and all(role in occurrence.original_roles for role in selector.roles)
        and all(_predicate_matches(predicate, occurrence) for predicate in selector.fields)
    )


def _resolved_encoding(outcome: StyleEncodingOutcome,
                        occurrence: StyleOccurrence) -> StyleEncodingOutcome:
    source = outcome.source
    matching_names = tuple(dict.fromkeys(
        fact.name for fact in occurrence.fields if _field_source_matches(fact, source)
    ))
    if len(matching_names) == 1:
        resolved_source = StyleFieldSource(field_name=matching_names[0])
    elif len(matching_names) > 1:
        raise StyleEvaluationError("E_STYLE_FACT_TYPE", "field-role source is ambiguous for occurrence",
                                   "/", subject=occurrence.key)
    else:
        resolved_source = source
    # Legend wording is presentation metadata, not encoding identity. S2 owns it.
    return StyleEncodingOutcome(outcome.channel, resolved_source, outcome.scale_id,
                                outcome.domain, None)


def _encoding_identity(outcome: StyleEncodingOutcome) -> tuple[Any, ...]:
    source = outcome.source
    return (outcome.channel, source.field_name, source.field_role,
            outcome.scale_id, outcome.domain)


def _validate_target(rule: StyleRule, occurrence: StyleOccurrence) -> None:
    outcome = rule.outcome
    if not isinstance(outcome, StyleEncodingOutcome):
        return
    binding = semantic_binding(occurrence.key.semantic_id)
    fillable = ((occurrence.key.semantic_id in _FILLABLE_MARKS
                 and binding.primitive_kind == "mark")
                or occurrence.purpose == "table-cell")
    if outcome.channel != "fill" or not fillable:
        raise StyleEvaluationError("E_STYLE_TARGET",
                                   f"fill channel cannot target semantic={occurrence.key.semantic_id!r} "
                                   f"purpose={occurrence.purpose!r}", rule.source_ref,
                                   (rule.rule_id,), occurrence.key)


def evaluate_style_rules(
    rules: tuple[StyleRule, ...],
    occurrences: tuple[StyleOccurrence, ...],
    *,
    field_catalogue: tuple[StyleFieldFact, ...] = (),
) -> tuple[OccurrenceStyleIntent, ...]:
    """Evaluate rule intersections over immutable original occurrence facts.

    Rule admission is independent of whether any current occurrence matches, so
    unknown or mistyped selectors fail deterministically on an empty input too.
    """
    catalogue_by_key: dict[tuple[Any, ...], StyleFieldFact] = {}
    for fact in (*field_catalogue, *(field for occurrence in occurrences for field in occurrence.fields)):
        if fact.name:
            catalogue_by_key[(fact.name, fact.kind, fact.cardinality, fact.enum_values, fact.aliases)] = fact
    catalogue = tuple(catalogue_by_key.values())

    ordered_rules = tuple(sorted(rules, key=lambda item: (item.rule_id, item.source_ref)))
    for rule in ordered_rules:
        _validate_selector(rule.selector, rule, catalogue)
        _validate_rule_target(rule)

    intents: list[OccurrenceStyleIntent] = []
    occurrence_keys: set[StyleOccurrenceKey] = set()
    for occurrence in occurrences:
        if occurrence.key in occurrence_keys:
            raise StyleEvaluationError("E_STYLE_RULE_CONFLICT", "duplicate Style occurrence identity", "/",
                                       subject=occurrence.key)
        occurrence_keys.add(occurrence.key)
        if occurrence.key.semantic_id not in semantic_ids() or occurrence.purpose not in purposes():
            raise StyleEvaluationError("E_STYLE_FACT_UNKNOWN",
                                       "occurrence has unknown semantic or purpose", "/",
                                       subject=occurrence.key)
        binding = semantic_binding(occurrence.key.semantic_id)
        if occurrence.purpose != binding.purpose or occurrence.primitive_family != binding.primitive_kind:
            raise StyleEvaluationError("E_STYLE_FACT_TYPE",
                                       "occurrence purpose or primitive family disagrees with its semantic binding",
                                       "/", subject=occurrence.key)
        assignments: list[tuple[StyleRule, StyleOutcome]] = []
        for rule in ordered_rules:
            if _matches(rule.selector, occurrence):
                _validate_target(rule, occurrence)
                outcome = (_resolved_encoding(rule.outcome, occurrence)
                           if isinstance(rule.outcome, StyleEncodingOutcome) else rule.outcome)
                assignments.append((rule, outcome))
        if not assignments:
            continue

        role_assignments: dict[str, list[str]] = {}
        fill_assignments: dict[tuple[Any, ...], tuple[StyleEncodingOutcome, list[str]]] = {}
        for rule, outcome in assignments:
            if isinstance(outcome, StyleRoleOutcome):
                role_assignments.setdefault(outcome.role, []).append(rule.rule_id)
            else:
                identity = _encoding_identity(outcome)
                if identity not in fill_assignments:
                    fill_assignments[identity] = (outcome, [])
                fill_assignments[identity][1].append(rule.rule_id)
        conflicts = (len(role_assignments) > 1 or len(fill_assignments) > 1)
        if conflicts:
            rule_ids = tuple(rule.rule_id for rule, _ in assignments)
            raise StyleEvaluationError("E_STYLE_RULE_CONFLICT",
                                       "matching Style rules assign conflicting role or fill outcomes",
                                       assignments[0][0].source_ref, rule_ids, occurrence.key)
        role = next(iter(role_assignments), None)
        fill, fill_ids = next(iter(fill_assignments.values()), (None, []))
        role_ids = tuple(sorted(next(iter(role_assignments.values()), [])))
        fill_rule_ids = tuple(sorted(fill_ids))
        matched_ids = tuple(sorted(rule.rule_id for rule, _ in assignments))
        intents.append(OccurrenceStyleIntent(occurrence.key, role, fill, matched_ids,
                                             role_ids, fill_rule_ids))
    return tuple(intents)
