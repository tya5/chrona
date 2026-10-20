"""Immutable values for the authored Style contract.

The resource schema owns structural validation. ``parse_style_rules`` is the
small typed conversion used after that validation at the contract boundary; it
does not evaluate rules or resolve Project fields.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import json
import math
from typing import Any


Scalar = str | bool | int | float


@dataclass(frozen=True)
class StyleFieldSource:
    field_name: str | None = None
    field_role: str | None = None


@dataclass(frozen=True)
class StyleFieldEquals:
    source: StyleFieldSource
    equals: Scalar


@dataclass(frozen=True)
class StyleSelector:
    semantic: str | None = None
    purpose: str | None = None
    comparison_category: str | None = None
    column_source: str | tuple[tuple[str, str], ...] | None = None
    roles: tuple[str, ...] = ()
    fields: tuple[StyleFieldEquals, ...] = ()


@dataclass(frozen=True)
class StyleLegend:
    title: str | None = None
    show_scope: bool = False


@dataclass(frozen=True)
class StyleRoleOutcome:
    role: str


@dataclass(frozen=True)
class StyleEncodingOutcome:
    channel: str
    source: StyleFieldSource
    scale_id: str
    domain: tuple[str, ...] | str
    legend: StyleLegend | None = None
    # Paint for an object with no value for the field: "base" keeps the role's own paint, else a domain value (#1789).
    missing: str = "base"


StyleOutcome = StyleRoleOutcome | StyleEncodingOutcome


@dataclass(frozen=True)
class EncodingSource:
    """Passive identity of one authored resource that supplied an encoding."""

    kind: str
    resource_id: str
    source_ref: str
    rule_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in {"view", "style"}:
            raise ValueError("encoding source kind must be 'view' or 'style'")
        if (not isinstance(self.resource_id, str) or not self.resource_id
                or not isinstance(self.source_ref, str) or not self.source_ref):
            raise ValueError("encoding source needs non-empty resource identity and source pointer")
        if self.kind == "style":
            if not isinstance(self.rule_id, str) or not self.rule_id:
                raise ValueError("Style encoding source needs an authored rule ID")
        elif self.rule_id is not None:
            raise ValueError("View encoding source cannot have a rule ID")

    def as_mapping(self) -> dict[str, str]:
        return {"kind": self.kind, "id": self.resource_id, "sourceRef": self.source_ref,
                **({"ruleId": self.rule_id} if self.rule_id is not None else {})}

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EncodingSource":
        if not isinstance(raw, Mapping):
            raise ValueError("encoding source must be an object")
        kind = raw.get("kind")
        expected = {"kind", "id", "sourceRef", *(('ruleId',) if kind == "style" else ())}
        if set(raw) != expected:
            raise ValueError("encoding source has missing or unsupported members")
        return cls(kind, raw["id"], raw["sourceRef"], raw.get("ruleId"))


@dataclass(frozen=True)
class EncodingWitness:
    """Completed passive identity/value for a fill supplied by an encoding."""

    channel: str
    scale_id: str
    field: str
    value: str
    sources: tuple[EncodingSource, ...]

    def __post_init__(self) -> None:
        if self.channel != "fill":
            raise ValueError("encoding witness channel must be 'fill'")
        if (not isinstance(self.scale_id, str) or not self.scale_id
                or not isinstance(self.field, str) or not self.field
                or not isinstance(self.value, str)):
            raise ValueError("encoding witness needs scale, field, and canonical string value")
        if (not isinstance(self.sources, tuple) or not self.sources
                or any(not isinstance(source, EncodingSource) for source in self.sources)
                or len(set(self.sources)) != len(self.sources)):
            raise ValueError("encoding witness needs non-empty unique source records")

    def as_mapping(self) -> dict[str, Any]:
        return {"channel": self.channel, "scaleId": self.scale_id, "field": self.field,
                "value": self.value, "sources": [source.as_mapping() for source in self.sources]}

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EncodingWitness":
        if not isinstance(raw, Mapping) or set(raw) != {"channel", "scaleId", "field", "value", "sources"}:
            raise ValueError("encoding witness has missing or unsupported members")
        sources = raw["sources"]
        if not isinstance(sources, (tuple, list)):
            raise ValueError("encoding witness sources must be an array")
        return cls(raw["channel"], raw["scaleId"], raw["field"], raw["value"],
                   tuple(EncodingSource.from_mapping(source) for source in sources))


@dataclass(frozen=True)
class StyleMatch:
    """Passive provenance for authored Style rules that treated one occurrence."""

    style_id: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class StyleLegendScope:
    """Passive authored scope attached to a completed Style legend swatch."""

    style_id: str
    rule_id: str
    scale_id: str
    selector: str
    title: str | None
    show_scope: bool


@dataclass(frozen=True)
class StyleRule:
    rule_id: str
    selector: StyleSelector
    outcome: StyleOutcome
    source_ref: str
    style_id: str | None = None
    authored_rule_id: str | None = None


def bind_style_rules(style_id: str, rules: tuple[StyleRule, ...]) -> tuple[StyleRule, ...]:
    """Qualify immutable rule identities without losing authored diagnostics.

    JSON tuple framing cannot alias a lowered View rule or another resource's
    local ID. Neither display labels nor host paths are identity inputs.
    """
    return tuple(replace(rule, rule_id="style:" + _canonical_json([style_id, rule.rule_id]),
                         style_id=style_id, authored_rule_id=rule.rule_id)
                 for rule in rules)


class StyleRuleError(ValueError):
    """A pointed failure while converting schema-valid Style rules."""

    def __init__(self, diagnostic_id: str, detail: str, source_ref: str):
        self.diagnostic_id = diagnostic_id
        self.detail = detail
        self.source_ref = source_ref
        super().__init__(detail)


def parse_style_rules(body: Mapping[str, Any]) -> tuple[StyleRule, ...]:
    """Convert a schema-validated Style body into detached immutable values."""
    raw_rules = body.get("rules", ())
    if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, (str, bytes, bytearray)):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "Style body rules must be an array", "/body/rules")

    parsed: list[StyleRule] = []
    seen: set[str] = set()
    for index, raw_rule in enumerate(raw_rules):
        rule_ref = f"/body/rules/{index}"
        if not isinstance(raw_rule, Mapping):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "Style rule must be an object", rule_ref)
        rule_id = raw_rule.get("id")
        if not isinstance(rule_id, str):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "Style rule id must be a string", f"{rule_ref}/id")
        if rule_id in seen:
            raise StyleRuleError("E_STYLE_RULE_ID_DUPLICATE", f"Duplicate Style rule id {rule_id!r}",
                                 f"{rule_ref}/id")
        seen.add(rule_id)

        raw_selector = raw_rule.get("when", {})
        if not isinstance(raw_selector, Mapping):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "Style selector must be an object", f"{rule_ref}/when")
        selector = _parse_selector(raw_selector, f"{rule_ref}/when")
        raw_outcome = raw_rule.get("then", {})
        if not isinstance(raw_outcome, Mapping):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "Style outcome must be an object", f"{rule_ref}/then")
        outcome = _parse_outcome(raw_outcome, f"{rule_ref}/then")
        if isinstance(outcome, StyleEncodingOutcome) and _is_scoped(selector):
            title = outcome.legend.title if outcome.legend is not None else None
            if title is None or not title.strip():
                raise StyleRuleError("E_STYLE_LEGEND_TITLE_REQUIRED",
                                     "Scoped Style encodings require a non-empty legend title",
                                     f"{rule_ref}/then/encode/legend/title")
        parsed.append(StyleRule(rule_id, selector, outcome, rule_ref))
    return tuple(parsed)


def canonical_style_selector(selector: StyleSelector) -> str:
    """Return stable JSON for selector identity, independent of authored order."""
    normalized: dict[str, Any] = {}
    if selector.semantic is not None:
        normalized["semantic"] = selector.semantic
    if selector.purpose is not None:
        normalized["purpose"] = selector.purpose
    if selector.comparison_category is not None:
        normalized["comparisonCategory"] = selector.comparison_category
    if selector.column_source is not None:
        normalized["columnSource"] = (
            selector.column_source if isinstance(selector.column_source, str)
            else dict(selector.column_source)
        )
    if selector.roles:
        normalized["roles"] = sorted(selector.roles)
    if selector.fields:
        predicates = [_field_equals_envelope(predicate) for predicate in selector.fields]
        normalized["fields"] = sorted(predicates, key=_canonical_json)
    return _canonical_json(normalized)


def _parse_selector(raw: Mapping[str, Any], source_ref: str) -> StyleSelector:
    column_source: str | tuple[tuple[str, str], ...] | None = None
    if "columnSource" in raw:
        value = raw["columnSource"]
        if isinstance(value, str):
            column_source = value
        elif isinstance(value, Mapping) and all(
            isinstance(key, str) and isinstance(item, str) for key, item in value.items()
        ):
            column_source = tuple(sorted(value.items()))
        else:
            raise StyleRuleError("E_RESOURCE_SCHEMA", "columnSource must be a string or string mapping",
                                 f"{source_ref}/columnSource")

    raw_roles = raw.get("roles", ())
    if not isinstance(raw_roles, Sequence) or isinstance(raw_roles, (str, bytes, bytearray)):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "roles must be an array", f"{source_ref}/roles")
    roles = tuple(raw_roles)
    if any(not isinstance(role, str) for role in roles):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "roles entries must be strings", f"{source_ref}/roles")

    raw_fields = raw.get("fields", ())
    if not isinstance(raw_fields, Sequence) or isinstance(raw_fields, (str, bytes, bytearray)):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "fields must be an array", f"{source_ref}/fields")
    fields: list[StyleFieldEquals] = []
    for index, item in enumerate(raw_fields):
        item_ref = f"{source_ref}/fields/{index}"
        if not isinstance(item, Mapping) or "source" not in item or "equals" not in item:
            raise StyleRuleError("E_RESOURCE_SCHEMA", "field predicate needs source and equals", item_ref)
        source = _parse_field_source(item["source"], f"{item_ref}/source")
        equals = item["equals"]
        if not isinstance(equals, (str, bool, int, float)):
            raise StyleRuleError("E_STYLE_FACT_TYPE", "field equality must use a scalar value",
                                 f"{item_ref}/equals")
        if isinstance(equals, float) and not math.isfinite(equals):
            raise StyleRuleError("E_STYLE_FACT_TYPE", "field equality must be finite",
                                 f"{item_ref}/equals")
        fields.append(StyleFieldEquals(source, equals))

    return StyleSelector(
        semantic=_optional_string(raw, "semantic", source_ref),
        purpose=_optional_string(raw, "purpose", source_ref),
        comparison_category=_optional_string(raw, "comparisonCategory", source_ref),
        column_source=column_source,
        roles=roles,
        fields=tuple(fields),
    )


def _parse_field_source(raw: Any, source_ref: str) -> StyleFieldSource:
    if not isinstance(raw, Mapping) or len(raw) != 1:
        raise StyleRuleError("E_RESOURCE_SCHEMA", "field source needs exactly one selector", source_ref)
    if "field" in raw:
        key, value = "field_name", raw["field"]
    elif "fieldRole" in raw:
        key, value = "field_role", raw["fieldRole"]
    else:
        raise StyleRuleError("E_RESOURCE_SCHEMA", "unknown field source selector", source_ref)
    if not isinstance(value, str):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "field source selector must be a string", source_ref)
    return StyleFieldSource(**{key: value})


def _parse_outcome(raw: Mapping[str, Any], source_ref: str) -> StyleOutcome:
    if "role" in raw:
        role = raw["role"]
        if not isinstance(role, str):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "role outcome must be a string", f"{source_ref}/role")
        return StyleRoleOutcome(role)

    encode = raw.get("encode")
    if not isinstance(encode, Mapping):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "Style outcome needs role or encode", source_ref)
    channel = encode.get("channel")
    if not isinstance(channel, str):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "encoding channel must be a string", f"{source_ref}/encode/channel")
    source = _parse_field_source(encode.get("source"), f"{source_ref}/encode/source")
    scale_id = encode.get("scale")
    if not isinstance(scale_id, str):
        raise StyleRuleError("E_RESOURCE_SCHEMA", "encoding scale must be a string", f"{source_ref}/encode/scale")
    raw_domain = encode.get("domain")
    if isinstance(raw_domain, str):
        domain: tuple[str, ...] | str = raw_domain
    elif isinstance(raw_domain, Sequence) and not isinstance(raw_domain, (bytes, bytearray)):
        if any(not isinstance(value, str) for value in raw_domain):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "encoding domain entries must be strings",
                                 f"{source_ref}/encode/domain")
        domain = tuple(raw_domain)
    else:
        raise StyleRuleError("E_RESOURCE_SCHEMA", "encoding domain must be a string or string array",
                             f"{source_ref}/encode/domain")

    legend: StyleLegend | None = None
    if "legend" in encode:
        raw_legend = encode["legend"]
        if not isinstance(raw_legend, Mapping):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "legend must be an object", f"{source_ref}/encode/legend")
        title = _optional_string(raw_legend, "title", f"{source_ref}/encode/legend")
        if title is not None and not title.strip():
            raise StyleRuleError("E_STYLE_LEGEND_TITLE_REQUIRED", "A provided legend title must be non-blank",
                                 f"{source_ref}/encode/legend/title")
        show_scope = raw_legend.get("showScope", False)
        if not isinstance(show_scope, bool):
            raise StyleRuleError("E_RESOURCE_SCHEMA", "showScope must be a boolean",
                                 f"{source_ref}/encode/legend/showScope")
        legend = StyleLegend(title, show_scope)
    missing = encode.get("missing", "base")
    if not isinstance(missing, str) or not missing:
        raise StyleRuleError("E_RESOURCE_SCHEMA", "encoding missing must be base or a nonempty domain value",
                             f"{source_ref}/encode/missing")
    return StyleEncodingOutcome(channel, source, scale_id, domain, legend, missing)


def _optional_string(raw: Mapping[str, Any], key: str, source_ref: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise StyleRuleError("E_RESOURCE_SCHEMA", f"{key} must be a string", f"{source_ref}/{key}")
    return value


def _is_scoped(selector: StyleSelector) -> bool:
    return bool(selector.comparison_category is not None or selector.column_source is not None
                or selector.roles or selector.fields)


def _field_equals_envelope(predicate: StyleFieldEquals) -> dict[str, Any]:
    source = predicate.source
    if source.field_name is not None:
        source_value = {"field": source.field_name}
    elif source.field_role is not None:
        source_value = {"fieldRole": source.field_role}
    else:
        source_value = {}
    return {"source": source_value, "equals": predicate.equals}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
