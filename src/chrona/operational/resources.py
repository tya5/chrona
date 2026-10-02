"""Canonical codecs for M26 operational workflow documents."""
from __future__ import annotations

import re
from typing import Any, Mapping

import yaml

from chrona.resources import safe_load, schema_validator
from chrona.schema_diagnostics import explain_errors
from chrona.usecases.diagnostic_messages import error_message
from chrona.core.identity import canonical_bytes, content_identity, json_value


class OperationalResourceError(ValueError):
    """A stable diagnostic for an invalid operational resource."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# Command Request versions the CLI accepts. v0.2 (loose Store addresses) was retired once no committed or
# test command used it (#731); an unknown, retired or missing version is reported against the current schema.
COMMAND_SCHEMAS = {
    "chrona/command/v0.3": "command-request-v0.3.schema.yaml",
}
COMMAND_SCHEMA = COMMAND_SCHEMAS["chrona/command/v0.3"]
# Automation Result versions. v0.1 (loose Store addresses) was retired with the writers' fallback to it (#731).
AUTOMATION_RESULT_SCHEMAS = {
    "chrona/automation-result/v0.2": "automation-result-v0.2.schema.yaml",
}


def command_schema_name(payload: str | bytes) -> str:
    """The Command Request schema named by a document's `version`, else the current one."""
    try:
        value = safe_load(payload)
    except yaml.YAMLError:
        return COMMAND_SCHEMA
    version = value.get("version") if isinstance(value, dict) else None
    return COMMAND_SCHEMAS.get(version, COMMAND_SCHEMA) if isinstance(version, str) else COMMAND_SCHEMA


def parse_command(payload: str | bytes) -> dict[str, Any]:
    """Parse one Command Request of any readable version."""
    return parse_document(payload, command_schema_name(payload))


_LEADING_CODE = re.compile(r"^[EW]_[A-Z0-9_]+")


def diagnostic_row(text: str) -> dict[str, str]:
    """The result row for ``"E_X"`` or ``"E_X: detail"``: the leading code, and the detail as the message (#829)."""
    leading = _LEADING_CODE.match(text)
    if leading is None:
        return {"code": "E_AUTOMATION_FAILURE", "message": text or "the automation operation failed without a message"}
    detail = text[leading.end():].lstrip(": ").strip()
    return {"code": leading.group(0), "message": detail} if detail else {"code": leading.group(0)}


def stamp_automation_result(result: dict[str, Any]) -> dict[str, Any]:
    """Set `version` to the current Automation Result contract when the content satisfies it, and return the result.

    Every diagnostic row leaves with a `message` that says more than its code: the producer's own, else the curated
    or derived sentence of `usecases.diagnostic_messages` (#829, as for the CLI rows of #782).

    The strict v0.2 refuses a Store address outside `storeAddress`. A result that does not satisfy it is left as built
    (every writer builds the current version); nothing falls back to the retired v0.1 any more (#731).
    """
    result["diagnostics"] = [
        {**row, "message": error_message(str(row["code"]), row.get("message"))}
        if isinstance(row, dict) and isinstance(row.get("code"), str) and row["code"] else row
        for row in result.get("diagnostics", [])
    ]
    for version, schema_name in AUTOMATION_RESULT_SCHEMAS.items():
        candidate = json_value({**result, "version": version})
        if not any(schema_validator(schema_name).iter_errors(candidate)):
            result["version"] = version
            break
    return result


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
