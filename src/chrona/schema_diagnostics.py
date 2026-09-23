"""Deterministic author-facing explanations for JSON Schema validation failures."""
from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import get_close_matches
import re
from typing import Any, Iterable, Mapping, Sequence

from jsonschema.exceptions import ValidationError


@dataclass(frozen=True)
class SchemaViolation:
    """One selected structural failure at an RFC 6901 instance location."""

    pointer: str
    rule: str
    expected: tuple[str, ...]
    actual_kind: str | None
    message: str
    resource_kind: str | None = None
    resource_identity: str | None = None


def explain_errors(
    errors: Iterable[ValidationError], *, resource_kind: str | None = None, resource_identity: str | None = None,
) -> SchemaViolation:
    """Select and explain one deterministic JSON Schema error.

    JSON Schema deliberately leaves author-facing error wording to consumers.
    This boundary turns validator details into a stable explanation before a
    Core or presentation ingress adapter exposes them.
    """
    candidates = tuple(errors)
    if not candidates:
        raise ValueError("E_SCHEMA_VIOLATION_EMPTY")
    error = min(candidates, key=_error_key)
    return replace(_explain(error), resource_kind=resource_kind, resource_identity=resource_identity)


def json_pointer(path: Iterable[Any]) -> str:
    """Encode an instance path as an RFC 6901 pointer."""
    parts = tuple(str(item).replace("~", "~0").replace("/", "~1") for item in path)
    return "/" + "/".join(parts) if parts else "/"


def _error_key(error: ValidationError) -> tuple[Any, ...]:
    pointer = json_pointer(error.absolute_path)
    # A leaf at a deeper instance location is normally more useful than a
    # wrapper `oneOf` error. Stable remaining fields avoid iterator-order leaks.
    return (-len(tuple(error.absolute_path)), pointer, _rule_rank(error.validator), str(error.validator), error.message)


def _rule_rank(rule: str | None) -> int:
    return {
        "additionalProperties": 0,
        "required": 1,
        "enum": 2,
        "const": 3,
        "type": 4,
        "pattern": 5,
        "minimum": 6,
        "maximum": 6,
        "minLength": 7,
        "maxLength": 7,
        "oneOf": 8,
        "anyOf": 8,
    }.get(rule or "", 99)


def _explain(error: ValidationError) -> SchemaViolation:
    rule = str(error.validator or "schema")
    pointer = json_pointer(error.absolute_path)
    actual_kind = _kind(error.instance)
    if rule in {"enum", "const"}:
        values = tuple(_literal(value) for value in (error.validator_value if rule == "enum" else (error.validator_value,)))
        noun = "one of" if rule == "enum" else "exactly"
        return SchemaViolation(pointer, rule, values, actual_kind, f"expected {noun} {', '.join(values)}")
    if rule == "required":
        missing = _quoted_member(error.message)
        expected = (missing,) if missing else ()
        suffix = f" '{missing}'" if missing else ""
        return SchemaViolation(pointer, rule, expected, actual_kind, f"missing required property{suffix}")
    if rule == "additionalProperties":
        unexpected = _quoted_member(error.message)
        properties = tuple(str(name) for name in error.schema.get("properties", {}).keys()) if isinstance(error.schema, Mapping) else ()
        suggestion = get_close_matches(unexpected, properties, n=1, cutoff=0.8) if unexpected else ()
        detail = f"unexpected property '{unexpected}'" if unexpected else "unexpected property"
        if suggestion:
            detail += f"; did you mean '{suggestion[0]}'?"
        return SchemaViolation(pointer, rule, properties, actual_kind, detail)
    if rule == "type":
        raw = error.validator_value
        expected = tuple(str(item) for item in raw) if isinstance(raw, (tuple, list)) else (str(raw),)
        return SchemaViolation(pointer, rule, expected, actual_kind, f"expected type {' or '.join(expected)}, got {actual_kind}")
    if rule in {"minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"}:
        bound = _literal(error.validator_value)
        return SchemaViolation(pointer, rule, (bound,), actual_kind, f"expected {rule} {bound}")
    if rule == "pattern":
        pattern = str(error.validator_value)
        return SchemaViolation(pointer, rule, (pattern,), actual_kind, f"expected value matching pattern {pattern!r}")
    if rule in {"oneOf", "anyOf"}:
        forms = _union_forms(error)
        return SchemaViolation(pointer, "union", forms, actual_kind, "expected one permitted form" + (": " + "; ".join(forms) if forms else ""))
    return SchemaViolation(pointer, rule, (), actual_kind, error.message)


def _union_forms(error: ValidationError) -> tuple[str, ...]:
    forms: list[str] = []
    for branch in error.validator_value if isinstance(error.validator_value, Sequence) else ():
        if not isinstance(branch, Mapping):
            continue
        properties = branch.get("properties")
        required = branch.get("required")
        if isinstance(properties, Mapping):
            tags = [f"{name}={_literal(value['const'])}" for name, value in properties.items()
                    if isinstance(value, Mapping) and "const" in value]
            if tags:
                forms.append(", ".join(tags))
                continue
        if isinstance(required, Sequence) and not isinstance(required, str):
            forms.append("properties " + ", ".join(str(item) for item in required))
    # ``jsonschema`` resolves a `$ref` branch before exposing child errors, so
    # the parent oneOf retains only the reference wrapper. Recover real tagged
    # forms from its deterministic const child errors in that case.
    for child in error.context:
        if child.validator != "const" or not child.absolute_path:
            continue
        member = str(tuple(child.absolute_path)[-1])
        forms.append(f"{member}={_literal(child.validator_value)}")
    return tuple(dict.fromkeys(forms))


def _quoted_member(message: str) -> str | None:
    match = re.search(r"'([^']+)'", message)
    return match.group(1) if match else None


def _literal(value: Any) -> str:
    if isinstance(value, str):
        return repr(value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _kind(value: Any) -> str:
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "string" if isinstance(value, str) else type(value).__name__
