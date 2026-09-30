"""Canonical codecs for M26 operational workflow documents."""
from __future__ import annotations

from typing import Any, Mapping

import yaml

from chrona.resources import safe_load, schema_validator
from chrona.schema_diagnostics import explain_errors
from chrona.core.identity import canonical_bytes, content_identity, json_value


class OperationalResourceError(ValueError):
    """A stable diagnostic for an invalid operational resource."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def parse_document(payload: str | bytes, schema_name: str) -> dict[str, Any]:
    """Parse one YAML/JSON document and validate it against a packaged schema."""
    try:
        value = safe_load(payload)
    except yaml.YAMLError as error:
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", str(error)) from error
    if not isinstance(value, dict):
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", "document must be an object")
    value = json_value(value)
    errors = tuple(schema_validator(schema_name).iter_errors(value))
    if errors:
        identity = value.get("id")
        violation = explain_errors(
            errors, resource_kind=schema_name.removesuffix(".schema.yaml"), resource_identity=identity if isinstance(identity, str) else None,
        )
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", f"{violation.pointer}: {violation.message}")
    return value
