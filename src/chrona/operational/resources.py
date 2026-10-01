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


# Command Request versions the CLI accepts. v0.2 stays readable while its successor (strict `storeAddress`,
# #710) is adopted; an unknown or missing version is reported against the current schema.
COMMAND_SCHEMAS = {
    "chrona/command/v0.2": "command-request-v0.2.schema.yaml",
    "chrona/command/v0.3": "command-request-v0.3.schema.yaml",
}
COMMAND_SCHEMA = COMMAND_SCHEMAS["chrona/command/v0.3"]
# Automation Result versions, newest first. A result names the newest contract its content satisfies, so content
# that still carries a loose legacy Store address (echoed from a v0.2 command or a v0.2 baseline) stays a v0.1 result.
AUTOMATION_RESULT_SCHEMAS = {
    "chrona/automation-result/v0.2": "automation-result-v0.2.schema.yaml",
    "chrona/automation-result/v0.1": "automation-result-v0.1.schema.yaml",
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


def stamp_automation_result(result: dict[str, Any]) -> dict[str, Any]:
    """Set `version` to the newest Automation Result contract the content satisfies, and return the result.

    The strict v0.2 refuses a Store address outside `storeAddress`. A result that echoes a legacy v0.2 command's
    target or a v0.2 baseline's Project reference can carry such an address, and it must not claim a contract it
    breaks, so it keeps the v0.1 version it is built with. A result that satisfies neither is left as built.
    """
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
