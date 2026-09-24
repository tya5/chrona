"""Canonical codecs for M26 operational workflow documents."""
from __future__ import annotations

from typing import Any, Mapping

import jsonschema
import yaml

from chrona.resources import safe_load, schema_document
from chrona.schema_diagnostics import explain_errors
from chrona.core.identity import canonical_bytes, content_identity, json_value


class OperationalResourceError(ValueError):
    """A stable diagnostic for an invalid operational resource."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def parse_document(payload: str | bytes, schema_name: str) -> dict[str, Any]:
    """Parse one YAML/JSON document and validate it against a packaged schema."""
    try:
        value = safe_load(payload)
    except yaml.YAMLError as error:
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", str(error)) from error
    if not isinstance(value, dict):
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", "document must be an object")
    value = json_value(value)
    schema = schema_document(schema_name)
    store = _schema_store()
    validator = jsonschema.Draft202012Validator(schema, resolver=jsonschema.RefResolver.from_schema(schema, store=store))
    errors = tuple(validator.iter_errors(value))
    if errors:
        identity = value.get("id")
        violation = explain_errors(
            errors, resource_kind=schema_name.removesuffix(".schema.yaml"), resource_identity=identity if isinstance(identity, str) else None,
        )
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", f"{violation.pointer}: {violation.message}")
    return value


def _schema_store() -> dict[str, Any]:
    names = (
        "revision-store-resource-ref-v0.1.schema.yaml",
        "actual-intake-batch-v0.2.schema.yaml",
        "actual-set-v0.2.schema.yaml",
        "authoring-command-v0.1.schema.yaml",
        "authoring-command-result-v0.1.schema.yaml",
        "command-request-v0.2.schema.yaml",
        "automation-result-v0.1.schema.yaml",
        "snapshot-ref-v0.2.schema.yaml",
        "store-config-v0.1.schema.yaml",
    )
    return {
        schema["$id"]: schema
        for name in names
        for schema in (schema_document(name),)
    }
