"""Deterministic author-facing explanations for JSON Schema validation failures."""
from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import get_close_matches
import re
from typing import Any, Iterable, Mapping, Sequence

from jsonschema.exceptions import ValidationError


def _empty_error(operand: str) -> ValueError:
    return ValueError(f"E_SCHEMA_VIOLATION_EMPTY: {operand}=0; expected one or more schema validation errors")


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
        raise _empty_error("errors")
    error = min(candidates, key=_error_key)
    return replace(_explain(error), resource_kind=resource_kind, resource_identity=resource_identity)


def explain_all_errors(
    errors: Iterable[ValidationError], *, resource_kind: str | None = None, resource_identity: str | None = None,
    select_branches: bool = False, echo_values: bool = False,
) -> tuple[SchemaViolation, ...]:
    """Explain every independent leaf violation in deterministic order.

    `select_branches` reports, for a union whose discriminator (a `const` member such as `mode`) selects exactly one
    branch, that branch's own violations instead of the union wrapper; the wrapper stays when the tag is missing or
    unknown. `echo_values` names a short offending scalar in a pattern or format message (Project validation, #1303).
    """
    candidates = tuple(_leaf_errors(tuple(errors), select_branches))
    if not candidates:
        raise _empty_error("leafErrors")
    explained = [replace(_explain(error, echo_values), resource_kind=resource_kind, resource_identity=resource_identity)
                 for error in sorted(candidates, key=_aggregate_error_key)]
    unique: dict[tuple[object, ...], SchemaViolation] = {}
    for violation in explained:
        unique[(violation.pointer, violation.rule, violation.expected, violation.actual_kind, violation.message,
                violation.resource_kind, violation.resource_identity)] = violation
    return tuple(unique.values())


def _leaf_errors(errors: Iterable[ValidationError], select_branches: bool = False) -> Iterable[ValidationError]:
    """Replace diagnostic-unhelpful union wrappers with their actual leaves."""
    for error in errors:
        if error.validator in {"oneOf", "anyOf"} and error.context:
            if select_branches:
                selected = _selected_branch(error)
                if selected is not None:
                    yield from _leaf_errors(selected, select_branches)
                else:
                    yield error
            else:
                yield from _leaf_errors(error.context)
        else:
            yield error


def _selected_branch(error: ValidationError) -> list[ValidationError] | None:
    """The violations of the one union branch the instance's discriminator selects, else None.

    A branch is selected when no `const` member of the instance's own object fails in it and every other failing branch
    does; a missing or unknown tag fails every branch (or none by a `const`), so the union wrapper is reported.
    """
    by_branch: dict[Any, list[ValidationError]] = {}
    for child in error.context or ():
        by_branch.setdefault(child.schema_path[0] if child.schema_path else None, []).append(child)
    total = len(error.validator_value) if isinstance(error.validator_value, Sequence) else 0
    if len(by_branch) < total:
        return None  # a branch the instance satisfies: not a failed selection
    tag_failed = {index for index, children in by_branch.items()
                  if any(child.validator == "const" and len(child.relative_path) == 1 for child in children)}
    selected = [index for index in by_branch if index not in tag_failed]
    if len(selected) != 1 or not tag_failed:
        return None
    return by_branch[selected[0]]


def json_pointer(path: Iterable[Any]) -> str:
    """Encode an instance path as an RFC 6901 pointer."""
    parts = tuple(str(item).replace("~", "~0").replace("/", "~1") for item in path)
    return "/" + "/".join(parts) if parts else "/"


def _error_key(error: ValidationError) -> tuple[Any, ...]:
    pointer = json_pointer(error.absolute_path)
    # A leaf at a deeper instance location is normally more useful than a
    # wrapper `oneOf` error. Stable remaining fields avoid iterator-order leaks.
    return (-len(tuple(error.absolute_path)), pointer, _rule_rank(error.validator), str(error.validator), error.message)


def _aggregate_error_key(error: ValidationError) -> tuple[Any, ...]:
    """Order the new multi-diagnostic API independently of legacy selection."""
    return (
        json_pointer(error.absolute_path),
        _rule_rank(error.validator),
        str(error.validator),
        error.message,
    )


def _rule_rank(rule: str | None) -> int:
    return {
        "additionalProperties": 0,
        "required": 1,
        "enum": 2,
        "const": 3,
        "type": 4,
        # A value that fails both a shape ``pattern`` and its ``format`` is
        # reported by the format rule: the tie breaks on the validator name.
        "format": 5,
        "pattern": 5,
        "minimum": 6,
        "maximum": 6,
        "minLength": 7,
        "maxLength": 7,
        "oneOf": 8,
        "anyOf": 8,
    }.get(rule or "", 99)


_FORMAT_DESCRIPTIONS = {"date": "YYYY-MM-DD calendar date"}


def _with_article(description: str) -> str:
    return ("an " if description[:1] in "AEIOUaeiou" else "a ") + description


def _echo(instance: Any, echo: bool) -> str:
    """`, got 'value'` for a short scalar string when the caller allows it (a Project's own date or id, #1303)."""
    return f", got {instance!r}" if echo and isinstance(instance, str) and len(instance) <= 64 else ""


def _explain(error: ValidationError, echo_values: bool = False) -> SchemaViolation:
    rule = str(error.validator or "schema")
    pointer = json_pointer(error.absolute_path)
    actual_kind = _kind(error.instance)
    if rule in {"enum", "const"}:
        values = tuple(_literal(value) for value in (error.validator_value if rule == "enum" else (error.validator_value,)))
        noun = "one of" if rule == "enum" else "exactly"
        return SchemaViolation(pointer, rule, values, actual_kind,
                               f"expected {noun} {', '.join(values)}" + _echo(error.instance, echo_values))
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
        if echo_values and pattern == r"^\d{4}-\d{2}-\d{2}$":  # an ISO date written another way: say so, not the regex (#1303)
            expected = _FORMAT_DESCRIPTIONS["date"]
            return SchemaViolation(pointer, rule, (expected,), actual_kind,
                                   f"expected {_with_article(expected)}" + _echo(error.instance, True))
        return SchemaViolation(pointer, rule, (pattern,), actual_kind,
                               f"expected value matching pattern {pattern!r}" + _echo(error.instance, echo_values))
    if rule == "format":
        # Never echo the value (Spec 56 section 3): name the declared format only.
        name = str(error.validator_value)
        expected = _FORMAT_DESCRIPTIONS.get(name, f"value in format '{name}'")
        return SchemaViolation(pointer, rule, (expected,), actual_kind,
                               f"expected {_with_article(expected)}" + _echo(error.instance, echo_values))
    if rule in {"oneOf", "anyOf"}:
        forms = _union_forms(error)
        return SchemaViolation(pointer, "union", forms, actual_kind, "expected one permitted form" + (": " + "; ".join(forms) if forms else ""))
    return SchemaViolation(pointer, rule, (), actual_kind, error.message)


def _union_forms(error: ValidationError) -> tuple[str, ...]:
    forms: list[str] = []
    for branch in error.validator_value if isinstance(error.validator_value, Sequence) else ():
        if not isinstance(branch, Mapping):
            continue
        branch = _shared_part_branch(branch)
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


def _shared_part_branch(branch: Mapping[str, Any]) -> Mapping[str, Any]:
    """Describe a union branch that only references a shared schema part as the part's own definition.

    A branch written `{$ref: urn:chrona:...}` exposes no `required` or `properties`, so the union message would lose the
    form the definition declares; reading the target keeps the message the same as when the branch was written inline.
    The branch's own sibling keywords win. A local reference or an unknown target is left as written.
    """
    reference = branch.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("urn:"):
        return branch
    from chrona.resources import resolve_schema_reference

    resolved = resolve_schema_reference({}, reference)
    if resolved is None:
        return branch
    return {**resolved[1], **{key: value for key, value in branch.items() if key != "$ref"}}


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
