"""Canonical codecs for M26 operational workflow documents."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Any, Mapping

import jsonschema
import yaml

from chrona.resources import schema_resource


class OperationalResourceError(ValueError):
    """A stable diagnostic for an invalid operational resource."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def json_value(value: Any) -> Any:
    """Convert YAML-native scalars to the JSON values described by the schemas."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_value(item) for item in value]
    return value


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the sole canonical JSON form used for operational identities."""
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_identity(value: Mapping[str, Any]) -> str:
    return "sha256:" + sha256(canonical_bytes(value)).hexdigest()


def parse_document(payload: str | bytes, schema_name: str) -> dict[str, Any]:
    """Parse one YAML/JSON document and validate it against a packaged schema."""
    try:
        value = yaml.safe_load(payload)
    except yaml.YAMLError as error:
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", str(error)) from error
    if not isinstance(value, dict):
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", "document must be an object")
    value = json_value(value)
    schema = yaml.safe_load(schema_resource(schema_name).read_text(encoding="utf-8"))
    store = _schema_store()
    validator = jsonschema.Draft202012Validator(schema, resolver=jsonschema.RefResolver.from_schema(schema, store=store))
    error = next(validator.iter_errors(value), None)
    if error is not None:
        location = "/" + "/".join(str(part) for part in error.absolute_path)
        raise OperationalResourceError("E_OPERATIONAL_SCHEMA", f"{location}: {error.message}")
    return value


def _schema_store() -> dict[str, Any]:
    names = (
        "revision-store-resource-ref-v0.1.schema.yaml",
        "actual-intake-batch-v0.2.schema.yaml",
        "actual-set-v0.2.schema.yaml",
        "command-request-v0.2.schema.yaml",
        "automation-result-v0.1.schema.yaml",
        "snapshot-ref-v0.2.schema.yaml",
        "store-config-v0.1.schema.yaml",
    )
    return {
        schema["$id"]: schema
        for name in names
        for schema in (yaml.safe_load(schema_resource(name).read_text(encoding="utf-8")),)
    }
